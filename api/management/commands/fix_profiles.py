from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Profile


class Command(BaseCommand):
    help = 'Create missing profiles for users who don\'t have one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        # Find users without profiles
        users_without_profiles = User.objects.filter(profile__isnull=True)
        
        if not users_without_profiles.exists():
            self.stdout.write(
                self.style.SUCCESS('All users already have profiles!')
            )
            return

        self.stdout.write(
            f'Found {users_without_profiles.count()} users without profiles:'
        )

        for user in users_without_profiles:
            self.stdout.write(f'  - {user.username} ({user.get_full_name()})')

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('\n--dry-run specified, no changes made.')
            )
            return

        # Create profiles for users without them
        created_count = 0
        for user in users_without_profiles:
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'admin_type': 'developer' if user.is_superuser else 'none',
                    'special_role': 'none',
                    'medias': True,
                    'password_set': True,  # Since they can log in, assume password is set
                    'telefonszam': None,
                    'stab': None,
                    'radio_stab': None,
                    'osztaly': None
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    f'Created profile for {user.username} (admin_type: {profile.admin_type})'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} profiles!'
            )
        )
