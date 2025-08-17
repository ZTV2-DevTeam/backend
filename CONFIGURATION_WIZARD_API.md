# Configuration Wizard API Documentation

## Overview

The Configuration Wizard provides admin-only endpoints for initial system setup through XLSX file uploads. This allows administrators to bulk import essential data for the FTV school media management system.

## Features

- **Admin-only access**: All endpoints require system administrator or developer administrator permissions
- **XLSX file parsing**: Upload and parse Excel files with data validation
- **Data preview**: Review parsed data before confirming creation
- **Bulk record creation**: Create multiple records in a single transaction
- **Template downloads**: Download XLSX templates with correct column formats
- **Progress tracking**: Monitor completion status of required setup steps

## Required Setup Steps

The wizard enforces completion of these required steps in the recommended order:

1. **Osztályok (Classes)** - School classes and sections
2. **Stábok (Teams)** - Media production teams
3. **Tanárok (Teachers)** - Teacher accounts and permissions
4. **Tanulók (Students)** - Student accounts and class assignments

## API Endpoints

### Authentication

All endpoints require JWT authentication with admin permissions:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

### 1. Get Wizard Status

**GET** `/api/config-wizard/status`

Returns current completion status of the configuration wizard.

**Response:**
```json
{
  "total_records": 150,
  "successful_uploads": 150,
  "in_progress": 0,
  "classes_completed": true,
  "stabs_completed": true,
  "teachers_completed": true,
  "students_completed": true,
  "wizard_completed": true
}
```

### 2. Parse XLSX File

**POST** `/api/config-wizard/parse-xlsx`

Upload and parse an XLSX file. Returns parsed data for confirmation.

**Request:**
- Content-Type: `multipart/form-data`
- `file`: XLSX file to upload
- `data_type`: One of `classes`, `stabs`, `teachers`, `students`

**Response:**
```json
{
  "type": "classes",
  "total_records": 5,
  "valid_records": 4,
  "invalid_records": 1,
  "data": [
    {
      "start_year": 2024,
      "section": "F",
      "school_year": "2024/2025",
      "class_teachers": "Nagy János"
    }
  ],
  "errors": ["Sor 3: Érvénytelen szekció 'X'"],
  "warnings": ["Osztály 2023F már létezik"]
}
```

### 3. Confirm Data Creation

**POST** `/api/config-wizard/confirm-data`

Confirm parsed data and create records in the database.

**Request:**
```json
{
  "type": "classes",
  "data": [
    {
      "start_year": 2024,
      "section": "F",
      "school_year": "2024/2025",
      "class_teachers": "Nagy János"
    }
  ]
}
```

**Response:**
```json
{
  "type": "classes",
  "created_records": 4,
  "failed_records": 0,
  "errors": [],
  "warnings": ["Osztály 2023F már létezik"]
}
```

### 4. Download Templates

**GET** `/api/config-wizard/download-template/{template_type}`

Download XLSX template files with correct column headers and sample data.

Template types: `classes`, `stabs`, `teachers`, `students`

Returns an Excel file download.

### 5. Complete Wizard

**POST** `/api/config-wizard/complete`

Complete the configuration wizard and activate the system.

**Response:**
```json
{
  "message": "Konfiguráció varázsló sikeresen befejezve",
  "system_active": true,
  "total_records": 150,
  "wizard_completed": true
}
```

### 6. Reset Wizard (Developer Only)

**POST** `/api/config-wizard/reset`

⚠️ **DANGER**: Resets the entire wizard and deletes all data. Only for developer admins.

## XLSX File Formats

### Classes (Osztályok)

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| start_year | Yes | Class start year | 2024 |
| section | Yes | Class section (single letter) | F |
| school_year | No | School year description | 2024/2025 |
| class_teachers | No | Class teacher names | Nagy János |

### Stabs (Teams)

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| name | Yes | Team name | A stáb |
| description | No | Team description | Első műszak média stáb |
| type | No | Team type | media |

### Teachers (Tanárok)

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| username | Yes | Unique username | nagy.janos |
| first_name | Yes | First name | János |
| last_name | Yes | Last name | Nagy |
| email | Yes | Email address | nagy.janos@iskola.hu |
| phone | No | Phone number | +36301234567 |
| admin_type | No | Admin role (teacher/system_admin/developer) | teacher |
| special_role | No | Special role (none/production_leader) | none |
| assigned_classes | No | Classes to assign as osztályfőnök (comma-separated) | 2024F,2023A |

**Note**: Teachers are not part of stábs. Use assigned_classes to assign them as class teachers to specific classes.

### Students (Tanulók)

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| username | Yes | Unique username | toth.anna |
| first_name | Yes | First name | Anna |
| last_name | Yes | Last name | Tóth |
| email | Yes | Email address | toth.anna@student.hu |
| phone | No | Phone number | +36301234567 |
| class_start_year | Yes | Class start year | 2024 |
| class_section | Yes | Class section | F |
| stab | No | Assigned team name | A stáb |
| radio_stab | No | Radio team name (for 9F students) | A1 |

## Frontend Usage

The wizard includes a complete web interface at `/config-wizard/` that provides:

- **Status dashboard**: Shows completion progress
- **File upload forms**: For each data type
- **Data preview**: Review parsed data before confirmation
- **Template downloads**: Direct links to XLSX templates
- **Progress tracking**: Visual indicators of completion
- **Error handling**: Clear error messages and validation

### JavaScript API Usage

```javascript
// Get wizard status
const status = await fetch('/api/config-wizard/status', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Upload file
const formData = new FormData();
formData.append('file', file);
formData.append('data_type', 'classes');

const result = await fetch('/api/config-wizard/parse-xlsx', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});

// Confirm data
const confirmation = await fetch('/api/config-wizard/confirm-data', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ type: 'classes', data: parsedData })
});
```

## Error Handling

The API provides detailed error messages for common issues:

- **File format errors**: Invalid XLSX files or missing columns
- **Data validation errors**: Invalid values, duplicates, missing required fields
- **Permission errors**: Insufficient admin permissions
- **System errors**: Database or server issues

All errors include specific row numbers and field names when applicable.

## Security

- **Admin-only access**: All endpoints require admin authentication
- **Permission levels**: Different operations require different admin levels
- **Data validation**: All uploaded data is validated before creation
- **Transaction safety**: Bulk operations use database transactions

## Best Practices

1. **Download templates first**: Use the provided XLSX templates to ensure correct format
2. **Start with classes**: Follow the recommended order (Classes → Stabs → Teachers → Students)
3. **Preview before confirming**: Always review parsed data before creation
4. **Handle errors**: Check for validation errors and warnings
5. **Complete in order**: Finish all required steps before completing the wizard

## Example Workflow

1. Login as admin and navigate to `/config-wizard/`
2. Download XLSX templates for each data type
3. Fill templates with your institution's data
4. Upload classes XLSX → preview → confirm
5. Upload stabs XLSX → preview → confirm
6. Upload teachers XLSX → preview → confirm
7. Upload students XLSX → preview → confirm
8. Complete the wizard to activate the system

This completes the initial system setup and enables full functionality of the FTV media management system.
