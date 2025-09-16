# Forgatás Creation Form - API Reference

This document provides comprehensive API reference for all endpoints needed to create new "forgatás" (filming sessions), including existing endpoints and missing ones that need to be implemented.

## Overview

The forgatás creation form requires the following data:
1. **Student/Reporter selection** - List of students who can be assigned as reporters
2. **KaCsa session linking** - List of existing KaCsa filming sessions for potential linking
3. **School year management** - Automatic school year calculation and validation
4. **Equipment integration** - Equipment selection and availability checking

---

## 🎯 Required Endpoints for Forgatás Creation

### 1. Student/Reporter Endpoints

#### **🔴 MISSING** - GET `/api/students`
**Description:** Get list of students, especially 10F students who can be reporters  
**Authentication:** Required  
**Parameters:**
- `section` (optional): Filter by class section (e.g., "F" for media students)
- `grade` (optional): Filter by grade level (e.g., 10, 11, 12)
- `can_be_reporter` (optional): Filter students eligible to be reporters
- `search` (optional): Search by name or username

**Expected Response:**
```json
[
  {
    "id": 123,
    "username": "student123",
    "first_name": "Anna",
    "last_name": "Kovács",
    "full_name": "Kovács Anna",
    "email": "anna.kovacs@student.edu",
    "osztaly": {
      "id": 1,
      "display_name": "10F",
      "section": "F",
      "start_year": 2024
    },
    "can_be_reporter": true,
    "is_media_student": true
  }
]
```

#### **🔴 MISSING** - GET `/api/students/reporters`
**Description:** Get list of students specifically eligible to be reporters  
**Authentication:** Required

**Expected Response:**
```json
[
  {
    "id": 123,
    "username": "student123",
    "full_name": "Kovács Anna",
    "osztaly_display": "10F",
    "grade_level": 10,
    "is_experienced": false
  }
]
```

### 2. KaCsa Session Endpoints

#### **✅ EXISTING** - GET `/api/production/filming-sessions?type=kacsa`
**Description:** Get existing KaCsa filming sessions for linking  
**Authentication:** Required  
**Parameters:**
- `type=kacsa`: Filter for KaCsa type sessions
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date

**Response:** (Already implemented)
```json
[
  {
    "id": 15,
    "name": "KaCsa Episode 5",
    "description": "Weekly student show",
    "date": "2024-03-15",
    "time_from": "09:00:00",
    "time_to": "11:00:00",
    "type": "kacsa",
    "type_display": "KaCsa"
  }
]
```

#### **🔴 MISSING** - GET `/api/production/filming-sessions/kacsa-available`
**Description:** Get KaCsa sessions available for linking (not already linked)  
**Authentication:** Required

**Expected Response:**
```json
[
  {
    "id": 15,
    "name": "KaCsa Episode 5",
    "date": "2024-03-15",
    "time_from": "09:00:00",
    "time_to": "11:00:00",
    "can_link": true,
    "already_linked": false
  }
]
```

### 3. School Year Management

#### **✅ EXISTING** - GET `/api/school-years/active`
**Description:** Get currently active school year  
**Authentication:** Required

**Response:** (Already implemented via academic.py)
```json
{
  "id": 1,
  "start_date": "2024-09-01",
  "end_date": "2025-06-15",
  "start_year": 2024,
  "end_year": 2025,
  "display_name": "2024/2025",
  "is_active": true
}
```

#### **🔴 MISSING** - GET `/api/school-years/for-date/{date}`
**Description:** Get school year for a specific date  
**Authentication:** Required  
**Path Parameter:**
- `date`: Date in YYYY-MM-DD format

**Expected Response:**
```json
{
  "id": 1,
  "display_name": "2024/2025",
  "is_active": true,
  "date_in_range": true
}
```

### 4. Equipment Integration

#### **✅ EXISTING** - GET `/api/equipment`
**Description:** Get list of all equipment  
**Authentication:** Required

#### **✅ EXISTING** - GET `/api/equipment/{id}/availability`
**Description:** Check equipment availability for specific date/time  
**Authentication:** Required  
**Parameters:**
- `start_date`: Start date (YYYY-MM-DD)
- `start_time`: Start time (HH:MM)
- `end_date` (optional): End date
- `end_time` (optional): End time

**Response:** (Already implemented)
```json
{
  "equipment_id": 1,
  "available": false,
  "conflicts": [
    {
      "type": "filming_session",
      "forgatas_id": 5,
      "forgatas_name": "Reggeli műsor felvétel",
      "date": "2024-03-15",
      "time_from": "13:30",
      "time_to": "15:00"
    }
  ]
}
```

---

## 🎬 Forgatás Creation and Management

### **✅ EXISTING** - POST `/api/production/filming-sessions`
**Description:** Create new filming session  
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
  "related_kacsa_id": 15,
  "equipment_ids": [1, 3, 7]
}
```

**Note:** To assign an editor, update the forgatás after creation or add szerkeszto_id to the creation schema.

### **🔴 NEEDS ENHANCEMENT** - Update Forgatás Creation Schema
The current `ForgatCreateSchema` should be enhanced to include editor assignment:

```python
class ForgatCreateSchema(Schema):
    name: str
    description: str
    date: str
    time_from: str
    time_to: str
    location_id: Optional[int] = None
    contact_person_id: Optional[int] = None
    szerkeszto_id: Optional[int] = None  # Add this field
    notes: Optional[str] = None
    type: str
    related_kacsa_id: Optional[int] = None
    equipment_ids: list[int] = []
```

---

## 🔧 Implementation Requirements

### Missing Endpoints to Implement

#### 1. Student/Reporter Endpoints

**File:** `backend/api_modules/students.py` (new file)

```python
"""
Student Management API Module for Forgatás Creation

Provides endpoints for student listing and reporter selection.
"""

@api.get("/students", auth=JWTAuth(), response=list[StudentSchema])
def list_students(request, 
                 section: str = None, 
                 grade: int = None, 
                 can_be_reporter: bool = None,
                 search: str = None):
    """List students with filtering options."""
    
@api.get("/students/reporters", auth=JWTAuth(), response=list[ReporterSchema])
def list_reporters(request):
    """List students eligible to be reporters."""
```

**Required Schemas:**
```python
class StudentSchema(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    osztaly: Optional[dict] = None
    can_be_reporter: bool
    is_media_student: bool

class ReporterSchema(Schema):
    id: int
    username: str
    full_name: str
    osztaly_display: str
    grade_level: int
    is_experienced: bool
```

#### 2. Enhanced School Year Endpoint

**File:** `backend/api_modules/academic.py` (enhance existing)

```python
@api.get("/school-years/for-date/{date}", auth=JWTAuth(), response=SchoolYearForDateSchema)
def get_school_year_for_date(request, date: str):
    """Get school year for specific date."""
```

#### 3. Enhanced KaCsa Endpoints

**File:** `backend/api_modules/production.py` (enhance existing)

```python
@api.get("/production/filming-sessions/kacsa-available", auth=JWTAuth(), response=list[KacsaAvailableSchema])
def get_available_kacsa_sessions(request):
    """Get KaCsa sessions available for linking."""
```

#### 4. Enhanced Forgatás Creation

**File:** `backend/api_modules/production.py` (enhance existing)

- Update `ForgatCreateSchema` to include `szerkeszto_id`
- Update creation logic to assign editor
- Add validation for editor eligibility

---

## 🎯 Frontend Integration Guidelines

### Forgatás Creation Form Flow

1. **Load Initial Data:**
   ```javascript
   const [students, schoolYear, equipment] = await Promise.all([
     fetch('/api/students/reporters'),
     fetch('/api/school-years/active'),
     fetch('/api/equipment')
   ]);
   ```

2. **Date Change Handler:**
   ```javascript
   const handleDateChange = async (date) => {
     // Update school year if needed
     const schoolYear = await fetch(`/api/school-years/for-date/${date}`);
     
     // Check equipment availability if equipment selected
     if (selectedEquipment.length > 0) {
       const availability = await checkEquipmentAvailability(selectedEquipment, date, timeFrom, timeTo);
     }
   };
   ```

3. **Load KaCsa Sessions for Linking:**
   ```javascript
   const loadKacsaSessions = async () => {
     const kacsa = await fetch('/api/production/filming-sessions/kacsa-available');
     setAvailableKacsa(kacsa);
   };
   ```

4. **Submit Forgatás:**
   ```javascript
   const createForgatas = async (formData) => {
     const response = await fetch('/api/production/filming-sessions', {
       method: 'POST',
       headers: {
         'Authorization': `Bearer ${token}`,
         'Content-Type': 'application/json'
       },
       body: JSON.stringify({
         ...formData,
         szerkeszto_id: selectedReporter?.id,
         related_kacsa_id: selectedKacsa?.id,
         equipment_ids: selectedEquipment.map(eq => eq.id)
       })
     });
   };
   ```

### Equipment Integration Decision

**Recommendation:** Include equipment selection in the creation form because:

1. **✅ Existing API Support:** Equipment availability checking is already implemented
2. **✅ Conflict Prevention:** Early conflict detection prevents scheduling issues
3. **✅ User Experience:** Single-form creation is more efficient
4. **✅ Workflow Integration:** Matches the existing equipment management system

**Implementation:**
- Use existing equipment endpoints
- Add real-time availability checking on date/time changes
- Show conflict warnings before form submission
- Allow form submission with conflicts (with warnings)

---

## 📝 Summary

### Existing APIs (Ready to Use)
- ✅ **Equipment Management:** Full CRUD and availability checking
- ✅ **Forgatás CRUD:** Create, read, update, delete filming sessions
- ✅ **School Year Management:** Basic active school year retrieval
- ✅ **KaCsa Filtering:** Can filter existing KaCsa sessions

### Missing APIs (Need Implementation)
- 🔴 **Student/Reporter Listing:** Endpoints for student selection
- 🔴 **KaCsa Availability:** Available KaCsa sessions for linking
- 🔴 **Date-based School Year:** School year lookup by specific date
- 🔴 **Enhanced Forgatás Creation:** Include reporter assignment in creation

### Enhancement Needed
- 🔧 **Forgatás Schema:** Add szerkeszto_id field to creation schema
- 🔧 **Validation Logic:** Editor eligibility validation
- 🔧 **Response Schemas:** Standardized student and editor response formats

The implementation priority should be:
1. Student/Editor endpoints (highest priority)
2. Enhanced Forgatás creation with editor assignment
3. KaCsa availability endpoint
4. Date-based school year lookup (lowest priority - can use active school year initially)
