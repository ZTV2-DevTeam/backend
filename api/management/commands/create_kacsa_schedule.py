#!/usr/bin/env python
"""
Django Management Command for KaCsa Schedule Creation

Usage:
    python manage.py create_kacsa_schedule --dry-run
    python manage.py create_kacsa_schedule --create
    python manage.py create_kacsa_schedule --create --auto-finalize
    python manage.py create_kacsa_schedule --goc-missing-users --dry-run
    python manage.py create_kacsa_schedule --goc-missing-users --create
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from api.models import (
    Forgatas, Beosztas, Szerepkor, SzerepkorRelaciok, 
    Tanev, Stab, Partner, PartnerTipus
)
from datetime import datetime, date, time
import sys

class Command(BaseCommand):
    help = 'Create KaCsa schedule for 2025-26 school year'

    def create_missing_users_from_registry(self, script_globals):
        """
        Create missing users from the NAME_REGISTRY with default settings.
        """
        NAME_REGISTRY = script_globals['NAME_REGISTRY']
        created_users = []
        
        self.stdout.write("🔧 Creating missing users from registry...")
        self.stdout.write("-" * 50)
        
        for literal_name, username in NAME_REGISTRY.items():
            try:
                # Check if user already exists
                user = User.objects.get(username=username)
                self.stdout.write(f"✅ User already exists: {username} ({literal_name})")
            except User.DoesNotExist:
                # Create new user
                try:
                    user = User.objects.create_user(
                        username=username,
                        email=f"{username}@botond.eu",
                        password="demo123",
                        first_name=literal_name.split()[0] if literal_name.split() else "",
                        last_name=" ".join(literal_name.split()[1:]) if len(literal_name.split()) > 1 else ""
                    )
                    created_users.append((literal_name, username))
                    self.stdout.write(
                        self.style.SUCCESS(f"✨ Created user: {username} ({literal_name}) - email: {username}@botond.eu")
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Failed to create user {username} ({literal_name}): {e}")
                    )
        
        if created_users:
            self.stdout.write(f"\n📊 Created {len(created_users)} new users")
            self.stdout.write("All users have email format: username@botond.eu and password: demo123")
        else:
            self.stdout.write("No new users needed to be created")
        
        return created_users

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and preview only, do not create records',
        )
        parser.add_argument(
            '--create',
            action='store_true',
            help='Actually create the database records',
        )
        parser.add_argument(
            '--auto-finalize',
            action='store_true',
            help='Automatically finalize all beosztások (use with --create)',
        )
        parser.add_argument(
            '--skip-confirmation',
            action='store_true',
            help='Skip user confirmation prompt (use with --create)',
        )
        parser.add_argument(
            '--goc-missing-users',
            action='store_true',
            help='Get or create missing users with default settings (username@botond.eu, demo123)',
        )

    def handle(self, *args, **options):
        # Load the script functions by executing the script file
        import os
        
        # Get the path to the KaCsa script
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        script_path = os.path.join(base_dir, 'one_time_scripts', 'kacsa_teljes_tanev_25_26.py')
        
        if not os.path.exists(script_path):
            raise CommandError(f"KaCsa script not found at: {script_path}")
        
        try:
            # Execute the script to load functions into current namespace
            script_globals = {}
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            exec(script_content, script_globals)
            
            # Extract the functions we need
            validate_name_registry = script_globals['validate_name_registry']
            process_kacsa_schedule = script_globals['process_kacsa_schedule']
            
        except Exception as e:
            raise CommandError(f"Could not load KaCsa script: {e}")

        # Validate arguments
        if not options['dry_run'] and not options['create']:
            raise CommandError("You must specify either --dry-run or --create")
        
        if options['dry_run'] and options['create']:
            raise CommandError("Cannot use both --dry-run and --create at the same time")
        
        if options['auto_finalize'] and not options['create']:
            raise CommandError("--auto-finalize can only be used with --create")

        # Start processing
        self.stdout.write(
            self.style.SUCCESS('🎯 KaCsa Teljes Tanév 2025-26 Management Command')
        )
        self.stdout.write("=" * 60)
        
        # Handle missing users if requested
        if options['goc_missing_users']:
            self.create_missing_users_from_registry(script_globals)
            self.stdout.write("")  # Add spacing
        
        # First validate the name registry
        self.stdout.write("Validating name registry...")
        validation_passed = validate_name_registry()
        
        if not validation_passed:
            if options['goc_missing_users']:
                self.stdout.write(
                    self.style.WARNING("⚠️  Some users are still missing after creation attempt.")
                )
            raise CommandError("Name registry validation failed. Please fix missing users or use --goc-missing-users flag.")
        
        # Determine mode
        dry_run = options['dry_run']
        auto_finalize = options['auto_finalize']
        skip_confirmation = options['skip_confirmation']
        goc_missing_users = options['goc_missing_users']
        
        if dry_run:
            mode_desc = "DRY RUN mode - no data will be created"
            if goc_missing_users:
                mode_desc += " (would create missing users)"
            self.stdout.write(self.style.WARNING(mode_desc))
        else:
            mode_desc = "CREATE mode"
            if auto_finalize:
                mode_desc += " with auto-finalization"
            if skip_confirmation:
                mode_desc += " (skipping confirmation)"
            if goc_missing_users:
                mode_desc += " (created missing users)"
            
            self.stdout.write(
                self.style.SUCCESS(f"Running in {mode_desc}")
            )
        
        # Run the main process
        try:
            success = process_kacsa_schedule(
                dry_run=dry_run,
                auto_finalize=auto_finalize,
                skip_confirmation=skip_confirmation
            )
            
            if success:
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS("✅ Dry run completed successfully!")
                    )
                    self.stdout.write("To create the data, run: python manage.py create_kacsa_schedule --create")
                else:
                    self.stdout.write(
                        self.style.SUCCESS("✅ KaCsa schedule created successfully!")
                    )
            else:
                raise CommandError("Process failed - check output above for details")
                
        except KeyboardInterrupt:
            raise CommandError("Process interrupted by user")
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}")