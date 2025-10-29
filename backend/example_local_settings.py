DJANGO_SECRET_KEY = 'your-secret-key-here'
DJANGO_DEBUG = True
DJANGO_ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = ''  # Change this to your actual email
EMAIL_HOST_PASSWORD = ''  # Change this to your app password
DEFAULT_FROM_EMAIL = ''

# Password Reset Settings
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour in seconds

# External API Access Token (for Igazoláskezelő integration)
EXTERNAL_ACCESS_TOKEN = 'your-secure-token-here-change-in-production'