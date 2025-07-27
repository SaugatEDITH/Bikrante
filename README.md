
# 🛍️ Bikrente – E-Commerce Platform

**Bikrente** is a Django-based e-commerce web application designed to support local businesses by providing a flexible, scalable, and user-friendly online shopping experience.

---

## 📥 Download & Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/SaugatEDITH/Bikrante.git
cd bikrente
```

### 2. Set Up Virtual Environment

#### On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

#### On Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Requirements

```bash
pip install -r requirements.txt
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser (Admin Access)

```bash
python manage.py createsuperuser
```

### 6. Start Development Server

```bash
python manage.py runserver
```

Visit: `http://localhost:8000/` the 127.0.0.1:8000 wont work properly because Trunstile havent configured for that. 

### 7. Access Admin Panel

Go to: `http://localhost:8000/admin/`

Login with your superuser credentials.

---

## 🧪 Features

- ✅ Product listing, cart, checkout
- 🔒 Secure login/logout/signup
- 📦 Order & Inventory Management
- 🧾 PDF Invoice Generation
- 🔍 Advanced Search & Filters
- 🤖 Zipher AI Chatbot and Smart Search
- 🎯 Trending / Popular / Top-selling Products
- 🌐 Payment Integration: Esewa, Khalti, PayPal
- 📱 Mobile-responsive UI
- 🛒 Wishlist and Product Comparison
- 👤 User & Admin Dashboards

---

## 📁 Project Structure (Simplified)

```
bikrente/
├── manage.py
├── bikrente/             ← Django settings and URLs
├── shopapp/              ← App: products, cart, orders, etc.
├── templates/
├── static/
├── media/
├── requirements.txt
└── README.md
```

---

## 📌 Notes

- Python 3.8+ recommended
- SQLite used for development
- To collect static files for production:
  ```bash
  python manage.py collectstatic
  ```

---

## 📧 Contact

- Email: info@bikrente.com
- GitHub Issues: [Submit a Bug](https://github.com/SaugatEDITH/Bikrante/issues)

---

🚀 Happy Coding!
