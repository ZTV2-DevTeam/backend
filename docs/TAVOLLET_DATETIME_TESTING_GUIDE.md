# Tavollet DateTime Migration Testing Guide

## 📋 Overview

This guide provides comprehensive testing procedures for validating the Tavollet model migration from DateField to DateTimeField. Follow these tests to ensure the migration was successful and all functionality works correctly.

## 🧪 Pre-Migration Testing

### 1. Backup Verification
```bash
# Create database backup before migration
pg_dump your_database > pre_migration_backup.sql

# Verify backup integrity
pg_restore --list pre_migration_backup.sql
```

### 2. Data Integrity Check
```sql
-- Count existing records
SELECT COUNT(*) FROM api_tavollet;

-- Check for any NULL dates
SELECT id, user_id, start_date, end_date 
FROM api_tavollet 
WHERE start_date IS NULL OR end_date IS NULL;

-- Verify date ranges are logical
SELECT id, start_date, end_date 
FROM api_tavollet 
WHERE start_date > end_date;
```

## 🔄 Migration Testing

### 1. Run Migration Commands
```bash
cd backend
python manage.py makemigrations
python manage.py migrate --dry-run  # Test migration without applying
python manage.py migrate            # Apply migration
```

### 2. Verify Schema Changes
```sql
-- Check column types after migration
\d api_tavollet

-- Expected output should show:
-- start_date | timestamp with time zone
-- end_date   | timestamp with time zone
```

### 3. Data Validation Post-Migration
```sql
-- Verify all records still exist
SELECT COUNT(*) FROM api_tavollet;

-- Check datetime format
SELECT id, start_date, end_date 
FROM api_tavollet 
LIMIT 5;

-- Verify time components are set correctly
-- start_date should be 00:00:00, end_date should be 23:59:59
SELECT 
    id,
    EXTRACT(HOUR FROM start_date) as start_hour,
    EXTRACT(MINUTE FROM start_date) as start_minute,
    EXTRACT(HOUR FROM end_date) as end_hour,
    EXTRACT(MINUTE FROM end_date) as end_minute
FROM api_tavollet 
LIMIT 10;
```

## 🔧 API Testing

### 1. Authentication Setup
```bash
# Get JWT token for testing
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}'

# Export token for use in tests
export JWT_TOKEN="your_jwt_token_here"
```

### 2. Create Absence with DateTime
```bash
# Test creating absence with datetime
curl -X POST http://localhost:8000/api/absences/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-03-15T09:00:00Z",
    "end_date": "2024-03-16T17:00:00Z",
    "reason": "Test datetime absence"
  }'

# Expected: 201 Created with absence object containing datetime fields
```

### 3. Test Invalid DateTime Formats
```bash
# Test with invalid format (should fail)
curl -X POST http://localhost:8000/api/absences/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-03-15",
    "end_date": "2024-03-16",
    "reason": "Test old format"
  }'

# Expected: 400 Bad Request with format error message
```

### 4. Test DateTime Overlap Detection
```bash
# Create first absence
curl -X POST http://localhost:8000/api/absences/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-03-20T09:00:00Z",
    "end_date": "2024-03-20T17:00:00Z",
    "reason": "First absence"
  }'

# Try to create overlapping absence
curl -X POST http://localhost:8000/api/absences/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-03-20T16:00:00Z",
    "end_date": "2024-03-20T18:00:00Z",
    "reason": "Overlapping absence"
  }'

# Expected: 400 Bad Request with overlap error message
```

### 5. Test Non-Overlapping Adjacent Times
```bash
# Create absence ending at specific time
curl -X POST http://localhost:8000/api/absences/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-03-25T09:00:00Z",
    "end_date": "2024-03-25T12:00:00Z",
    "reason": "Morning absence"
  }'

# Create adjacent absence starting exactly when first ends
curl -X POST http://localhost:8000/api/absences/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-03-25T12:00:00Z",
    "end_date": "2024-03-25T17:00:00Z",
    "reason": "Afternoon absence"
  }'

# Expected: 201 Created (no overlap, adjacent times are allowed)
```

### 6. Test Update with DateTime
```bash
# Update existing absence (replace {id} with actual ID)
curl -X PUT http://localhost:8000/api/absences/{id}/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-03-15T10:00:00Z",
    "end_date": "2024-03-16T16:00:00Z"
  }'

# Expected: 200 OK with updated absence object
```

### 7. Test Conflict Checking
```bash
# Check for conflicts in specific datetime range
curl -X GET "http://localhost:8000/api/absences/user/123/conflicts?start_date=2024-03-15T08:00:00Z&end_date=2024-03-15T18:00:00Z" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: 200 OK with conflict information
```

### 8. Test List with DateTime Filtering
```bash
# Get absences in date range
curl -X GET "http://localhost:8000/api/absences/?start_date=2024-03-01T00:00:00Z&end_date=2024-03-31T23:59:59Z" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: 200 OK with filtered absence list
```

## 🎯 Unit Testing

### 1. Model Tests
Create `test_tavollet_datetime.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from datetime import datetime, timezone
from api.models import Tavollet

class TavolletDateTimeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_create_with_datetime(self):
        """Test creating absence with datetime fields"""
        start_dt = datetime(2024, 3, 15, 9, 0, tzinfo=timezone.utc)
        end_dt = datetime(2024, 3, 16, 17, 0, tzinfo=timezone.utc)
        
        absence = Tavollet.objects.create(
            user=self.user,
            start_date=start_dt,
            end_date=end_dt,
            reason="Test absence"
        )
        
        self.assertEqual(absence.start_date, start_dt)
        self.assertEqual(absence.end_date, end_dt)
        self.assertIsInstance(absence.start_date, datetime)
        self.assertIsInstance(absence.end_date, datetime)
    
    def test_string_representation(self):
        """Test __str__ method with datetime"""
        start_dt = datetime(2024, 3, 15, 9, 0, tzinfo=timezone.utc)
        end_dt = datetime(2024, 3, 16, 17, 0, tzinfo=timezone.utc)
        
        absence = Tavollet.objects.create(
            user=self.user,
            start_date=start_dt,
            end_date=end_dt
        )
        
        expected = f"{self.user.get_full_name()}: 2024-03-15 09:00 - 2024-03-16 17:00"
        self.assertIn("2024-03-15 09:00", str(absence))
        self.assertIn("2024-03-16 17:00", str(absence))
    
    def test_overlap_detection(self):
        """Test datetime-based overlap detection"""
        # Create first absence
        Tavollet.objects.create(
            user=self.user,
            start_date=datetime(2024, 3, 15, 9, 0, tzinfo=timezone.utc),
            end_date=datetime(2024, 3, 15, 17, 0, tzinfo=timezone.utc)
        )
        
        # Test overlapping absence detection
        overlapping = Tavollet.objects.filter(
            user=self.user,
            start_date__lt=datetime(2024, 3, 15, 18, 0, tzinfo=timezone.utc),
            end_date__gt=datetime(2024, 3, 15, 16, 0, tzinfo=timezone.utc),
            denied=False
        ).exists()
        
        self.assertTrue(overlapping)
        
        # Test non-overlapping
        non_overlapping = Tavollet.objects.filter(
            user=self.user,
            start_date__lt=datetime(2024, 3, 16, 9, 0, tzinfo=timezone.utc),
            end_date__gt=datetime(2024, 3, 16, 8, 0, tzinfo=timezone.utc),
            denied=False
        ).exists()
        
        self.assertFalse(non_overlapping)
```

### 2. API Tests
Create `test_absence_api_datetime.py`:

```python
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from datetime import datetime, timezone
import json

class AbsenceAPIDateTimeTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_absence_with_datetime(self):
        """Test creating absence via API with datetime"""
        data = {
            'start_date': '2024-03-15T09:00:00Z',
            'end_date': '2024-03-16T17:00:00Z',
            'reason': 'Test datetime absence'
        }
        
        response = self.client.post('/api/absences/', data, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['start_date'], '2024-03-15T09:00:00Z')
        self.assertEqual(response.data['end_date'], '2024-03-16T17:00:00Z')
    
    def test_invalid_datetime_format(self):
        """Test API rejects invalid datetime format"""
        data = {
            'start_date': '2024-03-15',  # Date only, should fail
            'end_date': '2024-03-16',
            'reason': 'Test invalid format'
        }
        
        response = self.client.post('/api/absences/', data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('formátum', response.data['message'].lower())
    
    def test_overlap_detection_api(self):
        """Test API overlap detection with datetime precision"""
        # Create first absence
        data1 = {
            'start_date': '2024-03-15T09:00:00Z',
            'end_date': '2024-03-15T17:00:00Z',
            'reason': 'First absence'
        }
        response1 = self.client.post('/api/absences/', data1, format='json')
        self.assertEqual(response1.status_code, 201)
        
        # Try overlapping absence
        data2 = {
            'start_date': '2024-03-15T16:00:00Z',
            'end_date': '2024-03-15T18:00:00Z',
            'reason': 'Overlapping absence'
        }
        response2 = self.client.post('/api/absences/', data2, format='json')
        
        self.assertEqual(response2.status_code, 400)
        self.assertIn('átfedő', response2.data['message'].lower())
```

### 3. Run Tests
```bash
# Run specific test files
python manage.py test tests.test_tavollet_datetime
python manage.py test tests.test_absence_api_datetime

# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 🔍 Integration Testing

### 1. User Availability Check
```python
# Test Profile.is_available_for_datetime method
from api.models import Profile, Tavollet
from datetime import datetime, timezone

user = User.objects.get(username='testuser')
profile = user.profile

# Create absence
Tavollet.objects.create(
    user=user,
    start_date=datetime(2024, 3, 15, 9, 0, tzinfo=timezone.utc),
    end_date=datetime(2024, 3, 15, 17, 0, tzinfo=timezone.utc)
)

# Test availability
available = profile.is_available_for_datetime(
    datetime(2024, 3, 15, 16, 0, tzinfo=timezone.utc),  # During absence
    datetime(2024, 3, 15, 18, 0, tzinfo=timezone.utc)
)
assert not available  # Should be False (unavailable)

available = profile.is_available_for_datetime(
    datetime(2024, 3, 16, 9, 0, tzinfo=timezone.utc),   # After absence
    datetime(2024, 3, 16, 17, 0, tzinfo=timezone.utc)
)
assert available  # Should be True (available)
```

### 2. Assignment Conflict Detection
```python
# Test assignment module integration
from backend.api_modules.assignments import check_user_availability_for_forgatas
from api.models import Forgatas, Partner

# Create forgatas
partner = Partner.objects.create(name='Test Location')
forgatas = Forgatas.objects.create(
    name='Test Filming',
    date=datetime(2024, 3, 15).date(),
    timeFrom=datetime(2024, 3, 15, 14, 0).time(),
    timeTo=datetime(2024, 3, 15, 16, 0).time(),
    location=partner
)

# Check availability (should return conflict)
conflicts = check_user_availability_for_forgatas(user, forgatas)
assert len(conflicts) > 0  # Should have vacation conflict
```

## 📊 Performance Testing

### 1. Query Performance
```sql
-- Test query performance with datetime fields
EXPLAIN ANALYZE 
SELECT * FROM api_tavollet 
WHERE start_date < '2024-03-15T18:00:00Z' 
  AND end_date > '2024-03-15T16:00:00Z';

-- Compare with index usage
CREATE INDEX idx_tavollet_datetime_range ON api_tavollet (start_date, end_date);

EXPLAIN ANALYZE 
SELECT * FROM api_tavollet 
WHERE start_date < '2024-03-15T18:00:00Z' 
  AND end_date > '2024-03-15T16:00:00Z';
```

### 2. Bulk Operation Testing
```python
# Test creating many absences
import time
from django.test import TransactionTestCase

class BulkAbsenceTest(TransactionTestCase):
    def test_bulk_create_performance(self):
        start_time = time.time()
        
        absences = []
        for i in range(1000):
            absences.append(Tavollet(
                user=self.user,
                start_date=datetime(2024, 3, i % 28 + 1, 9, 0, tzinfo=timezone.utc),
                end_date=datetime(2024, 3, i % 28 + 1, 17, 0, tzinfo=timezone.utc),
                reason=f'Bulk test {i}'
            ))
        
        Tavollet.objects.bulk_create(absences)
        
        end_time = time.time()
        print(f'Bulk create of 1000 absences took {end_time - start_time:.2f} seconds')
        
        # Should complete in reasonable time (< 5 seconds)
        self.assertLess(end_time - start_time, 5.0)
```

## ✅ Validation Checklist

### Database Level
- [ ] Schema updated to datetime fields
- [ ] All existing data migrated correctly
- [ ] No data loss occurred
- [ ] Datetime values have appropriate time components
- [ ] Indexes created for performance

### API Level
- [ ] All endpoints accept datetime format
- [ ] Invalid formats rejected with clear error messages
- [ ] Overlap detection works with hour precision
- [ ] Response format includes datetime strings
- [ ] Filtering by datetime ranges works correctly

### Business Logic
- [ ] User availability checking uses datetime precision
- [ ] Assignment conflict detection updated
- [ ] Duration calculation considers date portion
- [ ] Status determination based on current datetime

### Admin Interface
- [ ] Admin forms accept datetime input
- [ ] List display shows datetime information
- [ ] Filtering by datetime works
- [ ] Export/import handles datetime format

### Performance
- [ ] Query performance acceptable
- [ ] Bulk operations complete in reasonable time
- [ ] Database indexes utilized effectively
- [ ] Memory usage within normal ranges

## 🚨 Rollback Procedure

If issues are found, rollback steps:

```bash
# 1. Stop application
sudo systemctl stop your_app

# 2. Restore database backup
pg_restore --clean --create -d your_database pre_migration_backup.sql

# 3. Revert code changes
git revert migration_commit_hash

# 4. Restart application
sudo systemctl start your_app

# 5. Verify rollback
python manage.py shell
>>> from api.models import Tavollet
>>> t = Tavollet.objects.first()
>>> type(t.start_date)  # Should be datetime.date, not datetime.datetime
```

## 📝 Test Report Template

```markdown
# Tavollet DateTime Migration Test Report

## Test Environment
- Database: PostgreSQL 13.x
- Django Version: 4.x
- Python Version: 3.x
- Test Date: YYYY-MM-DD

## Pre-Migration Status
- [ ] Data backup completed
- [ ] Record count verified: ___ records
- [ ] No invalid dates found

## Migration Execution
- [ ] makemigrations completed successfully
- [ ] migrate --dry-run passed
- [ ] migrate completed without errors
- [ ] Schema verification passed

## API Testing Results
- [ ] DateTime creation: PASS/FAIL
- [ ] Invalid format rejection: PASS/FAIL
- [ ] Overlap detection: PASS/FAIL
- [ ] Update operations: PASS/FAIL
- [ ] Conflict checking: PASS/FAIL

## Performance Testing
- [ ] Query performance acceptable: PASS/FAIL
- [ ] Bulk operations within limits: PASS/FAIL

## Issues Found
1. _Issue description_
   - Status: RESOLVED/PENDING
   - Solution: _Description_

## Final Status
- [ ] Migration successful
- [ ] All tests passing
- [ ] Ready for production
- [ ] Rollback required

## Sign-off
- Developer: ___________
- QA: ___________
- Date: ___________
```
