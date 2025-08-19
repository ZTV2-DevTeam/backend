# FTV Email Notification System

## Overview

The FTV system now includes comprehensive email notifications for announcements and assignment changes. This system automatically sends professional HTML emails to keep users informed about important updates.

## Features

### 📢 Announcement Notifications

**When emails are sent:**
- New announcement created with specific recipients → Emails sent to those recipients
- New announcement created without recipients (global) → Emails sent to ALL active users
- Announcement updated with content changes → Emails sent to existing recipients
- Announcement updated with new recipients → Emails sent to newly added recipients

**Email content includes:**
- Professional HTML template with FTV branding
- Announcement title and full content
- Author information and timestamp
- Direct link to FTV system
- Plain text fallback for compatibility

### 🎬 Assignment (Beosztás) Notifications

**When emails are sent:**
- New assignment created → Emails sent to all assigned users
- Assignment updated with user changes → Separate emails for added/removed users
- Assignment finalized → Confirmation emails sent to all assigned users

**Email content includes:**
- Assignment type (new assignment, modification, removal)
- Filming session details (name, description, date, time, location)
- Contact person information (if available)
- Professional formatting with color-coded headers

## SMTP Protection

To avoid being blocked by Google SMTP and other providers:

- **Single BCC Email**: All recipients are added as BCC to a single email
- **Rate Limiting**: No individual emails per user for bulk notifications
- **Graceful Errors**: Email failures don't break the API functionality
- **Detailed Logging**: All email activities are logged for troubleshooting

## Email Templates

### Announcement Email Template
```html
📢 Új közlemény érkezett

Cím: [Announcement Title]
Feladó: [Author Name]
Dátum: [Creation Date]

Tartalom:
[Announcement Body]

A teljes közlemény megtekintéséhez látogassa meg a FTV rendszert:
[Frontend URL]
```

### Assignment Addition Email Template
```html
🎬 Új forgatási beosztás

Kedves Kollégák!

Önt beosztották a következő forgatáshoz:

Forgatás: [Name]
Leírás: [Description]
Dátum: [Date]
Időpont: [Time From] - [Time To]
Helyszín: [Location]
Kapcsolattartó: [Contact Person]

Kérjük, készüljön fel a megadott időpontra!
```

### Assignment Removal Email Template
```html
📝 Beosztás módosítás

Kedves Kollégák!

A beosztása módosításra került a következő forgatásnál:

Forgatás: [Name]
Dátum: [Date]
Időpont: [Time From] - [Time To]

Önt eltávolították ebből a beosztásból.
Már nem szükséges részt vennie ezen a forgatáson.
```

## API Usage

### Test Email Functionality

**Test Announcement Email:**
```bash
POST /api/communications/test-email
Authorization: Bearer {token}
```

**Test Assignment Email:**
```bash
POST /api/assignments/test-email
Authorization: Bearer {token}
```

### Create Announcement with Email
```bash
POST /api/communications/announcements
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Important School Notice",
  "body": "This is an important announcement...",
  "recipient_ids": [1, 2, 3]  // or [] for all users
}
```

### Update Assignment with Email
```bash
PUT /api/assignments/filming-assignments/123
Authorization: Bearer {token}
Content-Type: application/json

{
  "student_role_pairs": [
    {"user_id": 1, "szerepkor_id": 2},
    {"user_id": 3, "szerepkor_id": 4}
  ]
}
```

## Configuration

Ensure your email settings are properly configured in `local_settings.py`:

```python
# Email settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "your-email@gmail.com"
EMAIL_HOST_PASSWORD = "your-app-password"
DEFAULT_FROM_EMAIL = "FTV System <your-email@gmail.com>"

# Frontend URL for email links
FRONTEND_URL = "https://ftv.szlg.info"
```

## Testing

### Manual Testing

1. **Run the test script:**
   ```bash
   python test_email_notifications.py
   ```

2. **Use API test endpoints:**
   - `/api/communications/test-email` - Test announcement emails
   - `/api/assignments/test-email` - Test assignment emails

3. **Create real announcements/assignments** and verify emails are received

### Automated Testing

The system includes comprehensive error handling:
- Email failures are logged but don't break API functionality
- Invalid email addresses are skipped automatically
- Connection issues are handled gracefully

## Troubleshooting

### Common Issues

**Email not being sent:**
1. Check email configuration in `local_settings.py`
2. Verify SMTP credentials are correct
3. Check if 2-factor authentication requires app passwords
4. Review Django logs for error messages

**Users not receiving emails:**
1. Verify user email addresses are set and valid
2. Check if users are active (`is_active=True`)
3. Check spam folders
4. Verify email server limits aren't exceeded

**SMTP rate limiting:**
1. The system uses BCC to send single emails for bulk notifications
2. Monitor email server logs for rate limit warnings
3. Consider using a dedicated email service for high volume

### Debug Information

Enable debug logging by checking the console output for:
- `[DEBUG]` messages showing email send process
- `[SUCCESS]` messages confirming email delivery
- `[ERROR]` messages indicating failures
- `[WARNING]` messages for non-critical issues

## Security Considerations

- **Email Content**: All email content is escaped to prevent XSS
- **Recipient Privacy**: BCC is used to hide recipient lists
- **Authentication**: Only authenticated users with proper permissions can trigger emails
- **Rate Limiting**: Built-in protection against spam and abuse

## Future Enhancements

Potential improvements for the email system:
- Email templates customization through admin interface
- Email delivery status tracking
- Unsubscribe functionality for non-critical notifications
- Email scheduling for delayed delivery
- Rich HTML email editor for announcements
- Email analytics and open tracking

## Support

For technical support with the email notification system:
1. Check the Django logs for error messages
2. Run the test script to verify configuration
3. Use the API test endpoints to isolate issues
4. Review email server settings and credentials
