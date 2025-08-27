# Beosztas Stab Field API Migration Guide

## Overview

This document provides a comprehensive guide for the addition of the `stab` field to the `Beosztas` (Assignment) model and all related API endpoints, admin interfaces, and data streaming capabilities.

## Changes Summary

### 1. Database Model Changes

#### Beosztas Model (`api/models.py`)
- **Added Field**: `stab = models.ForeignKey('Stab', related_name='beosztasok', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Stáb', help_text='A beosztáshoz tartozó stáb')`
- **Updated `__str__` method**: Now includes stab information in the string representation
- **Database Migration**: A new migration has been created and applied to add the field

#### Field Characteristics:
- **Type**: ForeignKey to Stab model
- **Null/Blank**: Both True (optional field)
- **On Delete**: PROTECT (prevents deletion of Stab if referenced by Beosztas)
- **Related Name**: `beosztasok` (allows `stab.beosztasok.all()` to get all assignments for a stab)

### 2. Admin Interface Updates

#### BeosztasAdmin (`api/admin.py`)
- **List Display**: Added `stab_display` to show stab information in the list view
- **List Filter**: Added `stab` to the filter options
- **Search Fields**: Added `stab__name` for searching by stab name
- **Autocomplete Fields**: Added `stab` for easy selection
- **Fieldsets**: Added `stab` field to the main "Beosztás adatok" fieldset
- **Custom Method**: Added `stab_display()` method with formatted display

### 3. Import/Export Resources

#### BeosztasResource (`api/resources.py`)
- **Added Field**: `stab_name` for importing/exporting stab information
- **Widget**: Uses `ForeignKeyWidget(Stab, 'name')` for proper stab resolution
- **Export Order**: Updated to include `stab_name` in the export sequence

### 4. API Schema Updates

#### Organization API (`backend/api_modules/organization.py`)
- **BeosztasSchema**: Added optional `stab: Optional[StabSchema] = None`
- **BeosztasCreateSchema**: Added optional `stab_id: Optional[int] = None`
- **BeosztasDetailSchema**: Added optional `stab: Optional[StabSchema] = None`
- **Response Functions**: Updated `create_beosztas_response()` to include stab information
- **Endpoints**: Updated GET `/assignments` to support `stab_id` filter parameter
- **Assignment Creation**: Updated POST `/assignments` to accept and validate `stab_id`

#### Assignment API (`backend/api_modules/assignments.py`)
- **BeosztasCreateSchema**: Added optional `stab_id: Optional[int] = None`
- **BeosztasUpdateSchema**: Added optional `stab_id: Optional[int] = None`
- **Response Functions**: Updated both `create_beosztas_response()` and `create_beosztas_with_availability_response()` to include stab data
- **Filtering**: All assignment list endpoints now support `stab_id` parameter
- **Database Queries**: Updated all queries to include `select_related('stab')` for efficiency

### 5. API Endpoint Changes

#### New/Updated Endpoints:

##### GET `/api/assignments` (Organization API)
- **New Parameter**: `stab_id` (optional) - Filter assignments by stab
- **Response**: Now includes stab information in each assignment object

##### GET `/api/assignments/filming-assignments` (Assignment API)
- **New Parameter**: `stab_id` (optional) - Filter filming assignments by stab
- **Response**: Now includes stab information in each assignment object

##### POST `/api/assignments` (Organization API)
- **New Field**: `stab_id` (optional) - Assign a stab to the new assignment
- **Validation**: Validates that the provided stab_id exists

##### POST `/api/assignments/filming-assignments` (Assignment API)
- **New Field**: `stab_id` (optional) - Assign a stab to the new filming assignment
- **Validation**: Validates that the provided stab_id exists

##### PUT `/api/assignments/filming-assignments/{assignment_id}` (Assignment API)
- **New Field**: `stab_id` (optional) - Update the stab assignment
- **Special Value**: `stab_id: 0` explicitly removes the stab assignment
- **Validation**: Validates that the provided stab_id exists

##### GET `/api/assignments/filming-assignments-with-availability`
- **New Parameter**: `stab_id` (optional) - Filter assignments with availability by stab
- **Response**: Includes stab information in availability responses

## API Usage Examples

### Creating an Assignment with Stab

```javascript
// Organization API
const response = await fetch('/api/assignments', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    kesz: false,
    tanev_id: 1,
    stab_id: 2,  // NEW: Assign to stab with ID 2
    szerepkor_relacio_ids: [1, 2, 3]
  })
});

// Assignment API
const filmingResponse = await fetch('/api/assignments/filming-assignments', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    forgatas_id: 5,
    stab_id: 2,  // NEW: Assign to stab with ID 2
    student_role_pairs: [
      {"user_id": 1, "szerepkor_id": 1},
      {"user_id": 2, "szerepkor_id": 2}
    ]
  })
});
```

### Filtering Assignments by Stab

```javascript
// Get all assignments for a specific stab
const stabAssignments = await fetch('/api/assignments?stab_id=2', {
  headers: { 'Authorization': 'Bearer YOUR_JWT_TOKEN' }
});

// Get filming assignments for a specific stab
const stabFilmingAssignments = await fetch('/api/assignments/filming-assignments?stab_id=2', {
  headers: { 'Authorization': 'Bearer YOUR_JWT_TOKEN' }
});

// Get assignments with availability for a specific stab
const stabAvailability = await fetch('/api/assignments/filming-assignments-with-availability?stab_id=2', {
  headers: { 'Authorization': 'Bearer YOUR_JWT_TOKEN' }
});
```

### Updating Assignment Stab

```javascript
// Update assignment to assign to a different stab
const updateResponse = await fetch('/api/assignments/filming-assignments/123', {
  method: 'PUT',
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    stab_id: 3  // NEW: Change to stab with ID 3
  })
});

// Remove stab assignment
const removeStabResponse = await fetch('/api/assignments/filming-assignments/123', {
  method: 'PUT',
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    stab_id: 0  // NEW: Remove stab assignment
  })
});
```

## Response Format Changes

### Assignment Response Object

All assignment responses now include stab information:

```json
{
  "id": 123,
  "kesz": false,
  "author": {
    "id": 1,
    "username": "teacher1",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "Doe John"
  },
  "tanev": {
    "id": 1,
    "display_name": "2024/2025",
    "is_active": true
  },
  "stab": {  // NEW: Stab information
    "id": 2,
    "name": "A stáb",
    "member_count": 15
  },
  "created_at": "2025-08-27T10:30:00Z",
  "role_relation_count": 5
}
```

### Filming Assignment Response Object

```json
{
  "id": 456,
  "forgatas": {
    "id": 10,
    "name": "Teszt Forgatás",
    "description": "Leírás",
    "date": "2025-08-30",
    "time_from": "14:00:00",
    "time_to": "16:00:00",
    "type": "rendes"
  },
  "szerepkor_relaciok": [...],
  "kesz": true,
  "author": {...},
  "stab": {  // NEW: Stab information
    "id": 2,
    "name": "A stáb"
  },
  "created_at": "2025-08-27T10:30:00Z",
  "student_count": 3,
  "roles_summary": [...]
}
```

## Database Relationships

### New Relationship
- **Stab ↔ Beosztas**: One-to-Many relationship
  - `Stab.beosztasok.all()` - Get all assignments for a stab
  - `Beosztas.stab` - Get the stab assigned to an assignment

### Query Optimization
All API endpoints now use `select_related('stab')` to avoid N+1 query problems when fetching assignment data.

## Admin Interface Features

### Filtering and Search
- **Filter by Stab**: Admins can filter assignments by stab in the list view
- **Search by Stab Name**: Admins can search assignments by typing stab names
- **Autocomplete**: When creating/editing assignments, stab selection uses autocomplete

### Display
- **List View**: Shows stab name with a 🎬 icon and blue color coding
- **Detail View**: Stab field is in the main "Beosztás adatok" fieldset
- **String Representation**: Assignment `__str__` method includes stab name in brackets

## Import/Export

### CSV/Excel Import
- **Column Name**: `stab_name`
- **Format**: Use the exact stab name as it appears in the database
- **Example**: `"A stáb"`, `"B stáb"`, `"Technikai stáb"`

### CSV/Excel Export
- **Column**: `stab_name` is included in all exports
- **Value**: Empty if no stab is assigned, otherwise the stab name

## Backward Compatibility

### API Compatibility
- **Existing Endpoints**: All existing endpoints continue to work without changes
- **Optional Field**: The `stab_id` parameter is optional in all requests
- **Response**: Existing clients will receive `"stab": null` for assignments without stabs

### Database Compatibility
- **Existing Data**: All existing assignments will have `stab = NULL`
- **No Data Loss**: No existing data is modified during migration
- **Gradual Adoption**: Stabs can be assigned to assignments over time

## Migration Steps

### Database Migration
1. **Migration File**: `add_stab_to_beosztas.py` has been created and applied
2. **Field Addition**: Adds the nullable stab foreign key field
3. **No Data Changes**: Existing assignments remain unchanged

### Code Deployment
1. **Models**: Updated Beosztas model with stab field
2. **Admin**: Enhanced admin interface with stab support
3. **Resources**: Updated import/export functionality
4. **APIs**: Enhanced all relevant API endpoints
5. **Documentation**: This migration guide created

## Testing Recommendations

### API Testing
```javascript
// Test assignment creation with stab
// Test assignment creation without stab
// Test assignment update to add stab
// Test assignment update to remove stab
// Test assignment filtering by stab
// Test assignment responses include stab data
```

### Admin Testing
- Create assignments with and without stabs
- Filter assignments by stab
- Search assignments by stab name
- Import/export assignments with stab data

### Database Testing
- Verify foreign key constraints
- Test stab deletion protection
- Verify query performance with select_related

## Performance Considerations

### Query Optimization
- All queries use `select_related('stab')` to fetch stab data efficiently
- No additional database queries needed for stab information

### Index Recommendations
- The foreign key field automatically creates a database index
- Consider adding composite indexes if filtering by stab becomes common

## Security Considerations

### Access Control
- Stab assignment follows existing permission patterns
- Only admin/teacher users can assign stabs to assignments
- Stab information is visible to all authenticated users (same as other assignment data)

### Data Protection
- `on_delete=models.PROTECT` prevents accidental stab deletion
- Foreign key constraints ensure data integrity

## Future Enhancements

### Potential Features
1. **Stab-based Notifications**: Send notifications to all members of an assigned stab
2. **Stab Analytics**: Reports showing assignment distribution across stabs
3. **Stab Templates**: Pre-configure role assignments based on stab
4. **Stab Schedules**: Integration with stab availability tracking

### API Extensions
1. **Bulk Assignment**: Assign multiple assignments to a stab at once
2. **Stab Statistics**: Endpoint to get assignment statistics per stab
3. **Stab Members**: Include stab member information in responses

## Troubleshooting

### Common Issues

#### Stab Not Found Error
```json
{"message": "Stáb nem található"}
```
**Solution**: Verify the stab_id exists in the database

#### Permission Denied
```json
{"message": "Adminisztrátor vagy tanár jogosultság szükséges"}
```
**Solution**: Ensure the user has admin or teacher permissions

#### Invalid Stab ID Format
**Solution**: Ensure stab_id is provided as an integer, use 0 to remove assignment

### Validation Rules
- `stab_id` must be a valid integer ID of an existing Stab
- `stab_id` can be `null`/omitted to leave stab unassigned
- `stab_id` can be `0` to explicitly remove stab assignment (in updates)

## Summary

The addition of the `stab` field to the `Beosztas` model provides enhanced organizational capabilities while maintaining full backward compatibility. All existing functionality continues to work, and the new stab features are optional and additive.

**Key Benefits:**
- **Enhanced Organization**: Assignments can now be grouped by stab
- **Better Filtering**: API consumers can filter assignments by stab
- **Improved Admin UX**: Admin interface supports stab-based management
- **Data Relationships**: Clear relationship between stabs and their assignments
- **Backward Compatible**: No breaking changes to existing functionality

**Implementation Status:**
- ✅ Database model updated
- ✅ Migration created and applied
- ✅ Admin interface enhanced
- ✅ Import/export functionality updated
- ✅ API endpoints updated
- ✅ Response schemas updated
- ✅ Documentation completed

The `stab` field integration is now complete and ready for use across all parts of the FTV system.
