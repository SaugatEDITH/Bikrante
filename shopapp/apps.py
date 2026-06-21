from django.apps import AppConfig


class ShopappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shopapp'

    def ready(self):
        try:
            from .recommender import train_on_startup_async

            train_on_startup_async()
        except Exception:
            # Never block app startup for recommender errors
            pass
