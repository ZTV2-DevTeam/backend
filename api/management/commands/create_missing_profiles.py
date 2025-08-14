from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Profile

class Command(BaseCommand):
    help = 'Creates missing Profile records for all users who do not have them'

    def handle(self, *args, **options):
        users_without_profiles = []
        
        for user in User.objects.all():
            try:
                # Try to access user.profile
                profile = user.profile
                self.stdout.write(f"✓ User {user.username} already has profile")
            except Profile.DoesNotExist:
                users_without_profiles.append(user)
                self.stdout.write(f"✗ User {user.username} missing profile")
        
        if users_without_profiles:
            self.stdout.write(f"\nCreating profiles for {len(users_without_profiles)} users...")
            
            for user in users_without_profiles:
                profile = Profile.objects.create(
                    user=user,
                    medias=True,  # Default to media student
                    admin_type='none',  # No admin permissions by default
                    password_set=True  # Assume password is set if user exists
                )
                self.stdout.write(f"✓ Created profile for user: {user.username}")
        
        else:
            self.stdout.write("All users already have profiles!")
        
        self.stdout.write(f"\n✅ Completed! Processed {User.objects.count()} users.")
