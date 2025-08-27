# Updated Absence API Documentation

## 📋 Overview

The Absence (Tavollet) API has been updated to support datetime fields instead of date-only fields. This provides more precise absence tracking with hour-level granularity.

## 🔄 Field Changes

| Field | Before | After | Description |
|-------|--------|-------|-------------|
| `start_date` | Date (YYYY-MM-DD) | DateTime (ISO 8601) | Absence start with time |
| `end_date` | Date (YYYY-MM-DD) | DateTime (ISO 8601) | Absence end with time |

## 📡 API Endpoints

### GET /api/absences

Get list of absences with optional filtering.

**Parameters:**
- `user_id` (int, optional): Filter by user ID (admin only)
- `start_date` (string, optional): Filter absences ending after this datetime (ISO format)
- `end_date` (string, optional): Filter absences starting before this datetime (ISO format)
- `my_absences` (boolean, optional): Return only current user's absences

**Example Request:**
```
GET /api/absences?start_date=2024-03-15T00:00:00Z&end_date=2024-03-31T23:59:59Z
Authorization: Bearer {jwt_token}
```

**Example Response:**
```json
[
  {
    "id": 1,
    "user": {
      "id": 123,
      "username": "john.doe",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "Doe John"
    },
    "start_date": "2024-03-15T09:00:00Z",
    "end_date": "2024-03-16T17:00:00Z",
    "reason": "Medical appointment",
    "denied": false,
    "approved": true,
    "duration_days": 2,
    "status": "jóváhagyva"
  }
]
```

### GET /api/absences/{absence_id}

Get specific absence details.

**Parameters:**
- `absence_id` (int): Absence ID

**Example Response:**
```json
{
  "id": 1,
  "user": {
    "id": 123,
    "username": "john.doe",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "Doe John"
  },
  "start_date": "2024-03-15T09:00:00Z",
  "end_date": "2024-03-16T17:00:00Z",
  "reason": "Medical appointment",
  "denied": false,
  "approved": true,
  "duration_days": 2,
  "status": "jóváhagyva"
}
```

### POST /api/absences

Create a new absence request.

**Request Body:**
```json
{
  "user_id": 123,
  "start_date": "2024-03-15T09:00:00Z",
  "end_date": "2024-03-16T17:00:00Z",
  "reason": "Medical appointment"
}
```

**Field Descriptions:**
- `user_id` (int, optional): Target user ID. If not provided, creates absence for current user
- `start_date` (string, required): Absence start datetime in ISO format
- `end_date` (string, required): Absence end datetime in ISO format
- `reason` (string, optional): Reason for absence (max 500 characters)

**Response:** Returns created absence object (same format as GET)

**Status Codes:**
- `201`: Absence created successfully
- `400`: Invalid data or overlapping absence
- `401`: Authentication required or insufficient permissions

### PUT /api/absences/{absence_id}

Update an existing absence.

**Parameters:**
- `absence_id` (int): Absence ID to update

**Request Body:**
```json
{
  "start_date": "2024-03-15T10:00:00Z",
  "end_date": "2024-03-16T16:00:00Z",
  "reason": "Updated medical appointment"
}
```

**Field Descriptions:**
- All fields are optional
- `start_date` (string): New start datetime
- `end_date` (string): New end datetime
- `reason` (string): Updated reason
- `denied` (boolean): Admin only - deny/undeny absence
- `approved` (boolean): Admin only - approve/unapprove absence

**Response:** Returns updated absence object

### PUT /api/absences/{absence_id}/approve

Approve an absence request (admin only).

**Parameters:**
- `absence_id` (int): Absence ID to approve

**Response:** Returns updated absence object with `approved: true`

### PUT /api/absences/{absence_id}/deny

Deny an absence request (admin only).

**Parameters:**
- `absence_id` (int): Absence ID to deny

**Response:** Returns updated absence object with `denied: true`

### PUT /api/absences/{absence_id}/reset

Reset absence status (admin only).

**Parameters:**
- `absence_id` (int): Absence ID to reset

**Response:** Returns updated absence object with `denied: false, approved: false`

### DELETE /api/absences/{absence_id}

Delete an absence request.

**Parameters:**
- `absence_id` (int): Absence ID to delete

**Response:**
```json
{
  "message": "Távollét 'John Doe (2024-03-15 09:00 - 2024-03-16 17:00)' sikeresen törölve"
}
```

### GET /api/absences/user/{user_id}/conflicts

Check for absence conflicts for a specific user.

**Parameters:**
- `user_id` (int): User ID to check
- `start_date` (string, required): Check period start (ISO datetime)
- `end_date` (string, required): Check period end (ISO datetime)

**Example Request:**
```
GET /api/absences/user/123/conflicts?start_date=2024-03-15T09:00:00Z&end_date=2024-03-16T17:00:00Z
Authorization: Bearer {jwt_token}
```

**Example Response:**
```json
{
  "user": {
    "id": 123,
    "username": "john.doe",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "Doe John"
  },
  "check_period": {
    "start_date": "2024-03-15T09:00:00Z",
    "end_date": "2024-03-16T17:00:00Z"
  },
  "has_conflicts": true,
  "conflicts": [
    {
      "id": 1,
      "start_date": "2024-03-15T08:00:00Z",
      "end_date": "2024-03-15T12:00:00Z",
      "reason": "Doctor appointment",
      "status": "jóváhagyva"
    }
  ]
}
```

## 🕐 DateTime Format Guidelines

### Accepted Formats

1. **UTC with Z suffix (Recommended):**
   ```
   2024-03-15T09:00:00Z
   ```

2. **With timezone offset:**
   ```
   2024-03-15T09:00:00+01:00
   2024-03-15T09:00:00-05:00
   ```

3. **Without timezone (interpreted as system timezone):**
   ```
   2024-03-15T09:00:00
   ```

### Invalid Formats
```
2024-03-15                 ❌ Date only (deprecated)
15/03/2024 09:00          ❌ Non-ISO format
2024-03-15 09:00:00       ❌ Space instead of T
2024-13-15T09:00:00Z      ❌ Invalid month
```

## ⚠️ Validation Rules

### DateTime Validation
- Start datetime must be before end datetime
- Both datetimes must be valid ISO 8601 format
- Future absences are allowed
- Past absences may have business rule restrictions

### Overlap Detection
- Precise datetime overlap detection
- Two absences overlap if their time periods intersect
- Only non-denied absences are considered for conflicts

### Example Overlaps:
```
Absence 1: 2024-03-15T09:00:00Z to 2024-03-15T17:00:00Z
Absence 2: 2024-03-15T16:00:00Z to 2024-03-15T18:00:00Z
Result: ❌ Overlap (1 hour overlap from 16:00-17:00)

Absence 1: 2024-03-15T09:00:00Z to 2024-03-15T17:00:00Z  
Absence 2: 2024-03-15T17:00:00Z to 2024-03-15T18:00:00Z
Result: ✅ No overlap (end time = start time is allowed)
```

## 🔍 Status Values

| Status | Description |
|--------|-------------|
| `függőben` | Pending approval (not yet approved or denied) |
| `jóváhagyva` | Approved by admin |
| `elutasítva` | Denied by admin |
| `folyamatban` | Currently ongoing (current time within absence period) |
| `lezárt` | Past absence (end time has passed) |
| `konfliktus` | Error state (both approved and denied flags set) |

## 🛡️ Permissions

### User Permissions
- Create absence for self
- View own absences
- Update own pending absences
- Delete own pending absences

### Admin Permissions
- Create absence for any user
- View all absences
- Update any absence
- Approve/deny absences
- Delete any absence
- Access conflict checking for all users

## 📊 Error Responses

### 400 Bad Request
```json
{
  "message": "Hibás dátum/idő formátum. Használj ISO formátumot (pl. 2024-03-15T14:00:00)"
}
```

### 401 Unauthorized
```json
{
  "message": "Nincs jogosultság a távollét szerkesztéséhez"
}
```

### 404 Not Found
```json
{
  "message": "Távollét nem található"
}
```

### 409 Conflict
```json
{
  "message": "Átfedő távollét már létezik ebben az időszakban"
}
```

## 💡 Best Practices

### For Frontend Development

1. **Always use ISO datetime strings:**
   ```javascript
   const startDate = new Date().toISOString(); // "2024-03-15T09:00:00.000Z"
   ```

2. **Handle timezone display appropriately:**
   ```javascript
   const displayTime = new Date(absence.start_date).toLocaleString();
   ```

3. **Validate datetime ranges on frontend:**
   ```javascript
   if (new Date(endDate) <= new Date(startDate)) {
     // Show error: End must be after start
   }
   ```

### For Backend Integration

1. **Use timezone-aware datetime objects:**
   ```python
   from django.utils import timezone
   start_dt = timezone.now()
   ```

2. **Handle timezone conversion:**
   ```python
   # Convert to user's timezone for display
   user_tz = pytz.timezone(user.profile.timezone)
   local_time = start_dt.astimezone(user_tz)
   ```

3. **Efficient overlap queries:**
   ```python
   # Overlap detection
   conflicts = Tavollet.objects.filter(
       start_date__lt=end_datetime,
       end_date__gt=start_datetime
   )
   ```
