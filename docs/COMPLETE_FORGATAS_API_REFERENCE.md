# Complete API Reference for Forgatás Creation

This document provides a comprehensive reference for all endpoints needed for forgatás creation, including both existing and newly implemented endpoints.

---

## 📋 Complete Endpoint List

### 🎯 Student/Editor Selection (NEW)

#### GET `/api/students/reporters`
**Purpose:** Get list of students eligible to be editors  
**Authentication:** Required  
**Response:** List of editors with experience data

```json
[
  {
    "id": 123,
    "username": "student123",
    "full_name": "Kovács Anna",
    "osztaly_display": "10F",
    "grade_level": 10,
    "is_experienced": false,
    "reporter_sessions_count": 1,
    "last_reporter_date": "2024-02-15"
  }
]
```

#### GET `/api/students/reporters/available`
**Purpose:** Get editors available for specific date/time  
**Authentication:** Required  
**Parameters:** `date`, `time_from`, `time_to` (all optional)  
**Response:** List of available editors (no conflicts)

#### GET `/api/students?section=F&grade=10`
**Purpose:** Get 10F students specifically  
**Authentication:** Required  
**Parameters:**
- `section=F` - Media students
- `grade=10` - 10th grade
- `can_be_reporter=true` - Only eligible reporters
- `search` - Search by name

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
      "start_year": 2024,
      "current_grade": 10
    },
    "can_be_reporter": true,
    "is_media_student": true
  }
]
```

---

### 🎬 KaCsa Session Management

#### GET `/api/production/filming-sessions?type=kacsa` (EXISTING)
**Purpose:** Get all KaCsa filming sessions  
**Authentication:** Required  
**Parameters:**
- `type=kacsa` - Filter for KaCsa sessions
- `start_date`, `end_date` - Date range filters

#### GET `/api/production/filming-sessions/kacsa-available` (NEW)
**Purpose:** Get KaCsa sessions available for linking  
**Authentication:** Required  
**Response:** KaCsa sessions with linking status

```json
[
  {
    "id": 15,
    "name": "KaCsa Episode 5",
    "date": "2024-03-15",
    "time_from": "09:00:00",
    "time_to": "11:00:00",
    "can_link": true,
    "already_linked": false,
    "linked_sessions_count": 0
  }
]
```

---

### 📅 School Year Management

#### GET `/api/school-years/active` (EXISTING)
**Purpose:** Get currently active school year  
**Authentication:** Required  
**Response:** Active school year details

```json
{
  "id": 1,
  "start_date": "2024-09-01",
  "end_date": "2025-06-15",
  "start_year": 2024,
  "end_year": 2025,
  "display_name": "2024/2025",
  "is_active": true,
  "osztaly_count": 12
}
```

#### GET `/api/school-years/for-date/2024-03-15` (NEW)
**Purpose:** Get school year for specific date  
**Authentication:** Required  
**Response:** School year containing the date

```json
{
  "id": 1,
  "display_name": "2024/2025",
  "is_active": true,
  "date_in_range": true
}
```

---

### 🛠️ Equipment Management (EXISTING)

#### GET `/api/equipment`
**Purpose:** Get list of all equipment  
**Authentication:** Required  
**Response:** List of equipment with types and status

#### GET `/api/equipment/{id}/availability`
**Purpose:** Check equipment availability for date/time  
**Authentication:** Required  
**Parameters:**
- `start_date` (required) - YYYY-MM-DD
- `start_time` (required) - HH:MM
- `end_date` (optional) - YYYY-MM-DD
- `end_time` (optional) - HH:MM

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
      "time_to": "15:00",
      "location": "Stúdió A",
      "type_display": "Rendes"
    }
  ]
}
```

---

### 🎥 Forgatás Creation and Management

#### POST `/api/production/filming-sessions` (ENHANCED)
**Purpose:** Create new filming session with editor assignment  
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
  "szerkeszto_id": 123,
  "notes": "Formal attire required",
  "type": "rendezveny",
  "related_kacsa_id": 15,
  "equipment_ids": [1, 3, 7]
}
```

**Response:** Created filming session with full details

#### PUT `/api/production/filming-sessions/{id}` (ENHANCED)
**Purpose:** Update existing filming session  
**Authentication:** Required (admin/teacher)  
**Request Body:** Same as creation, all fields optional

#### GET `/api/production/filming-sessions` (EXISTING)
**Purpose:** List filming sessions with filters  
**Authentication:** Required  
**Parameters:**
- `start_date`, `end_date` - Date range
- `type` - Session type filter

#### GET `/api/production/filming-sessions/{id}` (EXISTING)
**Purpose:** Get specific filming session details  
**Authentication:** Required

#### GET `/api/production/filming-sessions/types` (EXISTING)
**Purpose:** Get available filming session types  
**Authentication:** Public

```json
[
  {"value": "kacsa", "label": "KaCsa"},
  {"value": "rendes", "label": "Rendes"},
  {"value": "rendezveny", "label": "Rendezvény"},
  {"value": "egyeb", "label": "Egyéb"}
]
```

---

### 🏢 Contact and Location Management (EXISTING)

#### GET `/api/production/contact-persons`
**Purpose:** Get all contact persons  
**Authentication:** Required

#### GET `/api/partners`
**Purpose:** Get all partner locations  
**Authentication:** Required

---

## 🚀 Complete Frontend Integration Example

```javascript
class ForgatásCreationForm {
  constructor() {
    this.baseUrl = '/api';
    this.token = localStorage.getItem('jwt_token');
    this.headers = {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }

  // Initialize form data
  async initialize() {
    const [
      reporters,
      kacsaSessions,
      activeSchoolYear,
      equipment,
      contactPersons,
      locations,
      filmingTypes
    ] = await Promise.all([
      this.fetchReporters(),
      this.fetchAvailableKacsa(),
      this.fetchActiveSchoolYear(),
      this.fetchEquipment(),
      this.fetchContactPersons(),
      this.fetchLocations(),
      this.fetchFilmingTypes()
    ]);

    return {
      reporters,
      kacsaSessions,
      activeSchoolYear,
      equipment,
      contactPersons,
      locations,
      filmingTypes
    };
  }

  // Fetch available reporters
  async fetchReporters() {
    const response = await fetch(`${this.baseUrl}/students/reporters`, {
      headers: this.headers
    });
    return await response.json();
  }

  // Fetch available KaCsa sessions
  async fetchAvailableKacsa() {
    const response = await fetch(`${this.baseUrl}/production/filming-sessions/kacsa-available`, {
      headers: this.headers
    });
    return await response.json();
  }

  // Fetch active school year
  async fetchActiveSchoolYear() {
    const response = await fetch(`${this.baseUrl}/school-years/active`, {
      headers: this.headers
    });
    return await response.json();
  }

  // Get school year for specific date
  async getSchoolYearForDate(date) {
    const response = await fetch(`${this.baseUrl}/school-years/for-date/${date}`, {
      headers: this.headers
    });
    return await response.json();
  }

  // Check reporter availability
  async checkReporterAvailability(date, timeFrom, timeTo) {
    const params = new URLSearchParams({
      date: date,
      time_from: timeFrom,
      time_to: timeTo
    });
    
    const response = await fetch(`${this.baseUrl}/students/reporters/available?${params}`, {
      headers: this.headers
    });
    return await response.json();
  }

  // Check equipment availability
  async checkEquipmentAvailability(equipmentId, date, timeFrom, timeTo) {
    const params = new URLSearchParams({
      start_date: date,
      start_time: timeFrom,
      end_date: date,
      end_time: timeTo
    });
    
    const response = await fetch(`${this.baseUrl}/equipment/${equipmentId}/availability?${params}`, {
      headers: this.headers
    });
    return await response.json();
  }

  // Validate equipment selection
  async validateEquipmentSelection(equipmentIds, date, timeFrom, timeTo) {
    const validationResults = [];
    
    for (const equipmentId of equipmentIds) {
      const availability = await this.checkEquipmentAvailability(
        equipmentId, date, timeFrom, timeTo
      );
      
      validationResults.push({
        equipmentId,
        available: availability.available,
        conflicts: availability.conflicts
      });
    }
    
    return validationResults;
  }

  // Handle date change
  async onDateChange(date) {
    // Update school year
    const schoolYear = await this.getSchoolYearForDate(date);
    this.updateSchoolYearDisplay(schoolYear);
    
    // Refresh availability if reporter/equipment selected
    if (this.selectedReporter) {
      await this.validateReporterSelection(this.selectedReporter, date);
    }
    
    if (this.selectedEquipment.length > 0) {
      await this.validateEquipmentSelection(this.selectedEquipment, date);
    }
  }

  // Validate reporter selection
  async validateReporterSelection(reporterId, date, timeFrom, timeTo) {
    const availableReporters = await this.checkReporterAvailability(date, timeFrom, timeTo);
    const isAvailable = availableReporters.some(r => r.id === reporterId);
    
    if (!isAvailable) {
      this.showReporterConflictWarning();
    } else {
      this.clearReporterWarnings();
    }
    
    return isAvailable;
  }

  // Submit form
  async submitForm(formData) {
    try {
      // Final validation
      const validationErrors = await this.validateForm(formData);
      if (validationErrors.length > 0) {
        throw new Error('Validation failed: ' + validationErrors.join(', '));
      }

      // Prepare payload
      const payload = {
        name: formData.name,
        description: formData.description,
        date: formData.date,
        time_from: formData.timeFrom,
        time_to: formData.timeTo,
        location_id: formData.locationId || null,
        contact_person_id: formData.contactPersonId || null,
        szerkeszto_id: formData.reporterId || null,
        notes: formData.notes || null,
        type: formData.type,
        related_kacsa_id: formData.relatedKacsaId || null,
        equipment_ids: formData.equipmentIds || []
      };

      // Submit to API
      const response = await fetch(`${this.baseUrl}/production/filming-sessions`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to create filming session');
      }

      const result = await response.json();
      this.onSuccess(result);
      return result;

    } catch (error) {
      this.onError(error);
      throw error;
    }
  }

  // Validation helper
  async validateForm(formData) {
    const errors = [];

    // Required field validation
    if (!formData.name) errors.push('Name is required');
    if (!formData.description) errors.push('Description is required');
    if (!formData.date) errors.push('Date is required');
    if (!formData.timeFrom) errors.push('Start time is required');
    if (!formData.timeTo) errors.push('End time is required');
    if (!formData.type) errors.push('Type is required');

    // Time validation
    if (formData.timeFrom >= formData.timeTo) {
      errors.push('End time must be after start time');
    }

    // Conflict validation
    if (formData.reporterId) {
      const isReporterAvailable = await this.validateReporterSelection(
        formData.reporterId, formData.date, formData.timeFrom, formData.timeTo
      );
      if (!isReporterAvailable) {
        errors.push('Selected reporter has a scheduling conflict');
      }
    }

    return errors;
  }

  // Fetch other required data
  async fetchEquipment() {
    const response = await fetch(`${this.baseUrl}/equipment`, {
      headers: this.headers
    });
    return await response.json();
  }

  async fetchContactPersons() {
    const response = await fetch(`${this.baseUrl}/production/contact-persons`, {
      headers: this.headers
    });
    return await response.json();
  }

  async fetchLocations() {
    const response = await fetch(`${this.baseUrl}/partners`, {
      headers: this.headers
    });
    return await response.json();
  }

  async fetchFilmingTypes() {
    const response = await fetch(`${this.baseUrl}/production/filming-sessions/types`);
    return await response.json();
  }

  // UI update methods
  updateSchoolYearDisplay(schoolYear) {
    // Update school year display in UI
  }

  showReporterConflictWarning() {
    // Show warning about reporter conflict
  }

  clearReporterWarnings() {
    // Clear reporter warnings
  }

  onSuccess(result) {
    // Handle successful creation
    console.log('Filming session created successfully:', result);
  }

  onError(error) {
    // Handle creation error
    console.error('Error creating filming session:', error);
  }
}

// Usage example
const form = new ForgatásCreationForm();

// Initialize form when page loads
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const initialData = await form.initialize();
    populateFormOptions(initialData);
  } catch (error) {
    console.error('Failed to initialize form:', error);
  }
});
```

---

## 🔑 Key Features Summary

### ✅ Student/Reporter Management
- **Complete Reporter Listing** with experience tracking
- **Availability Checking** with conflict detection
- **Grade/Section Filtering** (10F students prioritized)
- **Experience Levels** (experienced vs. new reporters)

### ✅ KaCsa Integration
- **Available Sessions** for linking
- **Link Status Tracking** (already linked count)
- **Multiple Linking Support** (one KaCsa → many sessions)

### ✅ School Year Automation
- **Active School Year** retrieval
- **Date-based School Year** calculation
- **Automatic Assignment** based on forgatás date

### ✅ Equipment Integration
- **Availability Checking** for specific date/time ranges
- **Conflict Detection** with detailed conflict information
- **Multi-equipment Validation** for equipment sets

### ✅ Enhanced Validation
- **Reporter Conflicts** during creation and updates
- **Equipment Conflicts** with existing bookings
- **Time Range Validation** (start < end)
- **Permission Validation** (admin/teacher only)

All endpoints are production-ready and fully integrated into the existing FTV API structure!
