# Role API Extensions Documentation

This document describes the new and extended API endpoints for role (szerepkör) management and forgatas-role relationships.

## Summary of Changes

### 1. Extended Role (Szerepkör) Endpoints

#### New Endpoints in `/assignments/` module:

- **GET `/assignments/roles`** - Get all available roles with optional year filtering
- **GET `/assignments/roles/{role_id}`** - Get detailed information about a specific role
- **GET `/assignments/user-role-statistics/{user_id}`** - Get comprehensive role statistics for a user
- **GET `/assignments/roles-by-year`** - Get roles grouped by year level
- **GET `/assignments/summary`** - Get assignment system summary statistics

### 2. Enhanced Forgatas Endpoints with Role Information

#### New Endpoints in `/production/` module:

- **GET `/production/filming-sessions-with-roles`** - Get filming sessions with role assignment information
- **GET `/production/filming-sessions/{forgatas_id}/with-roles`** - Get detailed session with role assignments
- **GET `/production/filming-sessions/upcoming-with-roles`** - Get upcoming sessions with role information
- **GET `/production/filming-sessions/unassigned`** - Get sessions without role assignments

### 3. Consistent Admin/Teacher Permissions for Beosztás Management

- Updated **PUT `/assignments/filming-assignments/{assignment_id}`** - Now requires admin or teacher permissions (same as creating)
- Updated **DELETE `/assignments/filming-assignments/{assignment_id}`** - Now requires admin or teacher permissions (same as creating)
- Permission levels are now consistent: if you can create an assignment, you can also edit and delete it

## Detailed API Reference

### Role Management Endpoints

#### GET `/assignments/roles`
Get all available roles with optional filtering.

**Query Parameters:**
- `ev` (optional): Filter by year level

**Response Example:**
```json
[
  {
    "id": 1,
    "name": "Operatőr",
    "ev": 10
  },
  {
    "id": 2,
    "name": "Hang",
    "ev": 11
  }
]
```

#### GET `/assignments/user-role-statistics/{user_id}`
Get comprehensive role statistics for a specific user.

**Response Example:**
```json
{
  "user": {
    "id": 123,
    "username": "student1",
    "full_name": "Nagy Péter"
  },
  "summary": {
    "total_assignments": 5,
    "total_different_roles": 3,
    "most_used_role": {
      "id": 1,
      "name": "Operatőr"
    },
    "most_used_count": 3
  },
  "role_statistics": [
    {
      "role": {
        "id": 1,
        "name": "Operatőr",
        "ev": 10
      },
      "total_times": 3,
      "last_time": "2024-03-15",
      "last_forgatas": {
        "id": 45,
        "name": "Reggeli műsor",
        "date": "2024-03-15"
      },
      "assignments": [...]
    }
  ]
}
```

### Forgatas with Role Information

#### GET `/production/filming-sessions-with-roles`
Get filming sessions with role assignment information.

**Query Parameters:**
- `date_from`: Filter from date (YYYY-MM-DD)
- `date_to`: Filter to date (YYYY-MM-DD)
- `type`: Filter by session type
- `has_assignment`: Filter by assignment existence (boolean)
- `finalized_only`: Show only finalized assignments (boolean)

**Response Example:**
```json
[
  {
    "id": 1,
    "name": "Reggeli műsor",
    "description": "Heti reggeli műsor felvétel",
    "date": "2024-03-15",
    "time_from": "08:00:00",
    "time_to": "10:00:00",
    "type": "rendes",
    "type_display": "Rendes",
    "has_assignment": true,
    "assignment": {
      "id": 10,
      "finalized": true,
      "author": {
        "id": 5,
        "username": "teacher1",
        "full_name": "Tanár Mária"
      },
      "created_at": "2024-03-10T14:30:00Z",
      "student_count": 4
    },
    "assigned_students": [
      {
        "user": {
          "id": 123,
          "username": "student1",
          "full_name": "Nagy Péter"
        },
        "role": {
          "id": 1,
          "name": "Operatőr",
          "ev": 10
        }
      }
    ],
    "roles_summary": [
      {
        "role": "Operatőr",
        "count": 2
      },
      {
        "role": "Hang",
        "count": 1
      }
    ]
  }
]
```

#### GET `/production/filming-sessions/unassigned`
Get filming sessions that don't have role assignments yet.

**Query Parameters:**
- `days_ahead`: Number of days ahead to check (default: 60)

### Permission Changes

#### Consistent Permission Model for Beosztás Management
The following endpoints now use the same permission model as creation (admin or teacher permissions):

- **PUT `/assignments/filming-assignments/{assignment_id}`**
- **DELETE `/assignments/filming-assignments/{assignment_id}`**

This ensures consistent access: if you can create an assignment, you can also edit and delete it. All admin types (developer, teacher, system_admin) can manage assignments.

## Usage Examples

### Get Role Statistics for a User
```bash
curl -H "Authorization: Bearer {token}" \
  /api/assignments/user-role-statistics/123
```

### Get Upcoming Sessions with Role Info
```bash
curl -H "Authorization: Bearer {token}" \
  "/api/production/filming-sessions/upcoming-with-roles?days_ahead=14"
```

### Get Sessions Needing Assignments
```bash
curl -H "Authorization: Bearer {token}" \
  /api/production/filming-sessions/unassigned
```

### Get Roles by Year Level
```bash
curl -H "Authorization: Bearer {token}" \
  /api/assignments/roles-by-year
```

### Filter Sessions with Assignments
```bash
curl -H "Authorization: Bearer {token}" \
  "/api/production/filming-sessions-with-roles?has_assignment=true&finalized_only=true"
```

## Benefits

1. **Enhanced Role Management**: Easy access to role information and statistics
2. **Better Planning**: Forgatas endpoints now include assignment information for better planning
3. **User Statistics**: Track how often users take specific roles
4. **Security**: Admin-only protection for sensitive operations
5. **API Efficiency**: Combined endpoints reduce the need for multiple API calls
6. **Filtering**: Comprehensive filtering options for different use cases

## Integration Notes

- All endpoints maintain backward compatibility
- Role statistics are calculated in real-time
- Admin permissions are checked using the existing Profile system
- Response schemas are documented and validated
- Error handling provides clear messages in Hungarian

## Future Enhancements

Potential future improvements could include:
- Role preference tracking
- Automated role assignment suggestions
- Role conflict detection
- Performance optimization with caching
- Additional statistics and reporting features