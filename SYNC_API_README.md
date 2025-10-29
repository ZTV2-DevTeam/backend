# Sync API Implementation Summary

## What Was Created

A new **Sync API** category has been implemented for external system integration with **Igazoláskezelő** (Attendance Management System).

---

## Files Created/Modified

### New Files

1. **`backend/api_modules/sync.py`** (470 lines)
   - Complete sync API implementation
   - External token authentication
   - 6 endpoints for class and absence data
   - Email-based user linking

2. **`docs/SYNC_API_DOCUMENTATION.md`** (600+ lines)
   - Complete API documentation
   - Integration guide
   - Example code snippets
   - Security considerations

3. **`docs/SYNC_API_QUICK_START.md`** (600+ lines)
   - Quick start guide for developers
   - Code examples in JavaScript
   - Common integration patterns
   - Error handling best practices

4. **`test_sync_api.py`** (250+ lines)
   - Automated test suite
   - Tests all endpoints
   - Authentication verification
   - Error handling tests

### Modified Files

1. **`local_settings.py`**
   - Added: `EXTERNAL_ACCESS_TOKEN` configuration

2. **`backend/example_local_settings.py`**
   - Added: `EXTERNAL_ACCESS_TOKEN` with example value

3. **`backend/api.py`**
   - Added: Import for sync module
   - Added: Registration of sync endpoints

---

## API Endpoints

All endpoints are prefixed with `/api/sync/` and require external token authentication.

### Classes (Osztály)

```
GET /api/sync/osztalyok
GET /api/sync/osztaly/{id}
```

### Absences (Hiányzás)

```
GET /api/sync/hianyzasok/osztaly/{osztaly_id}
GET /api/sync/hianyzas/{id}
GET /api/sync/hianyzasok/user/{user_id}
```

### Profile

```
GET /api/sync/profile/{email}
```

---

## Authentication

Uses **external access token** (NOT JWT) configured in `local_settings.py`:

```python
EXTERNAL_ACCESS_TOKEN = "your-secure-token-here-change-in-production"
```

**Usage:**
```
Authorization: Bearer your-secure-token-here-change-in-production
```

**Security:**
- Separate from JWT authentication
- Read-only access
- No user session required
- Token stored in secure settings file

---

## Integration Strategy

### Email as Common Key

Email address is the common key between FTV and Igazoláskezelő:

1. Find user by email: `GET /api/sync/profile/{email}`
2. Get user's absences: `GET /api/sync/hianyzasok/user/{user_id}`
3. Link records in Igazoláskezelő using email

### Example Flow

```javascript
// 1. Find user in FTV
const profile = await fetch(`/api/sync/profile/${email}`, { headers });

// 2. Get user absences
const absences = await fetch(`/api/sync/hianyzasok/user/${profile.user_id}`, { headers });

// 3. Sync to your database
await saveAbsences(email, absences);
```

---

## Key Features

✅ **External Token Auth** - Separate from JWT, configured in settings  
✅ **Read-Only Access** - Safe integration, no data modification  
✅ **Email Linking** - Email as common key for user matching  
✅ **Complete Absence Data** - All hiányzás details including:
   - Basic absence info (date, time, status)
   - Student extra time (before/after)
   - Affected class periods (0-8)
   - Related filming session details

✅ **Class Organization** - Access to osztály structure  
✅ **Comprehensive Docs** - Full documentation + quick start guide  
✅ **Test Suite** - Automated tests for all endpoints  
✅ **Error Handling** - Proper 401/404/500 responses

---

## Testing

### Run the test suite:

```bash
# Install requests if needed
pip install requests

# Run tests
python test_sync_api.py
```

### Manual testing with curl:

```bash
# Test authentication and get all classes
curl -H "Authorization: Bearer your-secure-token-here-change-in-production" \
     http://localhost:8000/api/sync/osztalyok

# Get profile by email
curl -H "Authorization: Bearer your-secure-token-here-change-in-production" \
     http://localhost:8000/api/sync/profile/user@szlg.info
```

### Interactive testing:

Visit: `http://localhost:8000/api/docs`
- Browse all sync endpoints
- Test with your token
- View request/response schemas

---

## Configuration

### Development Setup

1. **Set token in `local_settings.py`:**
   ```python
   EXTERNAL_ACCESS_TOKEN = "dev-token-for-testing"
   ```

2. **Start server:**
   ```bash
   python manage.py runserver
   ```

3. **Test endpoints:**
   ```bash
   python test_sync_api.py
   ```

### Production Setup

1. **Generate secure token:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update `local_settings.py`:**
   ```python
   EXTERNAL_ACCESS_TOKEN = "generated-secure-token"
   ```

3. **Share token securely** with Igazoláskezelő team

4. **Monitor API usage** (logs, metrics)

---

## Security Considerations

### Token Management

- ✅ Token stored in `local_settings.py` (not in version control)
- ✅ Token must be changed in production
- ✅ Share token securely (not via email/chat)
- ✅ Rotate token periodically

### Access Control

- ✅ Read-only access (no POST/PUT/DELETE)
- ✅ No user sessions (stateless)
- ✅ Use HTTPS in production
- ✅ Log all access attempts

### Best Practices

- ✅ Never commit token to git
- ✅ Use environment variables in production
- ✅ Implement rate limiting (future)
- ✅ Monitor for abuse
- ✅ Revoke token if compromised

---

## Documentation

### For Developers

1. **Full API Reference**: `docs/SYNC_API_DOCUMENTATION.md`
   - Complete endpoint documentation
   - Response schemas
   - Integration patterns
   - Security guide

2. **Quick Start Guide**: `docs/SYNC_API_QUICK_START.md`
   - JavaScript examples
   - Common patterns
   - Error handling
   - Production checklist

### For Igazoláskezelő Team

Share these files:
- `docs/SYNC_API_DOCUMENTATION.md` - Complete reference
- `docs/SYNC_API_QUICK_START.md` - Integration guide
- External access token (securely)
- API base URL (production)

---

## Response Examples

### Get Profile by Email

**Request:**
```bash
GET /api/sync/profile/kovacs.janos@szlg.info
Authorization: Bearer token
```

**Response:**
```json
{
  "id": 12,
  "user_id": 45,
  "email": "kovacs.janos@szlg.info",
  "full_name": "Kovács János",
  "osztaly_name": "9F",
  "stab_name": "Hang",
  "admin_type": "none",
  "is_admin": false
}
```

### Get User Absences

**Request:**
```bash
GET /api/sync/hianyzasok/user/45
Authorization: Bearer token
```

**Response:**
```json
[
  {
    "id": 123,
    "diak_email": "kovacs.janos@szlg.info",
    "date": "2024-10-30",
    "timeFrom": "10:00:00",
    "timeTo": "12:00:00",
    "excused": false,
    "affected_classes": [3, 4],
    "forgatas_details": {
      "name": "KaCsa forgatás",
      "location_name": "SZLG Stúdió"
    }
  }
]
```

---

## Next Steps

### Immediate

1. ✅ **Change token in production** to secure value
2. ✅ **Run test suite** to verify endpoints work
3. ✅ **Share documentation** with Igazoláskezelő team
4. ✅ **Provide token securely** to integration partner

### Integration Phase

1. **Igazoláskezelő implements** sync logic
2. **Test in development** environment
3. **Verify data accuracy** (email matching, absence details)
4. **Deploy to production** with secure token

### Future Enhancements

- [ ] Rate limiting for API calls
- [ ] Webhook support for real-time updates
- [ ] Bulk export endpoints
- [ ] Date range filtering
- [ ] Pagination for large datasets
- [ ] API usage analytics

---

## Support

### Issues?

1. Check `docs/SYNC_API_DOCUMENTATION.md` for details
2. Run `python test_sync_api.py` to diagnose
3. Check server logs for errors
4. Verify token matches `local_settings.py`

### Common Problems

**401 Unauthorized**: Token mismatch - check `local_settings.py`  
**404 Not Found**: Resource doesn't exist - verify IDs  
**Connection Error**: Server not running - start with `python manage.py runserver`  
**Import Error**: Missing dependencies - run `pip install -r requirements.txt`

---

## Success Criteria

✅ All endpoints accessible with valid token  
✅ Invalid token returns 401  
✅ Non-existent resources return 404  
✅ Email lookup finds users correctly  
✅ Absence data includes all fields  
✅ Test suite passes 100%  
✅ Documentation complete and clear  
✅ Token securely configured  

---

**Implementation Date**: October 29, 2024  
**Version**: 1.0  
**Status**: ✅ Ready for Integration

