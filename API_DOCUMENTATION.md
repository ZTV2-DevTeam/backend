# FTV Backend API - Complete Documentation

## 📚 Overview

The FTV Backend API is a comprehensive REST API designed for school media management systems. It provides complete functionality for managing students, teachers, media equipment, filming sessions, radio programs, and administrative tasks.

**Base URL:** `/api/`
**Authentication:** JWT Bearer tokens
**Content-Type:** `application/json`

## 🔐 Quick Start

### 1. Authentication
```bash
# Login to get JWT token
curl -X POST /api/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=yourusername&password=yourpassword"

# Response:
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": 1,
  "username": "yourusername",
  "first_name": "Your",
  "last_name": "Name",
  "email": "your@email.com"
}
```

### 2. Using the Token
Include the token in the Authorization header for all subsequent requests:
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" /api/profile
```

## 🏗 API Architecture

The API is organized into logical modules:

| Module | Endpoint Prefix | Description |
|--------|----------------|-------------|
| **Authentication** | `/api/` | Login, logout, password reset |
| **Core** | `/api/` | Basic utilities, permissions, system status |
| **Users** | `/api/users/` | User profiles and information |
| **User Management** | `/api/user-management/` | CRUD operations for users |
| **Academic** | `/api/` | School years and classes |
| **Partners** | `/api/partners/` | External partner management |
| **Equipment** | `/api/` | Equipment types and inventory |
| **Production** | `/api/production/` | Filming sessions and contacts |
| **Radio** | `/api/` | Radio stabs and sessions |
| **Communications** | `/api/communications/` | Announcements and messaging |
| **Organization** | `/api/` | Stabs, roles, assignments |
| **Absence** | `/api/` | Absence management |
| **Config** | `/api/` | System configuration |

## 👥 User Roles & Permissions

### Student (admin_type: "none")
- ✅ View own profile and schedule
- ✅ View announcements
- ✅ Check availability
- ✅ Access radio sessions (9F students only)
- ❌ Administrative functions

### Teacher (admin_type: "teacher") 
- ✅ Everything students can do
- ✅ Manage filming sessions
- ✅ Create announcements
- ✅ Manage radio sessions
- ✅ Access student information
- ❌ System administration

### System Admin (admin_type: "system_admin")
- ✅ Everything teachers can do  
- ✅ Full user management
- ✅ System configuration
- ✅ Academic year setup
- ❌ Developer tools

### Developer Admin (admin_type: "developer")
- ✅ Complete system access
- ✅ All administrative functions
- ✅ API debugging capabilities
- ✅ Advanced system configuration

## 🔑 Core Endpoints

### Authentication
```bash
# Login
POST /api/login
Content-Type: application/x-www-form-urlencoded
Body: username=user&password=pass

# Get current user profile
GET /api/profile
Authorization: Bearer {token}

# Refresh token
POST /api/refresh-token
Authorization: Bearer {token}

# Logout
POST /api/logout
Authorization: Bearer {token}

# Password reset flow
POST /api/forgot-password
{"email": "user@example.com"}

GET /api/verify-reset-token/{token}

POST /api/reset-password
{"token": "...", "password": "newpass", "confirmPassword": "newpass"}
```

### User Permissions
```bash
# Get comprehensive user permissions
GET /api/permissions
Authorization: Bearer {token}

# Returns detailed permission structure for frontend
{
  "user_info": {...},
  "permissions": {
    "is_admin": true,
    "can_manage_users": true,
    "can_create_forgatas": true,
    ...
  },
  "display_properties": {
    "show_admin_menu": true,
    "dashboard_widgets": [...],
    "navigation_items": [...],
    ...
  },
  "role_info": {...}
}
```

## 🎬 Production Management

### Filming Sessions
```bash
# List filming sessions with filters
GET /api/production/filming-sessions?date_from=2024-03-01&date_to=2024-03-31

# Create new filming session
POST /api/production/filming-sessions
Authorization: Bearer {token}
{
  "name": "Morning Show Recording",
  "description": "Weekly morning show episode", 
  "date": "2024-03-15",
  "time_from": "09:00",
  "time_to": "11:00",
  "type": "rendes",
  "equipment_ids": [1, 2, 3]
}

# Update filming session
PUT /api/production/filming-sessions/123
Authorization: Bearer {token}
{
  "name": "Updated Morning Show Recording",
  "notes": "Equipment list updated"
}
```

### Contact Persons
```bash
# List contact persons
GET /api/production/contact-persons
Authorization: Bearer {token}

# Create contact person
POST /api/production/contact-persons
Authorization: Bearer {token}
{
  "name": "John Smith",
  "email": "john@partner.com", 
  "phone": "+36301234567"
}
```

## 🎓 Academic Management

### School Years
```bash
# Get all school years
GET /api/school-years
Authorization: Bearer {token}

# Get active school year
GET /api/school-years/active
Authorization: Bearer {token}

# Create new school year (admin only)
POST /api/school-years
Authorization: Bearer {token}
{
  "start_date": "2024-09-01",
  "end_date": "2025-06-30"
}
```

### Classes
```bash
# Get all classes
GET /api/classes
Authorization: Bearer {token}

# Get classes by section (e.g., F for radio students)
GET /api/classes/by-section/F
Authorization: Bearer {token}

# Create new class (admin only)
POST /api/classes
Authorization: Bearer {token}
{
  "start_year": 2020,
  "szekcio": "F",
  "tanev_id": 1
}
```

## 🔧 Equipment Management

### Equipment Types
```bash
# Get all equipment types
GET /api/equipment-types
Authorization: Bearer {token}

# Create equipment type (admin only)
POST /api/equipment-types
Authorization: Bearer {token}
{
  "name": "Kamera",
  "emoji": "📹"
}
```

### Equipment Items
```bash
# Get all equipment (with optional filters)
GET /api/equipment?functional_only=true
Authorization: Bearer {token}

# Create equipment (admin only)
POST /api/equipment
Authorization: Bearer {token}
{
  "nickname": "Main Camera",
  "brand": "Canon",
  "model": "XA40",
  "equipment_type_id": 1,
  "functional": true
}

# Check equipment availability
GET /api/equipment/123/availability?start_datetime=2024-03-15T14:00:00Z&end_datetime=2024-03-15T16:00:00Z
Authorization: Bearer {token}
```

## 📻 Radio Management

### Radio Stabs
```bash
# Get all radio stabs
GET /api/radio-stabs
Authorization: Bearer {token}

# Create radio stab (admin only)
POST /api/radio-stabs
Authorization: Bearer {token}
{
  "name": "Morning News Team",
  "team_code": "MNT",
  "description": "Daily morning news broadcast"
}
```

### Radio Sessions
```bash
# Get radio sessions with date filter
GET /api/radio-sessions?start_date=2024-03-01&end_date=2024-03-31
Authorization: Bearer {token}

# Create radio session (admin only)
POST /api/radio-sessions
Authorization: Bearer {token}
{
  "radio_stab_id": 1,
  "date": "2024-03-15",
  "time_from": "14:00",
  "time_to": "16:00",
  "participant_ids": [1, 2, 3]
}
```

## 👥 User Management

### User Information
```bash
# Get all users (admin only)
GET /api/users
Authorization: Bearer {token}

# Get specific user details (admin only)
GET /api/users/123
Authorization: Bearer {token}

# Get radio students (9F) (admin only)
GET /api/users/radio-students
Authorization: Bearer {token}

# Check user availability
GET /api/users/123/availability?start_datetime=2024-03-15T14:00:00Z&end_datetime=2024-03-15T16:00:00Z
Authorization: Bearer {token}

# Get active users (active now and active today)
GET /api/users/active
Authorization: Bearer {token}
```

### User CRUD Operations
```bash
# Create new user (admin only)
POST /api/user-management/users
Authorization: Bearer {token}
{
  "username": "student1",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "admin_type": "none",
  "osztaly_id": 1
}

# Update user (admin only)
PUT /api/user-management/users/123
Authorization: Bearer {token}
{
  "admin_type": "teacher",
  "special_role": "production_leader"
}

# Send first-login email (admin only)
POST /api/user-management/users/123/send-first-login
Authorization: Bearer {token}

# Bulk create students (admin only)
POST /api/user-management/users/bulk-create-students
Authorization: Bearer {token}
{
  "osztaly_id": 1,
  "students": [
    {"username": "student1", "first_name": "John", "last_name": "Doe", "email": "john@example.com"}
  ]
}
```

## 🤝 Partner Management

```bash
# Get all partners
GET /api/partners

# Get specific partner
GET /api/partners/123

# Create partner (admin only)
POST /api/partners
Authorization: Bearer {token}
{
  "name": "ABC Corporation",
  "address": "123 Main Street",
  "institution": "Technology",
  "imageURL": "https://example.com/logo.png"
}

# Update partner (admin only)
PUT /api/partners/123
Authorization: Bearer {token}
{
  "name": "ABC Corp Updated",
  "imageURL": "https://example.com/new-logo.png"
}
```

## 📢 Communications

```bash
# Get announcements (filtered by user permissions)
GET /api/communications/announcements
Authorization: Bearer {token}

# Create global announcement (admin/teacher only)
POST /api/communications/announcements
Authorization: Bearer {token}
{
  "title": "School Event Notification",
  "body": "Important information about upcoming school event...",
  "recipient_ids": []
}

# Create targeted announcement
POST /api/communications/announcements
Authorization: Bearer {token}
{
  "title": "9F Class Radio Session",
  "body": "Radio session scheduled for Friday at 2 PM",
  "recipient_ids": [12, 34, 56]
}
```

## 🛠 System Configuration

```bash
# Check system setup status (admin only)
GET /api/tanev-config-status
Authorization: Bearer {token}

# Returns setup wizard progress:
{
  "config_necessary": true,
  "system_admin_setup_required": true,
  "completion_percentage": 60,
  "setup_steps": [
    {
      "step": "basic_config",
      "name": "Alapvető rendszerbeállítások",
      "completed": true
    },
    ...
  ]
}
```

## 🔍 Testing and Debugging

```bash
# Basic connectivity test
GET /api/hello?name=Developer

# Authentication status check  
GET /api/test-auth
```

## 📱 Frontend Integration Tips

### 1. Permission-Based UI
```javascript
// Get user permissions to control UI elements
const permissionResponse = await fetch('/api/permissions', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { permissions, display_properties } = await permissionResponse.json();

// Show/hide UI elements based on permissions
if (display_properties.show_admin_menu) {
  // Show admin menu
}
if (permissions.can_manage_users) {
  // Show user management button
}
```

### 2. Error Handling
```javascript
try {
  const response = await fetch('/api/some-endpoint', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (!response.ok) {
    const error = await response.json();
    console.error('API Error:', error.message);
    // Handle specific error codes
    if (response.status === 401) {
      // Redirect to login
    }
  }
  
  const data = await response.json();
  // Handle success
} catch (error) {
  console.error('Network Error:', error);
}
```

### 3. Token Management
```javascript
// Check token expiration and refresh if needed
const checkAndRefreshToken = async () => {
  try {
    const response = await fetch('/api/profile', {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    
    if (response.status === 401) {
      // Token expired, try to refresh
      const refreshResponse = await fetch('/api/refresh-token', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${currentToken}` }
      });
      
      if (refreshResponse.ok) {
        const { token } = await refreshResponse.json();
        // Store new token
        localStorage.setItem('jwt_token', token);
        return token;
      } else {
        // Refresh failed, redirect to login
        window.location.href = '/login';
      }
    }
  } catch (error) {
    console.error('Token check failed:', error);
  }
};
```

## 🚀 Interactive Documentation

For comprehensive interactive documentation with request/response examples:

**Visit: `/api/docs` when the server is running**

This provides:
- Complete endpoint documentation
- Interactive request testing
- Schema definitions
- Example requests and responses
- Authentication testing

## 🔒 Security Best Practices

1. **Always use HTTPS in production**
2. **Store JWT tokens securely (HttpOnly cookies preferred)**
3. **Implement proper token expiration handling**
4. **Validate all user inputs**
5. **Use role-based access control**
6. **Log security events**
7. **Regular security updates**

## 📞 Support

For API support and questions:
- Check the interactive documentation at `/api/docs`
- Review the detailed module documentation in the codebase
- Contact the development team for advanced integration support

---

**Last Updated:** August 2025  
**API Version:** 2.0.0  
**Status:** Production Ready
