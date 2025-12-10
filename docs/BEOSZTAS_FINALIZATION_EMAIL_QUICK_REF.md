# Quick Reference: Beosztás Véglegesítve Email

## What It Does
Automatically sends email notifications to all assigned users when a Beosztás status changes from **Piszkozat** (Draft, `kesz=False`) to **Kész** (Finalized, `kesz=True`).

## When It Triggers
✅ **ONLY** when status changes: `kesz: False → True`  
❌ NOT on new assignment creation  
❌ NOT on other updates (user changes, etc.)  
❌ NOT on status change: `True → False`

## Email Recipients
All users assigned to the Beosztás who:
- Have a valid email address
- Are active (`is_active=True`)

## Email Content
- **Subject**: `FTV - Beosztás véglegesítve: [Forgatás Name]`
- **Icon**: ✅
- **Message**: Clear finalization notice
- **Details**: Complete forgatás info (date, time, location, contact)
- **Call to Action**: Prepare for the filming session

## Implementation
### Code Locations
- **Email Template**: `backend/backend/email_templates.py` → `get_assignment_finalized_email_content()`
- **Signal Handler**: `backend/api/models.py` → `send_assignment_email()` post_save signal
- **State Tracking**: `backend/api/models.py` → `track_beosztas_state()` pre_save signal

### How It Works
1. **Pre-save**: Captures old `kesz` value
2. **Post-save**: Compares old vs new
3. **If changed to True**: Sends finalization email
4. **Cleanup**: Removes tracking data

## Testing
Run the test script:
```bash
cd backend
python test_beosztas_finalization_email.py
```

## Monitoring
Watch Django logs for:
```
[DEBUG] *** Beosztás status changed from Piszkozat to Kész
[SUCCESS] Beosztás véglegesítve email sent to X users
```

## Troubleshooting
If emails not sending:
1. Check SMTP configuration in settings
2. Verify users have valid email addresses
3. Check that `forgatas` is associated with Beosztás
4. Ensure `forgTipus` is not 'kacsa'
5. Review Django logs for error messages

## Related Files
- Documentation: `backend/docs/BEOSZTAS_FINALIZATION_EMAIL.md`
- Email Templates: `backend/backend/email_templates.py`
- Signal Handlers: `backend/api/models.py`
- Test Script: `backend/test_beosztas_finalization_email.py`
- General Email Docs: `backend/docs/EMAIL_NOTIFICATIONS.md`
