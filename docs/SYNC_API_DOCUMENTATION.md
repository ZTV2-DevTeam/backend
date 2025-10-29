# FTV Sync API Documentation - Igazoláskezelő Integration

## Overview

The FTV Sync API provides read-only endpoints for external system integration, specifically designed for the **Igazoláskezelő** (Attendance Management System) to sync absence/attendance records with the FTV system.

### Key Features

- ✅ **External Token Authentication** - Uses a separate access token (not JWT)
- ✅ **Read-Only Access** - Safe integration with no data modification
- ✅ **Email-Based Linking** - Email address as common key between systems
- ✅ **Comprehensive Absence Data** - Full hiányzás (absence) record access
- ✅ **Class Organization** - Access to osztály (class) structure

---

## Authentication

### Token Configuration

The external access token is stored in `local_settings.py`:

```python
# External API Access Token (for Igazoláskezelő integration)
EXTERNAL_ACCESS_TOKEN = "your-secure-token-here-change-in-production"
```

⚠️ **Security Note**: Change this token in production to a long, random, secure string.

### Using the Token

Include the token in the `Authorization` header for all requests:

```
Authorization: Bearer your-secure-token-here-change-in-production
```

### Example Request

```bash
curl -H "Authorization: Bearer your-secure-token-here-change-in-production" \
     http://your-domain.com/api/sync/osztalyok
```

---

## API Endpoints

### Base URL

```
/api/sync/
```

---

## 1. Class (Osztály) Endpoints

### GET /api/sync/osztalyok

Get all classes in the system.

**Response**: `200 OK`

```json
[
  {
    "id": 1,
    "startYear": 2024,
    "szekcio": "F",
    "current_name": "9F",
    "tanev_id": 1,
    "tanev_name": "2024/2025"
  },
  {
    "id": 2,
    "startYear": 2023,
    "szekcio": "A",
    "current_name": "23A",
    "tanev_id": 1,
    "tanev_name": "2024/2025"
  }
]
```

**Fields:**
- `id`: Unique class identifier
- `startYear`: Year the class started
- `szekcio`: Class section (F, A, B, etc.)
- `current_name`: Display name for current school year
- `tanev_id`: School year ID (nullable)
- `tanev_name`: School year display name (nullable)

---

### GET /api/sync/osztaly/{osztaly_id}

Get detailed information for a specific class.

**Parameters:**
- `osztaly_id` (path, integer): The class ID

**Response**: `200 OK`

```json
{
  "id": 1,
  "startYear": 2024,
  "szekcio": "F",
  "current_name": "9F",
  "tanev_id": 1,
  "tanev_name": "2024/2025"
}
```

**Error Response**: `404 Not Found`

```json
{
  "detail": "Osztaly not found"
}
```

---

## 2. Absence (Hiányzás) Endpoints

### GET /api/sync/hianyzasok/osztaly/{osztaly_id}

Get all absence records for students in a specific class.

**Parameters:**
- `osztaly_id` (path, integer): The class ID

**Response**: `200 OK`

```json
[
  {
    "id": 123,
    "diak_id": 45,
    "diak_username": "kovacs.janos",
    "diak_email": "kovacs.janos@szlg.info",
    "diak_full_name": "Kovács János",
    "forgatas_id": 78,
    "forgatas_details": {
      "id": 78,
      "name": "Iskolai KaCsa forgatás",
      "description": "Heti iskolai műsor felvétele",
      "date": "2024-10-30",
      "timeFrom": "10:00:00",
      "timeTo": "12:00:00",
      "location_name": "SZLG Stúdió"
    },
    "date": "2024-10-30",
    "timeFrom": "10:00:00",
    "timeTo": "12:00:00",
    "excused": false,
    "unexcused": false,
    "auto_generated": true,
    "student_extra_time_before": 15,
    "student_extra_time_after": 30,
    "student_edited": true,
    "student_edit_timestamp": "2024-10-29T14:30:00",
    "student_edit_note": "Előkészület és utómunka miatt",
    "affected_classes": [3, 4]
  }
]
```

**Fields:**
- `id`: Unique absence record ID
- `diak_id`: Student user ID
- `diak_username`: Student username
- `diak_email`: Student email (**common key for linking**)
- `diak_full_name`: Student full name
- `forgatas_id`: Related filming session ID
- `forgatas_details`: Detailed filming session information
  - `name`: Filming session name
  - `description`: Session description
  - `date`: Session date
  - `timeFrom`: Start time
  - `timeTo`: End time
  - `location_name`: Location/partner name
- `date`: Absence date
- `timeFrom`: Absence start time
- `timeTo`: Absence end time
- `excused`: Whether absence is excused
- `unexcused`: Whether absence is unexcused
- `auto_generated`: Auto-created from assignment (vs. student-added)
- `student_extra_time_before`: Extra minutes before (student-submitted)
- `student_extra_time_after`: Extra minutes after (student-submitted)
- `student_edited`: Whether student modified the record
- `student_edit_timestamp`: When student last edited
- `student_edit_note`: Student's explanation for extra time
- `affected_classes`: List of affected class periods (0-8)

**Class Period Reference:**
```
0: 7:30-8:15   (0. óra)
1: 8:25-9:10   (1. óra)
2: 9:20-10:05  (2. óra)
3: 10:20-11:05 (3. óra)
4: 11:15-12:00 (4. óra)
5: 12:20-13:05 (5. óra)
6: 13:25-14:10 (6. óra)
7: 14:20-15:05 (7. óra)
8: 15:15-16:00 (8. óra)
```

---

### GET /api/sync/hianyzas/{absence_id}

Get detailed information for a specific absence record.

**Parameters:**
- `absence_id` (path, integer): The absence record ID

**Response**: `200 OK` - Same structure as individual items in `/hianyzasok/osztaly/` endpoint

**Error Response**: `404 Not Found`

```json
{
  "detail": "Absence not found"
}
```

---

### GET /api/sync/hianyzasok/user/{user_id}

Get all absence records for a specific user.

**Parameters:**
- `user_id` (path, integer): The user ID

**Response**: `200 OK` - Array of absence records (same structure as `/hianyzasok/osztaly/`)

**Error Response**: `404 Not Found`

```json
{
  "detail": "User not found"
}
```

---

## 3. Profile Endpoints

### GET /api/sync/profile/{email}

Get detailed user profile information using email as the common key.

**Parameters:**
- `email` (path, string): The user's email address

**Response**: `200 OK`

```json
{
  "id": 12,
  "user_id": 45,
  "username": "kovacs.janos",
  "email": "kovacs.janos@szlg.info",
  "first_name": "János",
  "last_name": "Kovács",
  "full_name": "Kovács János",
  "telefonszam": "+36 20 123 4567",
  "medias": true,
  "osztaly_id": 1,
  "osztaly_name": "9F",
  "stab_id": 3,
  "stab_name": "Hang",
  "radio_stab_id": 2,
  "radio_stab_name": "A2 rádió csapat (A2)",
  "admin_type": "none",
  "special_role": "none",
  "szerkeszto": false,
  "is_admin": false,
  "is_production_leader": false
}
```

**Fields:**
- `id`: Profile ID
- `user_id`: User ID
- `username`: Username
- `email`: Email address (**common key for linking**)
- `first_name`: First name
- `last_name`: Last name
- `full_name`: Full name (formatted)
- `telefonszam`: Phone number (nullable)
- `medias`: Whether user is a media student
- `osztaly_id`: Class ID (nullable)
- `osztaly_name`: Class display name (nullable)
- `stab_id`: Team/stab ID (nullable)
- `stab_name`: Team/stab name (nullable)
- `radio_stab_id`: Radio team ID (nullable, for 9F students)
- `radio_stab_name`: Radio team name (nullable)
- `admin_type`: Admin type (none, developer, teacher, system_admin)
- `special_role`: Special role (none, production_leader)
- `szerkeszto`: Can create filming sessions
- `is_admin`: Has admin permissions
- `is_production_leader`: Is production leader

**Error Response**: `404 Not Found`

```json
{
  "detail": "User not found"
}
```

---

## Integration Guide for Igazoláskezelő

### Common Key Strategy

**Email address** is the common key between FTV and Igazoláskezelő:

1. **User Lookup**: Use `/api/sync/profile/{email}` to find FTV user by email
2. **Get User Absences**: Use `user_id` from profile to call `/api/sync/hianyzasok/user/{user_id}`
3. **Link Records**: Match absence records in your system using email as the key

### Example Integration Flow

```javascript
// 1. Find user by email in FTV system
const email = "kovacs.janos@szlg.info";
const profileResponse = await fetch(`/api/sync/profile/${email}`, {
  headers: {
    'Authorization': 'Bearer YOUR_EXTERNAL_TOKEN'
  }
});
const profile = await profileResponse.json();

// 2. Get all absences for this user
const absencesResponse = await fetch(`/api/sync/hianyzasok/user/${profile.user_id}`, {
  headers: {
    'Authorization': 'Bearer YOUR_EXTERNAL_TOKEN'
  }
});
const absences = await absencesResponse.json();

// 3. Process absences in your system
absences.forEach(absence => {
  // Link to your database using email as key
  syncAbsenceRecord(absence, email);
});
```

### Syncing Strategy

**Option 1: User-Based Sync**
```
For each user in Igazoláskezelő:
  1. GET /api/sync/profile/{email}
  2. GET /api/sync/hianyzasok/user/{user_id}
  3. Compare and sync records
```

**Option 2: Class-Based Sync**
```
For each class:
  1. GET /api/sync/osztalyok (get all classes)
  2. For each osztaly_id:
     GET /api/sync/hianyzasok/osztaly/{osztaly_id}
  3. Match users by email and sync
```

**Option 3: On-Demand Sync**
```
When user requests sync in Igazoláskezelő:
  1. GET /api/sync/profile/{email}
  2. GET /api/sync/hianyzasok/user/{user_id}
  3. Update only this user's records
```

---

## Error Handling

### Common Error Responses

**401 Unauthorized** - Invalid or missing token
```json
{
  "detail": "Invalid external access token"
}
```

**404 Not Found** - Resource doesn't exist
```json
{
  "detail": "User not found"
}
```

**500 Internal Server Error** - Server error
```json
{
  "detail": "Internal server error message"
}
```

### Best Practices

1. **Always check response status** before processing data
2. **Handle 404 gracefully** - user/record may not exist in FTV
3. **Implement retry logic** for network errors
4. **Log all API calls** for debugging
5. **Cache class/profile data** to reduce API calls

---

## Security Considerations

### Token Management

- ✅ Store token securely (environment variables, secure config)
- ✅ Never commit token to version control
- ✅ Rotate token periodically
- ✅ Use HTTPS in production
- ✅ Log all access attempts

### Access Control

- ✅ Read-only access (no data modification)
- ✅ Token authentication only (no user sessions)
- ✅ Rate limiting (future enhancement)
- ✅ IP whitelist (optional, configure in settings)

---

## Testing the API

### Using curl

```bash
# Get all classes
curl -H "Authorization: Bearer your-token" \
     http://localhost:8000/api/sync/osztalyok

# Get specific class
curl -H "Authorization: Bearer your-token" \
     http://localhost:8000/api/sync/osztaly/1

# Get absences for class
curl -H "Authorization: Bearer your-token" \
     http://localhost:8000/api/sync/hianyzasok/osztaly/1

# Get profile by email
curl -H "Authorization: Bearer your-token" \
     http://localhost:8000/api/sync/profile/kovacs.janos@szlg.info
```

### Using Python

```python
import requests

TOKEN = "your-secure-token-here"
BASE_URL = "http://localhost:8000/api/sync"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Get all classes
response = requests.get(f"{BASE_URL}/osztalyok", headers=headers)
classes = response.json()
print(f"Found {len(classes)} classes")

# Get profile by email
email = "kovacs.janos@szlg.info"
response = requests.get(f"{BASE_URL}/profile/{email}", headers=headers)
profile = response.json()
print(f"User: {profile['full_name']}")

# Get user absences
user_id = profile['user_id']
response = requests.get(f"{BASE_URL}/hianyzasok/user/{user_id}", headers=headers)
absences = response.json()
print(f"Found {len(absences)} absences for {profile['full_name']}")
```

---

## API Documentation

Visit the interactive API documentation at:

```
http://your-domain.com/api/docs
```

The Swagger/OpenAPI interface allows you to:
- Test endpoints directly from the browser
- View detailed schema information
- See all available endpoints
- Try authentication with your token

---

## Support and Contact

For integration support or questions about the Sync API:

1. Review this documentation
2. Check the interactive API docs at `/api/docs`
3. Test endpoints using the provided examples
4. Contact the FTV development team for assistance

---

## Changelog

### Version 1.0 (October 2024)
- Initial release of Sync API
- External token authentication
- Class, absence, and profile endpoints
- Email-based user linking
- Read-only access for Igazoláskezelő integration

---

## Future Enhancements

Planned features for future versions:

- [ ] Rate limiting for API calls
- [ ] Webhook support for real-time updates
- [ ] Bulk data export endpoints
- [ ] Advanced filtering options
- [ ] Pagination for large datasets
- [ ] Date range filtering for absences
- [ ] IP whitelist configuration
- [ ] API usage statistics

---

**Last Updated**: October 29, 2024  
**API Version**: 1.0  
**Documentation Version**: 1.0
