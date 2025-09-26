# Forgatás Filtering API Guide

## Overview

The system already has comprehensive filtering capabilities for fetching forgatások by type and other criteria. This guide documents all available filtering endpoints that can be used for separated frontend menus.

## Available Forgatás Types

The system supports 4 types of forgatások:

- `kacsa` - KaCsa sessions
- `rendes` - Regular sessions  
- `rendezveny` - Event sessions
- `egyeb` - Other/Miscellaneous sessions

## API Endpoints with Type Filtering

### 1. Basic Filming Sessions List
**Endpoint:** `GET /api/production/filming-sessions`
**Authentication:** Required (JWT)

**Query Parameters:**
- `type` (optional): Filter by type (`kacsa`, `rendes`, `rendezveny`, `egyeb`)
- `start_date` (optional): Start date filter (ISO format: YYYY-MM-DD)
- `end_date` (optional): End date filter (ISO format: YYYY-MM-DD)

**Example Usage:**
```http
GET /api/production/filming-sessions?type=kacsa
GET /api/production/filming-sessions?type=rendes&start_date=2025-01-01
GET /api/production/filming-sessions?type=rendezveny&start_date=2025-01-01&end_date=2025-12-31
```

### 2. Filming Sessions with Role Assignments
**Endpoint:** `GET /api/production/filming-sessions-with-roles`
**Authentication:** Required (JWT)

**Query Parameters:**
- `type` (optional): Filter by type
- `date_from` (optional): Filter from date (YYYY-MM-DD)
- `date_to` (optional): Filter to date (YYYY-MM-DD)
- `has_assignment` (optional): Filter by assignment status (true/false)
- `finalized_only` (optional): Show only finalized assignments (true/false)

**Example Usage:**
```http
GET /api/production/filming-sessions-with-roles?type=kacsa
GET /api/production/filming-sessions-with-roles?type=rendes&has_assignment=true
GET /api/production/filming-sessions-with-roles?type=rendezveny&finalized_only=true
```

### 3. Upcoming Sessions with Roles
**Endpoint:** `GET /api/production/filming-sessions/upcoming-with-roles`
**Authentication:** Required (JWT)

**Query Parameters:**
- `days_ahead` (optional): Number of days ahead to look (default: 30)
- `type` (optional): Filter by type (`kacsa`, `rendes`, `rendezveny`, `egyeb`)

**Example Usage:**
```http
GET /api/production/filming-sessions/upcoming-with-roles?type=kacsa
GET /api/production/filming-sessions/upcoming-with-roles?type=rendes&days_ahead=14
```

### 4. Unassigned Sessions
**Endpoint:** `GET /api/production/filming-sessions/unassigned`
**Authentication:** Required (JWT)

**Query Parameters:**
- `days_ahead` (optional): Number of days ahead to check (default: 60)
- `type` (optional): Filter by type (`kacsa`, `rendes`, `rendezveny`, `egyeb`)

**Example Usage:**
```http
GET /api/production/filming-sessions/unassigned?type=kacsa
GET /api/production/filming-sessions/unassigned?type=rendezveny&days_ahead=30
```

### 5. Available KaCsa Sessions
**Endpoint:** `GET /api/production/filming-sessions/kacsa-available`
**Authentication:** Required (JWT)

This endpoint specifically returns KaCsa sessions that can be linked to other sessions.

### 6. Filming Session Types
**Endpoint:** `GET /api/production/filming-sessions/types`
**Authentication:** Public endpoint

Returns all available session types for use in frontend dropdowns.

## Frontend Menu Separation Strategy

Based on the available filtering, you can implement separate frontend menus as follows:

### Menu 1: KaCsa Sessions
```javascript
// Fetch only KaCsa sessions
const kaCsaSessions = await fetch('/api/production/filming-sessions?type=kacsa');
```

### Menu 2: Regular Sessions  
```javascript
// Fetch only regular sessions
const regularSessions = await fetch('/api/production/filming-sessions?type=rendes');
```

### Menu 3: Event Sessions
```javascript
// Fetch only event sessions
const eventSessions = await fetch('/api/production/filming-sessions?type=rendezveny');
```

### Menu 4: Other Sessions
```javascript
// Fetch miscellaneous sessions
const otherSessions = await fetch('/api/production/filming-sessions?type=egyeb');
```

### Menu 5: Sessions with Role Assignments
```javascript
// Fetch sessions with detailed role information
const sessionsWithRoles = await fetch('/api/production/filming-sessions-with-roles?type=kacsa');
```

## Recent Enhancements ✅

The following endpoints have been enhanced with type filtering support:

1. **Upcoming Sessions**: Added `type` parameter to `/production/filming-sessions/upcoming-with-roles`
2. **Unassigned Sessions**: Added `type` parameter to `/production/filming-sessions/unassigned`

These enhancements provide complete filtering support for all major forgatás endpoints.

## Implementation Notes

- All filtering is already implemented and tested
- The `type` parameter validation ensures only valid types are accepted
- Error handling is in place for invalid date formats and type values
- Performance is optimized with proper database queries and relationships

## Response Schemas

### Basic ForgatSchema
```json
{
  "id": 1,
  "name": "Session Name",
  "description": "Session Description",
  "date": "2025-01-15",
  "time_from": "09:00:00",
  "time_to": "12:00:00",
  "type": "kacsa",
  "type_display": "KaCsa",
  "location": {...},
  "contact_person": {...},
  "equipment_ids": [1, 2, 3]
}
```

### ForgatWithRolesSchema
Includes all basic fields plus detailed role assignment information.

## Conclusion

The filtering system is already fully functional and ready to support separated frontend menus. No backend changes are needed - you can immediately start using the `type` parameter in your API calls to filter forgatások by their specific types.