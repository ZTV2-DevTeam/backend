# Beosztás Véglegesítve Email Notification Implementation

## Overview

Implemented automatic email notifications that are sent to all assigned users when a Beosztás (assignment) status changes from **Piszkozat (Draft)** to **Kész (Finalized)**.

## Implementation Details

### 1. New Email Template

**File:** `backend/backend/email_templates.py`

Added a new email template function: `get_assignment_finalized_email_content()`

This template generates professional HTML content with:
- ✅ Clear finalization message
- 📋 Complete forgatás details (name, description, date, time, location)
- 👤 Contact person information
- ⚠️ Emphasis that participation is mandatory
- 🎨 Consistent FTV branding and styling

### 2. Status Change Detection

**File:** `backend/api/models.py`

Implemented a two-signal approach to detect status changes:

#### `pre_save` Signal
```python
@receiver(pre_save, sender=Beosztas)
def track_beosztas_state(sender, instance, **kwargs):
```
- Captures the old state of the Beosztás before saving
- Stores the old `kesz` value in a temporary dictionary

#### `post_save` Signal (Updated)
```python
@receiver(post_save, sender=Beosztas)
def send_assignment_email(sender, instance, created, **kwargs):
```
- Checks if status changed from `kesz=False` to `kesz=True`
- Only sends the finalization email when this specific transition occurs
- Prevents duplicate emails on other updates

### 3. Email Sending Logic

When status changes from Piszkozat to Kész:

1. **Collects all assigned users** from the Beosztás
2. **Validates email addresses** (active users with valid emails)
3. **Generates HTML email** using the new template
4. **Sends to all recipients** using the existing email infrastructure
5. **Logs results** for monitoring and debugging

## Key Features

✅ **Specific Trigger**: Only fires when status changes from False → True  
✅ **No Duplicate Emails**: Won't send on assignment creation or other updates  
✅ **Professional Template**: Matches existing FTV email design  
✅ **Detailed Content**: Includes all forgatás information  
✅ **Bulk Send**: Uses BCC to send to multiple recipients efficiently  
✅ **Error Handling**: Gracefully handles email failures without breaking the system  
✅ **Comprehensive Logging**: Debug logs for troubleshooting  

## Email Content

### Subject
```
FTV - Beosztás véglegesítve: [Forgatás Name]
```

### Content Highlights
- Clear "Beosztás véglegesítve" header with ✅ icon
- Complete forgatás details in styled info boxes
- Mandatory participation notice
- Contact information for questions
- Link to FTV system
- Both HTML and plain text versions

## Testing

A comprehensive test script has been created:

**File:** `backend/test_beosztas_finalization_email.py`

### Test Flow
1. Creates a test Forgatas
2. Creates a Beosztás in **Piszkozat** state (`kesz=False`)
3. Assigns test users to the Beosztás
4. Changes status to **Kész** (`kesz=True`)
5. Verifies that the finalization email is sent

### Running the Test
```bash
cd backend
python test_beosztas_finalization_email.py
```

## Files Modified

1. **backend/backend/email_templates.py**
   - Added `get_assignment_finalized_email_content()` function

2. **backend/api/models.py**
   - Added `_beosztas_old_state` dictionary for tracking
   - Added `track_beosztas_state()` pre_save signal
   - Updated `send_assignment_email()` post_save signal

3. **backend/docs/EMAIL_NOTIFICATIONS.md**
   - Updated documentation with new email type
   - Added template example for finalized assignments

4. **backend/test_beosztas_finalization_email.py** (New)
   - Test script for verification

## Usage

The email is automatically sent when:

### Via Django Admin
1. Open a Beosztás with `kesz=False`
2. Change `kesz` to `True`
3. Save → Email sent automatically

### Via API
1. Update assignment with `kesz=True`
2. System detects status change
3. Email sent to all assigned users

### Example API Call
```bash
PUT /api/assignments/filming-assignments/{id}
{
  "kesz": true,
  "student_role_pairs": [...]
}
```

## Monitoring

Check Django logs for:
- `[DEBUG] *** Beosztás status changed from Piszkozat to Kész`
- `[SUCCESS] Beosztás véglegesítve email sent to X users`
- `[WARNING]` messages if any emails fail

## Error Handling

- Email failures don't prevent the Beosztás from being saved
- Failed emails are logged with recipient details
- System continues functioning even if SMTP is unavailable

## Future Enhancements

Potential improvements:
- Add email preview in admin interface
- Configurable email templates via admin
- Email delivery status tracking
- Retry mechanism for failed sends

## Notes

- Emails are NOT sent for KaCsa type forgatások
- Emails are NOT sent if no forgatas is associated with the Beosztás
- Only active users with valid email addresses receive notifications
- Uses the same SMTP configuration as other FTV emails
