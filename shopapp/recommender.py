import os
import pickle
import threading
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db.models import Count, Max
from django.utils import timezone

from .models import Product, RecommenderTrainingState, Review, UserActivityEvent, UserRecommendationCache
from django.db import transaction
import datetime
import logging
import math


logger = logging.getLogger(__name__)


MODEL_DIRNAME = "recommender_models"
MODEL_FILENAME = "surprise_svd.pkl"
MODEL_PREV_FILENAME = "surprise_svd_prev.pkl"


def _model_dir() -> Path:
    base = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    path = base / MODEL_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _model_paths():
    d = _model_dir()
    return d / MODEL_FILENAME, d / MODEL_PREV_FILENAME


def _load_model():
    model_path, _prev = _model_paths()
    if not model_path.exists():
        return None
    with model_path.open("rb") as f:
        return pickle.load(f)


def _save_model(model):
    model_path, prev_path = _model_paths()
    if model_path.exists():
        try:
            if prev_path.exists():
                prev_path.unlink()
            model_path.replace(prev_path)
        except Exception:
            # If backup rotation fails, keep going; we can still overwrite.
            pass

    with model_path.open("wb") as f:
        pickle.dump(model, f)


def _event_to_rating(event_type: str, duration_ms: int | None) -> float:
    if event_type == "impression":
        return 1.0
    if event_type == "hover":
        if not duration_ms:
            return 1.0
        return min(3.0, 1.0 + (duration_ms / 3000.0))
    if event_type == "dwell":
        if not duration_ms:
            return 1.0
        return min(4.0, 1.0 + (duration_ms / 5000.0) * 2.0)
    if event_type in {"click", "quick_view"}:
        return 3.5
    if event_type == "add_to_cart":
        return 4.5
    if event_type == "wishlist":
        return 4.8
    return 1.0


def _user_key_for_event(e: UserActivityEvent) -> str:
    if e.user_id:
        return f"u:{e.user_id}"
    if e.anon_id:
        return f"a:{e.anon_id}"
    if e.fingerprint:
        return f"f:{e.fingerprint}"
    if e.session_key:
        return f"s:{e.session_key}"
    return "unknown"


@dataclass
class RecoResult:
    product_ids: list[int]
    source: str


def train_if_needed(force: bool = False) -> bool:
    """Train Surprise SVD model if new events exist.

    Returns True if a new model was trained.
    """

    try:
        from surprise import Dataset, Reader, SVD
    except Exception:
        # surprise not installed
        return False

    max_id = UserActivityEvent.objects.aggregate(m=Max("id")).get("m") or 0
    state, _ = RecommenderTrainingState.objects.get_or_create(key="default")

    if not force and max_id <= state.last_trained_event_id:
        return False

    ninety_days_ago = timezone.now() - datetime.timedelta(days=90)
    events = list(
        UserActivityEvent.objects.select_related("product")
        .filter(product__isnull=False, created_at__gte=ninety_days_ago)
        .order_by("id")
        .values("id", "user_id", "anon_id", "session_key", "fingerprint", "product_id", "event_type", "duration_ms")
    )

    if not events:
        return False

    rows: list[tuple[str, str, float]] = []

    # Implicit feedback from activity events
    for e in events:
        et = e["event_type"]
        dur = e.get("duration_ms")
        rating = _event_to_rating(et, dur)

        user_id = e.get("user_id")
        if user_id:
            user_key = f"u:{user_id}"
        elif e.get("anon_id"):
            user_key = f"a:{e.get('anon_id')}"
        elif e.get("fingerprint"):
            user_key = f"f:{e.get('fingerprint')}"
        elif e.get("session_key"):
            user_key = f"s:{e.get('session_key')}"
        else:
            user_key = "unknown"

        rows.append((user_key, str(e["product_id"]), float(rating)))

    # Explicit feedback from product reviews (1–5 stars)
    reviews_qs = (
        Review.objects.filter(rating__isnull=False)
        .select_related("product", "user")
        .values("user_id", "product_id", "rating")
    )
    for r in reviews_qs:
        user_id = r.get("user_id")
        product_id = r.get("product_id")
        rating = r.get("rating")
        if not user_id or not product_id or rating is None:
            continue
        user_key = f"u:{user_id}"
        rows.append((user_key, str(product_id), float(rating)))

    if not rows:
        return False

    reader = Reader(rating_scale=(1, 5))
    data = Dataset.load_from_df(
        __import__("pandas").DataFrame(rows, columns=["user", "item", "rating"]),
        reader,
    )

    trainset = data.build_full_trainset()
    algo = SVD(n_factors=80, n_epochs=25, lr_all=0.005, reg_all=0.02)
    algo.fit(trainset)

    _save_model(algo)

    # BEGIN: Offline precomputation
    all_user_keys = {row[0] for row in rows}
    
    products_qs = Product.objects.annotate(like_count=Count("likes"))
    candidate_ids = list(products_qs.values_list("id", flat=True))
    pop_stats = {
        p["id"]: p for p in products_qs.values("id", "sales_count", "views_count", "like_count")
    }

    cache_objects = []
    
    for ukey in all_user_keys:
        scored = []
        for pid in candidate_ids:
            try:
                pred = algo.predict(ukey, str(pid))
                cf_score = float(pred.est)
            except Exception:
                continue

            pstats = pop_stats.get(pid) or {}
            sales = float(pstats.get("sales_count") or 0.0)
            views = float(pstats.get("views_count") or 0.0)
            likes = float(pstats.get("like_count") or 0.0)

            raw_pop = sales * 1.0 + views * 0.1 + likes * 2.0
            pop_score = math.log1p(raw_pop) if raw_pop > 0.0 else 0.0

            final_score = 0.7 * cf_score + 0.3 * pop_score
            scored.append((pid, final_score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        top_ids = [pid for pid, _s in scored[:50]]
        
        cache_objects.append(
            UserRecommendationCache(user_key=ukey, recommended_product_ids=top_ids)
        )
        
    if cache_objects:
        with transaction.atomic():
            UserRecommendationCache.objects.all().delete()
            UserRecommendationCache.objects.bulk_create(cache_objects, batch_size=500)
    # END: Offline precomputation

    state.last_trained_event_id = max_id
    state.trained_at = timezone.now()
    state.model_version = state.model_version + 1
    state.save(update_fields=["last_trained_event_id", "trained_at", "model_version"])

    return True


def train_on_startup_async():
    def _runner():
        try:
            train_if_needed(force=False)
        except Exception:
            # Never block startup for recommender errors.
            pass

    t = threading.Thread(target=_runner, daemon=True)
    t.start()


def recommend_for_request(*, user, anon_id: str = "", fingerprint: str = "", limit: int = 24) -> RecoResult:
    """Return recommended product IDs (in-stock prioritized by the caller)."""

    # Determine stable user identity
    if getattr(user, "is_authenticated", False):
        user_key = f"u:{user.id}"
        identity_filter = {"user": user}
    elif anon_id:
        user_key = f"a:{anon_id}"
        identity_filter = {"anon_id": anon_id}
    elif fingerprint:
        user_key = f"f:{fingerprint}"
        identity_filter = {"fingerprint": fingerprint}
    else:
        logger.debug("Recommender: no user identity, using fallback.")
        return fallback_recommendations(limit=limit)

    # Cold-start handling: fall back if this identity has very little history
    MIN_EVENTS_FOR_CF = 5
    event_count = (
        UserActivityEvent.objects.filter(product__isnull=False, **identity_filter).count()
    )
    if event_count < MIN_EVENTS_FOR_CF:
        logger.debug(
            "Recommender: cold-start for %s (events=%s), using popularity fallback.",
            user_key,
            event_count,
        )
        return fallback_recommendations(limit=limit)

    # Check the database cache for pre-computed recommendations
    cached_rec = UserRecommendationCache.objects.filter(user_key=user_key).first()
    if cached_rec and cached_rec.recommended_product_ids:
        logger.debug(
            "Recommender: using precomputed cache for %s, top_ids=%s",
            user_key,
            cached_rec.recommended_product_ids[:5],
        )
        return RecoResult(product_ids=cached_rec.recommended_product_ids[:limit], source="cached_hybrid")

    logger.debug("Recommender: missing cache for %s, using popularity fallback.", user_key)
    return fallback_recommendations(limit=limit)


def fallback_recommendations(*, limit: int = 24) -> RecoResult:
    # popularity-based: sales_count + views_count + likes
    products = (
        Product.objects.annotate(like_count=Count("likes"))
        .order_by("-sales_count", "-views_count", "-like_count", "-created_at")
        .values_list("id", flat=True)[:limit]
    )
    return RecoResult(product_ids=list(products), source="fallback_popularity")
