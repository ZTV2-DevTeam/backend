"""
Django management command to synchronize the osztalyfonok boolean field
with actual class teacher assignments.

This command will:
1. Set osztalyfonok=True for users who are assigned to classes as teachers
2. Set osztalyfonok=False for users who are marked as class teachers but not assigned to any class
3. Report on changes made

Usage: python manage.py sync_class_teachers
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Profile, Osztaly


class Command(BaseCommand):
    help = 'Synchronize the osztalyfonok boolean field with actual class teacher assignments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be changed without actually making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Get all users with profiles
        profiles = Profile.objects.select_related('user').all()
        
        changes_made = 0
        users_set_true = []
        users_set_false = []
        
        for profile in profiles:
            user = profile.user
            
            # Check if user is actually assigned to any class as teacher
            has_class_assignments = Osztaly.objects.filter(osztaly_fonokei=user).exists()
            
            # Check current state
            current_state = profile.osztalyfonok
            
            if has_class_assignments and not current_state:
                # User should be marked as class teacher but isn't
                users_set_true.append(user.get_full_name())
                if not dry_run:
                    profile.osztalyfonok = True
                    profile.save()
                    changes_made += 1
                    
            elif not has_class_assignments and current_state:
                # User is marked as class teacher but has no assignments
                users_set_false.append(user.get_full_name())
                if not dry_run:
                    profile.osztalyfonok = False
                    profile.save()
                    changes_made += 1
        
        # Report results
        if users_set_true:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Users to be marked as class teachers ({len(users_set_true)}):'
                )
            )
            for user_name in users_set_true:
                self.stdout.write(f'  - {user_name}')
        
        if users_set_false:
            self.stdout.write(
                self.style.WARNING(
                    f'Users to be unmarked as class teachers ({len(users_set_false)}):'
                )
            )
            for user_name in users_set_false:
                self.stdout.write(f'  - {user_name}')
        
        if not users_set_true and not users_set_false:
            self.stdout.write(
                self.style.SUCCESS('All users are already properly synchronized!')
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Would make {len(users_set_true) + len(users_set_false)} changes. '
                    'Run without --dry-run to apply changes.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully synchronized {changes_made} profiles.'
                )
            )
        
        # Show summary of current class teacher assignments
        self.stdout.write('\n' + self.style.HTTP_INFO('Current class teacher assignments:'))
        
        classes_with_teachers = Osztaly.objects.filter(osztaly_fonokei__isnull=False).distinct()
        
        if classes_with_teachers.exists():
            for osztaly in classes_with_teachers:
                teachers = osztaly.get_osztaly_fonokei()
                teacher_names = [t.get_full_name() for t in teachers]
                self.stdout.write(f'  {osztaly}: {", ".join(teacher_names)}')
        else:
            self.stdout.write('  No classes have assigned teachers.')
