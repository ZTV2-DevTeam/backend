# Tavollet DateTime Migration Guide

## 📋 Overview

This guide covers the migration of the `Tavollet` (absence) model from `DateField` to `DateTimeField` for `start_date` and `end_date` fields. This change enables more precise absence tracking with timestamps instead of just dates.

## 🔄 Changes Made

### Model Changes

#### Before (DateField)
```python
class Tavollet(models.Model):
    start_date = models.DateField(verbose_name='Kezdő dátum')
    end_date = models.DateField(verbose_name='Záró dátum')
```

#### After (DateTimeField)
```python
class Tavollet(models.Model):
    start_date = models.DateTimeField(verbose_name='Kezdő időpont')
    end_date = models.DateTimeField(verbose_name='Záró időpont')
```

### API Changes

#### Request Format Changes

**Before (Date only):**
```json
{
  "start_date": "2024-03-15",
  "end_date": "2024-03-16"
}
```

**After (DateTime with timestamps):**
```json
{
  "start_date": "2024-03-15T09:00:00Z",
  "end_date": "2024-03-16T17:00:00Z"
}
```

#### Response Format Changes

**Before:**
```json
{
  "id": 1,
  "start_date": "2024-03-15",
  "end_date": "2024-03-16",
  "duration_days": 2
}
```

**After:**
```json
{
  "id": 1,
  "start_date": "2024-03-15T09:00:00Z",
  "end_date": "2024-03-16T17:00:00Z",
  "duration_days": 2
}
```

## 🛠️ Migration Steps

### 1. Database Migration

Run the Django migration to update the database schema:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

### 2. API Client Updates

#### Frontend/Client Changes Required

1. **Date Input Handling**
   - Update date pickers to include time selection
   - Convert date-only inputs to datetime with default times
   - Handle timezone conversions if needed

2. **Request Formatting**
   ```javascript
   // Before
   const absenceData = {
     start_date: "2024-03-15",
     end_date: "2024-03-16"
   };

   // After
   const absenceData = {
     start_date: "2024-03-15T09:00:00Z",
     end_date: "2024-03-16T17:00:00Z"
   };
   ```

3. **Response Parsing**
   ```javascript
   // Before
   const startDate = new Date(response.start_date);

   // After (same, but now includes time)
   const startDateTime = new Date(response.start_date);
   ```

## 📡 Updated API Endpoints

### POST /api/absences
Create a new absence with datetime precision.

**Request Body:**
```json
{
  "start_date": "2024-03-15T09:00:00Z",
  "end_date": "2024-03-16T17:00:00Z",
  "reason": "Medical appointment"
}
```

**Response:**
```json
{
  "id": 123,
  "user": {
    "id": 45,
    "username": "john.doe",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "Doe John"
  },
  "start_date": "2024-03-15T09:00:00Z",
  "end_date": "2024-03-16T17:00:00Z",
  "reason": "Medical appointment",
  "denied": false,
  "approved": false,
  "duration_days": 2,
  "status": "függőben"
}
```

### PUT /api/absences/{id}
Update an existing absence with datetime precision.

**Request Body:**
```json
{
  "start_date": "2024-03-15T10:00:00Z",
  "end_date": "2024-03-16T16:00:00Z"
}
```

### GET /api/absences/user/{user_id}/conflicts
Check for absence conflicts with datetime precision.

**Parameters:**
- `start_date`: ISO datetime string (e.g., "2024-03-15T09:00:00Z")
- `end_date`: ISO datetime string (e.g., "2024-03-16T17:00:00Z")

**Example:**
```
GET /api/absences/user/123/conflicts?start_date=2024-03-15T09:00:00Z&end_date=2024-03-16T17:00:00Z
```

## ⚠️ Breaking Changes

### For API Clients

1. **Date Format Validation**
   - API now expects ISO datetime strings instead of date-only strings
   - Invalid datetime formats will return 400 Bad Request

2. **Overlap Detection**
   - More precise overlap detection using datetime comparison
   - Previously, full-day overlaps were checked; now hour-level precision

3. **Admin Interface**
   - Admin date range display now includes time information
   - Export/import formats updated to include timestamps

### Backward Compatibility

#### Date-only Input Support
The API maintains some backward compatibility:

```python
# The API will attempt to parse date-only strings and convert them
# Date-only input: "2024-03-15"
# Converts to: "2024-03-15T00:00:00" (start of day)
# And: "2024-03-15T23:59:59" (end of day) for end_date
```

However, **it's recommended to update clients to use full datetime strings**.

## 🔍 Testing Changes

### Test Cases to Update

1. **Absence Creation Tests**
   ```python
   # Before
   data = {
       "start_date": "2024-03-15",
       "end_date": "2024-03-16"
   }

   # After
   data = {
       "start_date": "2024-03-15T09:00:00Z",
       "end_date": "2024-03-16T17:00:00Z"
   }
   ```

2. **Overlap Detection Tests**
   ```python
   # Test precise datetime overlaps
   absence1 = Tavollet.objects.create(
       start_date=datetime(2024, 3, 15, 9, 0),
       end_date=datetime(2024, 3, 15, 17, 0)
   )
   
   absence2 = Tavollet.objects.create(
       start_date=datetime(2024, 3, 15, 16, 0),  # Overlaps by 1 hour
       end_date=datetime(2024, 3, 15, 18, 0)
   )
   ```

3. **Duration Calculation Tests**
   ```python
   # Duration calculation now considers datetime fields
   absence = Tavollet.objects.create(
       start_date=datetime(2024, 3, 15, 9, 0),
       end_date=datetime(2024, 3, 17, 17, 0)
   )
   # duration_days = 3 (considers date portion for day calculation)
   ```

## 📋 Validation Rules

### DateTime Format Requirements

1. **ISO Format**: `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS±HHMM`
2. **Examples:**
   - `2024-03-15T09:00:00Z` (UTC)
   - `2024-03-15T09:00:00+01:00` (CET)
   - `2024-03-15T09:00:00` (Local time, will be interpreted as system timezone)

### Business Logic Validation

1. **Start Before End**: `start_date` must be before `end_date`
2. **Overlap Prevention**: No overlapping non-denied absences for the same user
3. **Future Dates**: Can create absences for future dates
4. **Past Dates**: May have restrictions based on business rules

## 🔧 Implementation Details

### Database Schema Changes

```sql
-- Migration will change column types
ALTER TABLE api_tavollet 
    ALTER COLUMN start_date TYPE timestamp,
    ALTER COLUMN end_date TYPE timestamp;
```

### Query Optimization

Updated database queries for better performance with datetime comparisons:

```python
# Before (date comparison)
Tavollet.objects.filter(
    start_date__lte=check_date,
    end_date__gte=check_date
)

# After (datetime comparison) 
Tavollet.objects.filter(
    start_date__lt=check_end_datetime,
    end_date__gt=check_start_datetime
)
```

## 🚀 Deployment Checklist

### Pre-deployment

- [ ] Update API client code to handle datetime fields
- [ ] Update frontend date/time pickers
- [ ] Update test cases
- [ ] Backup existing absence data

### Deployment

- [ ] Run database migrations
- [ ] Deploy updated API code
- [ ] Deploy updated frontend code
- [ ] Update API documentation

### Post-deployment

- [ ] Verify datetime format validation
- [ ] Test absence creation/update flows
- [ ] Verify overlap detection accuracy
- [ ] Check admin interface functionality
- [ ] Validate export/import processes

## 🐛 Troubleshooting

### Common Issues

1. **Invalid DateTime Format**
   ```
   Error: "Hibás dátum/idő formátum. Használj ISO formátumot"
   Solution: Use ISO datetime format (YYYY-MM-DDTHH:MM:SSZ)
   ```

2. **Timezone Issues**
   ```
   Problem: Times appearing different in different timezones
   Solution: Always use UTC (Z suffix) or explicit timezone offsets
   ```

3. **Migration Errors**
   ```
   Error: Cannot convert existing date data to datetime
   Solution: Ensure all existing data is valid before migration
   ```

### Data Migration Considerations

If you have existing date-only data, the migration will:
- Convert `start_date` to `start_date 00:00:00`
- Convert `end_date` to `end_date 23:59:59`

This ensures no data loss and maintains logical absence periods.

## 📞 Support

For issues or questions regarding this migration:

1. Check the API documentation at `/api/docs`
2. Review error messages for specific format requirements
3. Test with simple datetime strings first
4. Contact the development team for complex migration scenarios

## 📝 Changelog

### Version 2.1.0 (Current)
- Changed `Tavollet.start_date` from `DateField` to `DateTimeField`
- Changed `Tavollet.end_date` from `DateField` to `DateTimeField`
- Updated all API endpoints to handle datetime strings
- Enhanced overlap detection with hour-level precision
- Updated admin interface to display time information
- Modified export/import to include timestamps

### Migration Timeline
- **Development**: Models and API updated
- **Testing**: Comprehensive testing of datetime handling
- **Staging**: Integration testing with frontend
- **Production**: Coordinated deployment of backend and frontend
