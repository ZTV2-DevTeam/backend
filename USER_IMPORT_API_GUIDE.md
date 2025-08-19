# FTV User Import API Guide

This guide explains how to use the new bulk user import functionality to create users, profiles, radio stabs, and classes from Excel-like data.

## Overview

The User Import API allows you to:
- Create multiple users at once from structured data
- Automatically generate usernames from email addresses
- Create radio stabs with naming format: "YYYY XX" (e.g., "2025 A1")
- Create classes based on start year and section (e.g., "2023F")
- Set user profiles with proper permissions
- Assign class teachers automatically
- Send first-login emails to new users

## API Endpoints

### Base URL: `/api/user-import/`

All endpoints require authentication with JWT token in the Authorization header:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

### 1. Get Import Template
**GET** `/api/user-import/import-template`

Returns the data structure template for importing users.

**Response:**
```json
{
    "description": "FTV felhasználó import sablon",
    "required_fields": ["vezetekNev", "keresztNev", "email"],
    "optional_fields": ["telefonszam", "stab", "kezdesEve", "tagozat", "radio", "gyartasvezeto", "mediatana", "osztalyfonok", "osztalyai"],
    "field_descriptions": {
        "vezetekNev": "Vezetéknév (kötelező)",
        "keresztNev": "Keresztnév (kötelező)", 
        "telefonszam": "Telefonszám (+36301234567 formátum)",
        "email": "Email cím (kötelező, ebből generálódik a felhasználónév)",
        "stab": "Stáb neve (pl. 'A stáb', 'B stáb')",
        "kezdesEve": "Tanulmányok kezdésének éve (pl. '2025')",
        "tagozat": "Tagozat (pl. 'F', 'A', 'B')",
        "radio": "Rádiós csapat kód (pl. 'A1', 'B3')",
        "gyartasvezeto": "'Igen' ha gyártásvezető jogot kap",
        "mediatana": "'Igen' ha médiatanár jogot kap",
        "osztalyfonok": "'Igen' ha osztályfőnök jogot kap",
        "osztalyai": "Osztályok amiket vezet (pl. '2023F,2024F')"
    },
    "example_data": [...]
}
```

### 2. Validate Import Data
**POST** `/api/user-import/validate-import`

Validates import data without creating users (dry run).

**Request Body:**
```json
{
    "users": [
        {
            "vezetekNev": "Nagy",
            "keresztNev": "Imre",
            "telefonszam": "+36301234567",
            "email": "nagy.imre.25f@szlgbp.hu",
            "stab": "B stáb",
            "kezdesEve": "2025",
            "tagozat": "F",
            "radio": "",
            "gyartasvezeto": "",
            "mediatana": "",
            "osztalyfonok": "",
            "osztalyai": ""
        }
    ],
    "dry_run": true,
    "send_emails": false
}
```

**Response:**
```json
{
    "success": true,
    "total_users": 1,
    "created_users": 0,
    "created_classes": 1,
    "created_stabs": 1,
    "created_radio_stabs": 0,
    "errors": [],
    "warnings": [],
    "user_details": [
        {
            "index": 1,
            "username": "nagy.imre.25f",
            "full_name": "Nagy Imre",
            "email": "nagy.imre.25f@szlgbp.hu",
            "admin_type": "none",
            "special_role": "none",
            "osztaly": "2025F",
            "stab": "B stáb",
            "radio_stab": null,
            "success": true
        }
    ]
}
```

### 3. Import Users
**POST** `/api/user-import/import-users`

Creates users from the provided data.

**Request Body:**
```json
{
    "users": [
        {
            "vezetekNev": "Nagy",
            "keresztNev": "Imre",
            "telefonszam": "+36301234567",
            "email": "nagy.imre.25f@szlgbp.hu",
            "stab": "B stáb",
            "kezdesEve": "2025",
            "tagozat": "F",
            "radio": "",
            "gyartasvezeto": "",
            "mediatana": "",
            "osztalyfonok": "",
            "osztalyai": ""
        }
    ],
    "dry_run": false,
    "send_emails": true
}
```

**Response:** Same structure as validation, but with actual creation counts.

### 4. Import Sample Data
**POST** `/api/user-import/import-sample-data?dry_run=false&send_emails=false`

Imports the pre-defined sample data from the original attachment.

**Query Parameters:**
- `dry_run`: boolean (default: false) - If true, validates only
- `send_emails`: boolean (default: false) - If true, sends first-login emails

## Data Structure

### User Import Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `vezetekNev` | ✓ | Last name | "Nagy" |
| `keresztNev` | ✓ | First name | "Imre" |
| `email` | ✓ | Email address (used for username generation) | "nagy.imre.25f@szlgbp.hu" |
| `telefonszam` | | Phone number | "+36301234567" |
| `stab` | | Team/stab name | "A stáb", "B stáb" |
| `kezdesEve` | | Start year for studies | "2025" |
| `tagozat` | | Section/track | "F", "A", "B" |
| `radio` | | Radio team code | "A1", "B3", "B4" |
| `gyartasvezeto` | | Production leader permission | "Igen" or "" |
| `mediatana` | | Media teacher permission | "Igen" or "" |
| `osztalyfonok` | | Class teacher permission | "Igen" or "" |
| `osztalyai` | | Classes to manage (comma-separated) | "2023F,2024F" |

### Generated Objects

1. **Username Generation:**
   - Extracted from email address (part before @)
   - `nagy.imre.25f@szlgbp.hu` → `nagy.imre.25f`

2. **Radio Stab Creation:**
   - Format: `{kezdesEve} {radio}`
   - Example: Start year "2025" + radio "A1" → "2025 A1"

3. **Class Creation:**
   - Format: `{kezdesEve}{tagozat}`
   - Example: Start year "2025" + section "F" → "2025F"

4. **Permission Assignment:**
   - `mediatana = "Igen"` → `admin_type = "teacher"`
   - `gyartasvezeto = "Igen"` → `special_role = "production_leader"`
   - `osztalyfonok = "Igen"` → User becomes class teacher for specified classes

## Example Usage

### JavaScript/TypeScript
```javascript
// 1. Get the template first
const templateResponse = await fetch('/api/user-import/import-template', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
const template = await templateResponse.json();

// 2. Validate your data
const validationResponse = await fetch('/api/user-import/validate-import', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
        users: [
            {
                "vezetekNev": "Test",
                "keresztNev": "User",
                "email": "test.user@example.com",
                "stab": "A stáb",
                "kezdesEve": "2025",
                "tagozat": "F"
            }
        ],
        dry_run: true,
        send_emails: false
    })
});
const validation = await validationResponse.json();

// 3. If validation passes, import the users
if (validation.success) {
    const importResponse = await fetch('/api/user-import/import-users', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            users: [
                {
                    "vezetekNev": "Test",
                    "keresztNev": "User",
                    "email": "test.user@example.com",
                    "stab": "A stáb",
                    "kezdesEve": "2025",
                    "tagozat": "F"
                }
            ],
            dry_run: false,
            send_emails: true
        })
    });
    const result = await importResponse.json();
    console.log('Import result:', result);
}
```

### Python
```python
import requests

# Authentication
login_response = requests.post('http://localhost:8000/api/login', data={
    'username': 'admin',
    'password': 'your_password'
})
token = login_response.json()['token']

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Import users
import_data = {
    "users": [
        {
            "vezetekNev": "Test",
            "keresztNev": "User", 
            "email": "test.user@example.com",
            "stab": "A stáb",
            "kezdesEve": "2025",
            "tagozat": "F"
        }
    ],
    "dry_run": False,
    "send_emails": True
}

response = requests.post(
    'http://localhost:8000/api/user-import/import-users',
    json=import_data,
    headers=headers
)

result = response.json()
print(f"Created {result['created_users']} users")
```

## Sample Data Import

The API includes a convenient endpoint to import the exact data from your attachment:

```bash
curl -X POST "http://localhost:8000/api/user-import/import-sample-data?dry_run=false&send_emails=false" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

This will create:
- 17 users with their profiles
- Multiple classes (2021F, 2022F, 2023F, 2024F, 2025F)
- Two stabs (A stáb, B stáb)
- Three radio stabs (2022 A1, 2022 B3, 2022 B4)
- Proper permission assignments for teachers and production leaders

## Error Handling

The API provides detailed error information:

```json
{
    "success": false,
    "total_users": 2,
    "created_users": 1,
    "errors": [
        "Felhasználónév már létezik: existing.user",
        "Email cím már létezik: existing@example.com"
    ],
    "warnings": [
        "Első bejelentkezési email elküldve: new.user@example.com"
    ],
    "user_details": [
        {
            "index": 1,
            "success": true,
            "username": "new.user"
        },
        {
            "index": 2,
            "success": false,
            "errors": ["Felhasználónév már létezik: existing.user"]
        }
    ]
}
```

## Best Practices

1. **Always validate first:** Use the validation endpoint before actual import
2. **Handle duplicates:** Check error messages for existing usernames/emails
3. **Use dry run:** Test your data with `dry_run: true` first
4. **Email management:** Consider `send_emails: false` for testing
5. **Batch processing:** Process users in smaller batches for large datasets
6. **Permission verification:** Ensure you have system admin permissions

## Permissions Required

- **System Admin:** Required for all import operations
- **Authentication:** Valid JWT token required
- **CSRF:** Disabled for API endpoints

## Generated Objects Summary

From the sample data, the import will create:

**Classes:**
- 2021F, 2022F, 2023F, 2024F, 2025F

**Stabs:**
- A stáb, B stáb

**Radio Stabs:**
- 2022 A1, 2022 B3, 2022 B4

**User Types:**
- Students (majority)
- Media teachers (Csanádi, Horváth, Tóth, Sibak)
- Production leaders (Minta Katalin, Riport Erik, Nagy Ernő)
- Class teachers (Horváth Bence for 2022F)

This provides a complete user management solution for importing large datasets while maintaining data integrity and proper permissions.
