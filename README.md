
# 🛍️ Bikrente – E-Commerce Platform

**Bikrente** is a Django-based e-commerce web application designed to support local businesses by providing a flexible, scalable, and user-friendly online shopping experience.

---

## 📥 Download & Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/bikrente.git
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
