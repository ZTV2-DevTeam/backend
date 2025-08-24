# FTV Backend API - Complete Documentation

## 📚 Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Modules](#api-modules)
4. [Common Patterns](#common-patterns)
5. [Error Handling](#error-handling)
6. [Examples](#examples)

---

## 🎥 Overview

The FTV Backend API is a comprehensive REST API built with Django Ninja for managing a school media system. It provides complete functionality for student/teacher management, media equipment tracking, filming session planning, radio program management, and institutional collaboration.

**Base URL:** `http://your-domain.com/api/`

**Content-Type:** `application/json` (for POST/PUT requests)

**Authentication:** JWT Bearer tokens required for most endpoints

**Interactive Documentation:** Visit `/api/docs` when the server is running

---

## 🔐 Authentication

### JWT Authentication System

All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Authentication Endpoints

#### POST `/api/login`
**Description:** User login with username/password  
**Content-Type:** `application/x-www-form-urlencoded`  
**Request Body:**
```
username=testuser&password=password123
```

**Success Response (200):**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": 123,
  "username": "testuser",
  "first_name": "Test",
  "last_name": "User",
  "email": "test@example.com",
  "telefonszam": "+36301234567",
  "medias": true,
  "admin_type": "teacher",
  "is_class_teacher": true,
  "stab_name": "Stúdió Stáb",
  "radio_stab_name": "Morning Team (MT)",
  "osztaly_name": "12A",
  "is_second_year_radio": false
}
```

**Error Response (401):**
```json
{
  "message": "Unauthorized"
}
```

#### GET `/api/profile`
**Description:** Get current user profile  
**Authentication:** Required

**Success Response (200):** Same as login response

#### POST `/api/refresh-token`
**Description:** Refresh JWT token  
**Authentication:** Required

**Success Response (200):**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "Token refreshed successfully"
}
```

#### POST `/api/logout`
**Description:** User logout (client should discard token)  
**Authentication:** Required

#### POST `/api/forgot-password`
**Description:** Initiate password reset  
**Request Body:**
```json
{
  "email": "user@example.com"
}
```

#### GET `/api/verify-reset-token/{token}`
**Description:** Verify password reset token  
**Response:**
```json
{
  "valid": true
}
```

#### POST `/api/reset-password`
**Description:** Complete password reset  
**Request Body:**
```json
{
  "token": "reset-token-here",
  "password": "newpassword123",
  "confirmPassword": "newpassword123"
}
```

---

## 📋 API Modules

### 🏠 Core API (`/api/`)

#### GET `/api/hello`
**Description:** Basic test endpoint  
**Parameters:**
- `name` (optional): Name to greet

**Response:**
```json
"Hello, World!"
```

#### GET `/api/test-auth`
**Description:** API status and authentication check

**Response:**
```json
{
  "message": "API is working!",
  "user_authenticated": true,
  "timestamp": "2024-03-15T14:30:00Z"
}
```

#### GET `/api/permissions`
**Description:** Get comprehensive user permissions and roles  
**Authentication:** Required

**Response:**
```json
{
  "user_info": {
    "id": 123,
    "username": "testuser",
    "full_name": "Test User",
    "email": "test@example.com",
    "is_staff": true,
    "telefonszam": "+36301234567",
    "has_profile": true
  },
  "permissions": {
    "is_admin": true,
    "is_teacher_admin": true,
    "can_manage_forgatas": true,
    "can_view_all_users": true,
    "can_create_forgatas": true
  },
  "display_properties": {
    "show_admin_menu": true,
    "show_teacher_menu": true,
    "dashboard_widgets": ["announcements", "my_forgatas", "class_info"],
    "navigation_items": ["dashboard", "forgatas", "users", "profile"]
  },
  "role_info": {
    "admin_type": "teacher",
    "primary_role": "teacher_admin",
    "roles": ["Médiatanár", "Osztályfőnök"],
    "class_assignment": {
      "id": 1,
      "display_name": "12A"
    }
  }
}
```

#### GET `/api/tanev-config-status`
**Description:** System configuration status (admin only)  
**Authentication:** Required (system admin)

**Response:**
```json
{
  "config_necessary": true,
  "system_admin_setup_required": false,
  "current_tanev": {
    "id": 1,
    "display_name": "2024/2025",
    "is_active": true
  },
  "missing_components": ["equipment_types", "equipment"],
  "setup_steps": [
    {
      "step": "basic_config",
      "name": "Alapvető rendszerbeállítások",
      "required": true,
      "completed": true,
      "description": "Rendszer alapbeállításainak konfigurálása"
    }
  ]
}
```

---

### 👥 Users API (`/api/users/`)

#### GET `/api/users`
**Description:** List all user profiles (admin only)  
**Authentication:** Required (admin)

**Response:**
```json
[
  {
    "id": 123,
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "telefonszam": "+36301234567",
    "medias": true,
    "admin_type": "teacher",
    "is_class_teacher": true,
    "stab_name": "Stúdió Stáb",
    "radio_stab_name": "Morning Team (MT)",
    "osztaly_name": "12A",
    "is_second_year_radio": false
  }
]
```

#### GET `/api/users/{id}`
**Description:** Get specific user profile (admin only)  
**Authentication:** Required (admin)

#### GET `/api/users/radio-students`
**Description:** Get 9F radio students (admin only)  
**Authentication:** Required (admin)

#### GET `/api/users/{id}/availability`
**Description:** Check user availability  
**Authentication:** Required  
**Parameters:**
- `start_datetime`: Start time (ISO format)
- `end_datetime`: End time (ISO format)

**Response:**
```json
{
  "available": false,
  "user_id": 123,
  "conflicts": [
    {
      "type": "absence",
      "reason": "Medical appointment",
      "start": "2024-03-15",
      "end": "2024-03-15"
    },
    {
      "type": "radio_session",
      "description": "Morning Team rádiós összejátszás",
      "date": "2024-03-15",
      "time_from": "14:00:00",
      "time_to": "16:00:00"
    }
  ],
  "is_radio_student": true
}
```

#### GET `/api/users/active`
**Description:** Get active users (now and today)  
**Authentication:** Required

**Response:**
```json
{
  "active_now": [
    {
      "user_id": 123,
      "full_name": "Test User",
      "last_login_time": "2024-03-15T14:25:00Z",
      "active": true
    }
  ],
  "active_today": [
    {
      "user_id": 124,
      "full_name": "Another User",
      "last_login_time": "2024-03-15T09:15:00Z",
      "active": false
    }
  ]
}
```

---

### 🤝 Partners API (`/api/partners/`)

#### GET `/api/partners`
**Description:** List all partners (public)

**Response:**
```json
[
  {
    "id": 1,
    "name": "ABC Corporation",
    "address": "123 Main Street, City",
    "institution": "Technology",
    "imageURL": "https://example.com/logo.png"
  }
]
```

#### GET `/api/partners/{id}`
**Description:** Get specific partner (public)

#### POST `/api/partners`
**Description:** Create new partner  
**Authentication:** Required  
**Request Body:**
```json
{
  "name": "New Partner Corp",
  "address": "456 Business Ave",
  "institution": "Education",
  "imageURL": "https://example.com/newlogo.png"
}
```

#### PUT `/api/partners/{id}`
**Description:** Update partner  
**Authentication:** Required

#### DELETE `/api/partners/{id}`
**Description:** Delete partner  
**Authentication:** Required

---

### 🔧 Equipment API (`/api/equipment/`)

#### GET `/api/equipment-types`
**Description:** List all equipment types  
**Authentication:** Required

**Response:**
```json
[
  {
    "id": 1,
    "name": "Kamera",
    "emoji": "📹",
    "equipment_count": 5
  },
  {
    "id": 2,
    "name": "Mikrofon",
    "emoji": "🎤",
    "equipment_count": 12
  }
]
```

#### POST `/api/equipment-types`
**Description:** Create new equipment type (admin only)  
**Authentication:** Required (admin)  
**Request Body:**
```json
{
  "name": "Világítás",
  "emoji": "💡"
}
```

#### GET `/api/equipment`
**Description:** List all equipment  
**Authentication:** Required  
**Parameters:**
- `functional_only` (optional): Filter for working equipment only

**Response:**
```json
[
  {
    "id": 1,
    "nickname": "Main Camera",
    "brand": "Canon",
    "model": "XA40",
    "serial_number": "CN123456789",
    "equipment_type": {
      "id": 1,
      "name": "Kamera",
      "emoji": "📹",
      "equipment_count": 5
    },
    "functional": true,
    "notes": "Primary studio camera",
    "display_name": "Main Camera (Canon XA40)"
  }
]
```

#### GET `/api/equipment/{id}`
**Description:** Get specific equipment details  
**Authentication:** Required

#### GET `/api/equipment/by-type/{type_id}`
**Description:** Get equipment by type  
**Authentication:** Required  
**Parameters:**
- `functional_only` (optional): Filter for working equipment only

#### POST `/api/equipment`
**Description:** Create new equipment (admin only)  
**Authentication:** Required (admin)  
**Request Body:**
```json
{
  "nickname": "Studio Camera 2",
  "brand": "Sony",
  "model": "FX30",
  "serial_number": "SN987654321",
  "equipment_type_id": 1,
  "functional": true,
  "notes": "Secondary studio camera"
}
```

#### PUT `/api/equipment/{id}`
**Description:** Update equipment (admin only)  
**Authentication:** Required (admin)

#### DELETE `/api/equipment/{id}`
**Description:** Delete equipment (admin only)  
**Authentication:** Required (admin)

#### GET `/api/equipment/{id}/availability`
**Description:** Check equipment availability  
**Authentication:** Required  
**Parameters:**
- `start_date`: Start date (YYYY-MM-DD)
- `start_time`: Start time (HH:MM)
- `end_date`: End date (YYYY-MM-DD, optional)
- `end_time`: End time (HH:MM, optional)

**Response:**
```json
{
  "equipment_id": 1,
  "available": false,
  "conflicts": [
    {
      "type": "filming_session",
      "forgatas_id": 15,
      "forgatas_name": "Morning Show Recording",
      "date": "2024-03-15",
      "time_from": "09:00:00",
      "time_to": "11:00:00",
      "location": "Studio A",
      "type_display": "Rendes"
    }
  ]
}
```

#### GET `/api/equipment/availability-overview`
**Description:** Get availability overview for all equipment  
**Authentication:** Required  
**Parameters:**
- `date`: Date to check (YYYY-MM-DD)
- `type_id` (optional): Filter by equipment type

---

### 🎬 Production API (`/api/production/`)

#### GET `/api/production/contact-persons`
**Description:** List all contact persons  
**Authentication:** Required

**Response:**
```json
[
  {
    "id": 1,
    "name": "John Smith",
    "email": "john@partner.com",
    "phone": "+36301234567"
  }
]
```

#### POST `/api/production/contact-persons`
**Description:** Create new contact person (admin only)  
**Authentication:** Required (admin)  
**Request Body:**
```json
{
  "name": "Jane Doe",
  "email": "jane@partner.com",
  "phone": "+36307654321"
}
```

#### GET `/api/production/filming-sessions`
**Description:** List filming sessions  
**Authentication:** Required  
**Parameters:**
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date
- `type` (optional): Filter by type (kacsa, rendes, rendezveny, egyeb)

**Response:**
```json
[
  {
    "id": 15,
    "name": "Morning Show Recording",
    "description": "Weekly morning show episode",
    "date": "2024-03-15",
    "time_from": "09:00:00",
    "time_to": "11:00:00",
    "location": {
      "id": 1,
      "name": "Partner School",
      "address": "123 School St"
    },
    "contact_person": {
      "id": 1,
      "name": "John Smith",
      "email": "john@partner.com",
      "phone": "+36301234567"
    },
    "notes": "Bring extra batteries",
    "type": "rendes",
    "type_display": "Rendes",
    "related_kacsa": null,
    "equipment_ids": [1, 2, 5],
    "equipment_count": 3,
    "tanev": {
      "id": 1,
      "display_name": "2024/2025",
      "is_active": true
    }
  }
]
```

#### GET `/api/production/filming-sessions/{id}`
**Description:** Get specific filming session  
**Authentication:** Required

#### GET `/api/production/filming-sessions/types`
**Description:** Get available filming types (public)

**Response:**
```json
[
  {"value": "kacsa", "label": "KaCsa"},
  {"value": "rendes", "label": "Rendes"},
  {"value": "rendezveny", "label": "Rendezvény"},
  {"value": "egyeb", "label": "Egyéb"}
]
```

#### POST `/api/production/filming-sessions`
**Description:** Create new filming session (admin/teacher)  
**Authentication:** Required (admin/teacher)  
**Request Body:**
```json
{
  "name": "Afternoon Interview",
  "description": "Interview with local mayor",
  "date": "2024-03-20",
  "time_from": "14:00",
  "time_to": "16:00",
  "location_id": 1,
  "contact_person_id": 1,
  "notes": "Formal attire required",
  "type": "rendezveny",
  "equipment_ids": [1, 3, 7]
}
```

#### PUT `/api/production/filming-sessions/{id}`
**Description:** Update filming session (admin/teacher)  
**Authentication:** Required (admin/teacher)

#### DELETE `/api/production/filming-sessions/{id}`
**Description:** Delete filming session (admin only)  
**Authentication:** Required (admin)

---

### 📻 Radio API (`/api/radio/`)

#### GET `/api/radio-stabs`
**Description:** List all radio stabs  
**Authentication:** Required

**Response:**
```json
[
  {
    "id": 1,
    "name": "Morning News Team",
    "team_code": "MNT",
    "description": "Daily morning news broadcast",
    "member_count": 8
  }
]
```

#### POST `/api/radio-stabs`
**Description:** Create new radio stab (admin only)  
**Authentication:** Required (admin)  
**Request Body:**
```json
{
  "name": "Evening Talk Show",
  "team_code": "ETS",
  "description": "Weekly evening discussion program"
}
```

#### GET `/api/radio-sessions`
**Description:** List radio sessions  
**Authentication:** Required  
**Parameters:**
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date

**Response:**
```json
[
  {
    "id": 5,
    "radio_stab": {
      "id": 1,
      "name": "Morning News Team",
      "team_code": "MNT"
    },
    "date": "2024-03-15",
    "time_from": "14:00:00",
    "time_to": "16:00:00",
    "description": "Weekly news review and planning",
    "participant_count": 6
  }
]
```

#### POST `/api/radio-sessions`
**Description:** Create new radio session (admin only)  
**Authentication:** Required (admin)  
**Request Body:**
```json
{
  "radio_stab_id": 1,
  "date": "2024-03-20",
  "time_from": "15:00",
  "time_to": "17:00",
  "description": "Special guest interview session",
  "participant_ids": [10, 11, 12, 13]
}
```

---

### 🏫 Academic API (`/api/`)

#### GET `/api/school-years`
**Description:** List all school years  
**Authentication:** Required

**Response:**
```json
[
  {
    "id": 1,
    "start_date": "2024-09-01",
    "end_date": "2025-06-30",
    "start_year": 2024,
    "end_year": 2025,
    "display_name": "2024/2025",
    "is_active": true,
    "osztaly_count": 12
  }
]
```

#### GET `/api/school-years/active`
**Description:** Get currently active school year  
**Authentication:** Required

#### POST `/api/school-years`
**Description:** Create new school year (admin only)  
**Authentication:** Required (admin)  
**Request Body:**
```json
{
  "start_date": "2025-09-01",
  "end_date": "2026-06-30"
}
```

#### GET `/api/classes`
**Description:** List all classes  
**Authentication:** Required

**Response:**
```json
[
  {
    "id": 1,
    "start_year": 2020,
    "szekcio": "A",
    "display_name": "12A",
    "current_display_name": "12A",
    "tanev": {
      "id": 1,
      "display_name": "2024/2025"
    },
    "student_count": 25
  }
]
```

#### GET `/api/classes/by-section/{section}`
**Description:** Get classes by section  
**Authentication:** Required

#### POST `/api/classes`
**Description:** Create new class (admin only)  
**Authentication:** Required (admin)  
**Request Body:**
```json
{
  "start_year": 2024,
  "szekcio": "F",
  "tanev_id": 1
}
```

---

### 📢 Communications API

#### GET `/api/announcements`
**Description:** List announcements  
**Authentication:** Required

#### POST `/api/announcements`
**Description:** Create announcement (admin/teacher)  
**Authentication:** Required (admin/teacher)

---

### 🏢 Organization API

#### GET `/api/stabs`
**Description:** List all stabs (teams)  
**Authentication:** Required

#### GET `/api/roles`
**Description:** List all roles  
**Authentication:** Required

---

### 📋 Absence Management APIs

#### GET `/api/absences`
**Description:** List user absences  
**Authentication:** Required

#### POST `/api/absences`
**Description:** Create absence request  
**Authentication:** Required

---

### 🔧 Configuration API

#### GET `/api/config`
**Description:** Get system configuration (admin only)  
**Authentication:** Required (admin)

---

### 👨‍💼 User Management API

#### GET `/api/user-management/users`
**Description:** Comprehensive user CRUD operations (admin only)  
**Authentication:** Required (admin)

#### POST `/api/user-management/users`
**Description:** Create new user (admin only)  
**Authentication:** Required (admin)

---

## 🔄 Common Patterns

### Request Format
```bash
# GET requests
curl -H "Authorization: Bearer {token}" \
     "http://localhost:8000/api/endpoint?param=value"

# POST requests
curl -X POST \
     -H "Authorization: Bearer {token}" \
     -H "Content-Type: application/json" \
     -d '{"field":"value"}' \
     "http://localhost:8000/api/endpoint"
```

### Response Format
**Success responses:**
```json
{
  "id": 123,
  "field": "value",
  "...": "other fields"
}
```

**Error responses:**
```json
{
  "message": "Detailed error description in Hungarian"
}
```

### Pagination
Some endpoints support pagination:
```json
{
  "results": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_pages": 5,
    "total_items": 95,
    "has_next": true,
    "has_previous": false
  }
}
```

---

## ⚠️ Error Handling

### HTTP Status Codes
- **200**: Success
- **201**: Created
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (authentication failed)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **409**: Conflict (scheduling conflicts, duplicates)
- **500**: Internal Server Error

### Common Error Messages
```json
{
  "message": "Unauthorized"
}
```

```json
{
  "message": "Adminisztrátor jogosultság szükséges"
}
```

```json
{
  "message": "Eszköz nem található"
}
```

```json
{
  "message": "Hibás dátum formátum"
}
```

---

## 💡 Examples

### Complete Authentication Flow
```javascript
// 1. Login
const loginResponse = await fetch('/api/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded'
  },
  body: 'username=testuser&password=password123'
});

const loginData = await loginResponse.json();
const token = loginData.token;

// 2. Use token for authenticated requests
const profileResponse = await fetch('/api/profile', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const profile = await profileResponse.json();

// 3. Make API calls
const partnersResponse = await fetch('/api/partners', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const partners = await partnersResponse.json();
```

### Equipment Availability Check
```javascript
const checkAvailability = async (equipmentId, startDate, startTime, endDate, endTime) => {
  const params = new URLSearchParams({
    start_date: startDate,
    start_time: startTime,
    end_date: endDate,
    end_time: endTime
  });
  
  const response = await fetch(
    `/api/equipment/${equipmentId}/availability?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  return await response.json();
};

// Usage
const availability = await checkAvailability(1, '2024-03-15', '14:00', '2024-03-15', '16:00');
if (!availability.available) {
  console.log('Conflicts:', availability.conflicts);
}
```

### Create Filming Session
```javascript
const createFilmingSession = async (sessionData) => {
  const response = await fetch('/api/production/filming-sessions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(sessionData)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }
  
  return await response.json();
};

// Usage
const newSession = await createFilmingSession({
  name: 'Documentary Filming',
  description: 'Filming for history documentary',
  date: '2024-03-20',
  time_from: '10:00',
  time_to: '14:00',
  type: 'rendes',
  equipment_ids: [1, 2, 5],
  location_id: 1,
  contact_person_id: 1
});
```

### User Permission Check
```javascript
const checkUserPermissions = async () => {
  const response = await fetch('/api/permissions', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  
  // Check specific permissions
  if (data.permissions.can_manage_forgatas) {
    // Show filming session management UI
  }
  
  if (data.permissions.is_admin) {
    // Show admin panel
  }
  
  // Use display properties for UI
  if (data.display_properties.show_admin_menu) {
    // Show admin menu items
  }
  
  return data;
};
```

---

## 🚀 Getting Started

1. **Authentication**: Start with `/api/login` to get JWT token
2. **User Context**: Call `/api/profile` to understand user permissions  
3. **Explore Data**: Use appropriate endpoints based on user role
4. **Handle Errors**: Implement proper error handling for all API calls
5. **Interactive Docs**: Visit `/api/docs` for live testing

## 🔑 Permission Levels

- **Public**: No authentication required
- **Authenticated**: Valid JWT token required
- **Admin**: System admin, teacher admin, or developer admin
- **Teacher**: Teacher admin permissions
- **System Admin**: System administrator only

This API provides complete functionality for educational media management with role-based access control and comprehensive error handling.
