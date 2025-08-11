# FTV Backend API

Comprehensive REST API for the FTV (Zalaegerszegi Televízió 2) school media management system.

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure settings:**
   ```bash
   copy backend\example_local_settings.py local_settings.py
   # Edit local_settings.py with your configuration
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Start development server:**
   ```bash
   python manage.py runserver
   ```

5. **Access API documentation:**
   - Interactive docs: http://localhost:8000/api/docs
   - API endpoints: http://localhost:8000/api/

## 📚 Documentation

- **Complete API Documentation:** [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Interactive OpenAPI Docs:** Visit `/api/docs` when server is running
- **Module Documentation:** Detailed docstrings in each `api_modules/` file

## 🏗 Architecture

The API is organized into modular components:

```
backend/
├── api_modules/           # API endpoint modules
│   ├── auth.py           # Authentication & JWT
│   ├── core.py           # Basic utilities & permissions  
│   ├── users.py          # User profiles & info
│   ├── user_management.py # User CRUD operations
│   ├── academic.py       # School years & classes
│   ├── partners.py       # Partner management
│   ├── equipment.py      # Equipment & types
│   ├── production.py     # Filming sessions
│   ├── radio.py          # Radio stabs & sessions
│   ├── communications.py # Announcements
│   ├── organization.py   # Stabs & roles
│   ├── absence.py        # Absence management
│   └── config.py         # System configuration
├── api.py                # Main API router
├── settings.py           # Django settings
└── urls.py               # URL configuration
```

## 🔐 Authentication

JWT-based authentication with role-based access control:

```bash
# Login to get token
curl -X POST http://localhost:8000/api/login \
  -d "username=admin&password=password"

# Use token in requests  
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/profile
```

## 👥 User Roles

- **Student** (`admin_type: "none"`): Basic access to own data
- **Teacher** (`admin_type: "teacher"`): Manage classes and filming
- **System Admin** (`admin_type: "system_admin"`): Full user management
- **Developer** (`admin_type: "developer"`): Complete system access

## 🎯 Key Features

- **🎬 Production Management:** Filming sessions with equipment booking
- **📻 Radio System:** Special support for 9F radio students  
- **👥 User Management:** Complete CRUD with role-based permissions
- **🎓 Academic Integration:** School years, classes, and student tracking
- **🔧 Equipment Tracking:** Inventory management with availability
- **📢 Communications:** Announcements with targeted messaging
- **🤝 Partner Management:** External institution coordination

## 🛠 Development

**Project Structure:**
- Django + Django Ninja framework
- Modular API design for maintainability  
- JWT authentication with role-based access
- Comprehensive documentation and type hints
- SQLite database (configurable)

**Code Style:**
- Detailed docstrings for all public APIs
- Type hints for better IDE support
- Modular organization for easy maintenance
- Consistent error handling patterns

## 📱 Frontend Integration

The API is designed for easy frontend integration:

- **Permission-based UI:** GET `/api/permissions` returns UI configuration
- **Consistent responses:** All endpoints use standard JSON responses
- **Rich error messages:** Detailed error information for debugging
- **Interactive docs:** Built-in API explorer for testing

## 🔒 Security

- JWT token authentication
- Role-based access control  
- Input validation and sanitization
- SQL injection prevention
- CORS configuration support

## 🚀 Production Deployment

1. **Environment setup:**
   ```bash
   # Copy and configure production settings
   cp backend/example_local_settings.py local_settings.py
   # Edit local_settings.py for production
   ```

2. **Database migration:**
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

3. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

4. **Start production server:**
   ```bash
   # Use proper WSGI server like Gunicorn
   gunicorn backend.wsgi:application
   ```

## 📞 Support

- **API Documentation:** [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Interactive Testing:** Visit `/api/docs`
- **Issues:** Contact development team

---

**Version:** 2.0.0  
**Status:** Production Ready  
**Last Updated:** August 2025