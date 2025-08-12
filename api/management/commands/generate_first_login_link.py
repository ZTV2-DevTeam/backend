from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
from api.models import Profile
from datetime import datetime, timedelta
import jwt


class Command(BaseCommand):
    help = 'Generate first-time password login link for a user'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username of the user to generate first login link for'
        )
        parser.add_argument(
            '--frontend-url',
            type=str,
            default='http://localhost:3000',
            help='Frontend URL base (default: http://localhost:3000 for local development)'
        )
        parser.add_argument(
            '--validity-days',
            type=int,
            default=30,
            help='Token validity in days (default: 30)'
        )

    def handle(self, *args, **options):
        username = options['username']
        frontend_url = options['frontend_url']
        validity_days = options['validity_days']

        try:
            # Get user
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')

        # Get or create profile
        profile, created = Profile.objects.get_or_create(user=user)
        if created:
            self.stdout.write(
                self.style.WARNING(f'Profile created for user "{username}"')
            )

        # Generate first login token
        token = self.generate_first_login_token(user.id, validity_days)
        
        # Store token in profile for reference
        profile.first_login_token = token
        profile.save()

        # Generate the login URL
        login_url = f"{frontend_url}/first-login?token={token}"

        # Display results
        self.stdout.write(
            self.style.SUCCESS('\n' + '='*80)
        )
        self.stdout.write(
            self.style.SUCCESS('FIRST-TIME LOGIN LINK GENERATED')
        )
        self.stdout.write(
            self.style.SUCCESS('='*80 + '\n')
        )

        self.stdout.write(f"User: {user.get_full_name()} ({username})")
        self.stdout.write(f"Email: {user.email}")
        self.stdout.write(f"Token validity: {validity_days} days")
        self.stdout.write(f"Frontend URL: {frontend_url}")
        self.stdout.write("")
        
        self.stdout.write(
            self.style.WARNING("First-Time Login Link:")
        )
        self.stdout.write(
            self.style.HTTP_INFO(login_url)
        )
        self.stdout.write("")
        
        self.stdout.write(
            self.style.WARNING("JWT Token (for debugging):")
        )
        self.stdout.write(token)
        self.stdout.write("")

        self.stdout.write("INSTRUCTIONS:")
        self.stdout.write("1. Copy the login link above")
        self.stdout.write("2. Send it to the user via email or other secure method")
        self.stdout.write("3. The user can click the link to set their password")
        self.stdout.write(f"4. The link expires after {validity_days} days")
        self.stdout.write("")

        # Check if user already has a password set
        if profile.password_set:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  WARNING: User already has a password set. "
                    "This link will allow them to reset it."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "✅ User does not have a password set yet. "
                    "This is their first-time login link."
                )
            )

        self.stdout.write(
            self.style.SUCCESS('\n' + '='*80)
        )

    def generate_first_login_token(self, user_id: int, validity_days: int = 30) -> str:
        """Generate JWT token for first-time login."""
        payload = {
            "user_id": user_id,
            "type": "first_login",
            "exp": datetime.utcnow() + timedelta(days=validity_days),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
