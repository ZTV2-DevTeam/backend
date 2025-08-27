"""
Django Import-Export Resources for all models.
Comprehensive import/export functionality for the FTV system.
"""

from import_export import resources, fields, widgets
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, DateWidget, DateTimeWidget, TimeWidget, BooleanWidget
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from .models import (
    Profile, Tanev, Osztaly, Stab, RadioStab, Partner, PartnerTipus,
    Equipment, EquipmentTipus, ContactPerson, Forgatas, Absence,
    Tavollet, RadioSession, Beosztas, SzerepkorRelaciok, Szerepkor,
    Announcement, Config
)


# ============================================================================
# � CUSTOM WIDGETS
# ============================================================================

class OsztalyWidget(ForeignKeyWidget):
    """
    Custom widget for handling Osztaly imports.
    Supports multiple formats for specifying classes:
    - "startYear-szekcio" format (e.g., "2023-F", "2022-A")
    - Dynamic class names (e.g., "9F", "10A") - converted to startYear-szekcio
    """
    
    def clean(self, value, row=None, **kwargs):
        if not value:
            print(f"[DEBUG] OsztalyWidget: No value provided")
            return None
            
        value = str(value).strip()
        print(f"[DEBUG] OsztalyWidget: Processing value '{value}'")
        
        # Try direct format: "startYear-szekcio" (e.g., "2023-F")
        if '-' in value:
            try:
                start_year, szekcio = value.split('-', 1)
                osztaly = self.model.objects.get(
                    startYear=int(start_year),
                    szekcio=szekcio.upper()
                )
                print(f"[DEBUG] OsztalyWidget: Found osztaly by direct format: {osztaly}")
                return osztaly
            except (ValueError, self.model.DoesNotExist) as e:
                print(f"[DEBUG] OsztalyWidget: Direct format failed: {e}")
                pass
        
        # Try dynamic format: "9F", "10A", etc.
        # For F section: extract year number and calculate startYear
        if value.upper().endswith('F') and len(value) >= 2:
            try:
                year_number = int(value[:-1])
                print(f"[DEBUG] OsztalyWidget: F format - year_number: {year_number}")
                if 8 <= year_number <= 12:  # Valid F class years
                    from datetime import datetime
                    current_year = datetime.now().year
                    is_first_semester = datetime.now().month >= 9
                    
                    # Calculate startYear based on current year and class year
                    if is_first_semester:
                        start_year = current_year - (year_number - 8)
                    else:
                        start_year = current_year - (year_number - 8) - 1
                    
                    print(f"[DEBUG] OsztalyWidget: F format - calculated startYear: {start_year}")
                    osztaly = self.model.objects.get(
                        startYear=start_year,
                        szekcio='F'
                    )
                    print(f"[DEBUG] OsztalyWidget: Found osztaly by F format: {osztaly}")
                    return osztaly
            except (ValueError, self.model.DoesNotExist) as e:
                print(f"[DEBUG] OsztalyWidget: F format failed: {e}")
                pass
        
        # Try other sections: "21A", "22B", etc.
        if len(value) >= 3 and value[-1].upper() in ['A', 'B', 'C', 'D']:
            try:
                year_part = value[:-1]
                szekcio = value[-1].upper()
                
                # Handle 2-digit years (e.g., "21A" -> 2021)
                if len(year_part) == 2:
                    year_int = int(year_part)
                    if year_int <= 50:  # Assume 2000s
                        start_year = 2000 + year_int
                    else:  # Assume 1900s
                        start_year = 1900 + year_int
                else:
                    start_year = int(year_part)
                
                osztaly = self.model.objects.get(
                    startYear=start_year,
                    szekcio=szekcio
                )
                print(f"[DEBUG] OsztalyWidget: Found osztaly by section format: {osztaly}")
                return osztaly
            except (ValueError, self.model.DoesNotExist) as e:
                print(f"[DEBUG] OsztalyWidget: Section format failed: {e}")
                pass
        
        # If all else fails, raise an error
        print(f"[ERROR] OsztalyWidget: All format attempts failed for value '{value}'")
        raise ValueError(
            f"Invalid osztaly format: '{value}'. "
            f"Use formats like: '2023-F', '9F', '2021-A', '21A'"
        )
    
    def render(self, value, obj=None, **kwargs):
        """Export format: startYear-szekcio"""
        if value:
            return f"{value.startYear}-{value.szekcio}"
        return ""


# ============================================================================
# �👤 USER AND PROFILE RESOURCES
# ============================================================================

class UserResource(resources.ModelResource):
    """User import/export with comprehensive fields including password handling"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'password', 'is_active', 'is_staff', 'date_joined')
        export_order = ('id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'date_joined')
        
    def skip_row(self, instance, original, row, import_validation_errors=None):
        """Skip rows that are completely empty or have no meaningful data"""
        username = row.get('username')
        first_name = row.get('first_name', '')
        last_name = row.get('last_name', '')
        email = row.get('email', '')
        
        # Skip if username is empty or all key fields are empty
        if not username or not str(username).strip():
            return True
            
        # Skip if all key fields are empty
        if not any([str(field).strip() for field in [username, first_name, last_name, email] if field]):
            return True
            
        return super().skip_row(instance, original, row, import_validation_errors)
        
    def before_import_row(self, row, **kwargs):
        """Process password field before importing - hash it immediately"""
        username = row.get('username')
        
        # Skip empty rows - if no username provided, skip processing
        if not username or not str(username).strip():
            return
            
        # Hash the password immediately if provided
        password = row.get('password')
        if password and str(password).strip():
            # Hash the password using Django's make_password
            hashed_password = make_password(str(password).strip())
            row['password'] = hashed_password
            print(f"Password hashed for user: {username}")
        elif row.get('password') == '':
            # If password is empty string, generate random password
            random_password = get_random_string(8)
            hashed_password = make_password(random_password)
            row['password'] = hashed_password
            row['generated_password'] = random_password
            print(f"Random password generated and hashed for user: {username}")
    
    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        """No longer needed since password is hashed in before_import_row"""
        pass
    
    def import_obj(self, obj, data, dry_run, **kwargs):
        """Standard import - password is already hashed"""
        return super().import_obj(obj, data, dry_run, **kwargs)
            
    def dehydrate_password(self, user):
        """Don't export actual password hashes for security"""
        return "*** HIDDEN ***"


class ProfileResource(resources.ModelResource):
    """
    Profile import/export with user relationship and profile fields.
    Only username is needed to establish User foreign key connection.
    """
    
    # Username field to establish User foreign key connection
    username = fields.Field(
        column_name='username',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    
    # Profile fields only
    telefonszam = fields.Field(
        column_name='telefonszam',
        attribute='telefonszam'
    )
    medias = fields.Field(
        column_name='medias',
        attribute='medias',
        widget=BooleanWidget()
    )
    admin_type = fields.Field(
        column_name='admin_type',
        attribute='admin_type'
    )
    special_role = fields.Field(
        column_name='special_role',
        attribute='special_role'
    )
    stab_name = fields.Field(
        column_name='stab_name',
        attribute='stab',
        widget=ForeignKeyWidget(Stab, 'name')
    )
    radio_stab_team = fields.Field(
        column_name='radio_stab_team',
        attribute='radio_stab',
        widget=ForeignKeyWidget(RadioStab, 'team_code')
    )
    osztaly_display = fields.Field(
        column_name='osztaly_display',
        attribute='osztaly',
        widget=OsztalyWidget(Osztaly)
    )
    
    class Meta:
        model = Profile
        fields = (
            'username', 'telefonszam', 'medias', 'admin_type', 'special_role', 
            'stab_name', 'radio_stab_team', 'osztaly_display'
        )
        export_order = (
            'id', 'username', 'telefonszam', 'medias', 'admin_type', 'special_role', 
            'stab_name', 'radio_stab_team', 'osztaly_display'
        )
    
    def skip_row(self, instance, original, row, import_validation_errors=None):
        """Skip rows with empty username"""
        username = row.get('username')
        if not username or not str(username).strip():
            print(f"[DEBUG] Skipping row - username is empty")
            return True
        return super().skip_row(instance, original, row, import_validation_errors)
    
    def before_import_row(self, row, **kwargs):
        """Create or update User before creating Profile - User fields are already defined in User model"""
        username = row.get('username')
        if not username or not str(username).strip():
            return
        
        username = str(username).strip()
        row['username'] = username
        
        print(f"[DEBUG] Processing user: {username}")
        
        # Handle osztaly - try osztaly_display first, then osztaly_name
        osztaly_value = row.get('osztaly_display') or row.get('osztaly_name')
        if osztaly_value:
            # Set osztaly_display so the widget can process it
            row['osztaly_display'] = osztaly_value
            print(f"[DEBUG] Setting osztaly_display to: {osztaly_value}")
        
        # User model already has first_name, last_name, email, is_active fields
        # We just need to ensure the User exists with the username
        try:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'password': make_password(get_random_string(8)),  # Default password for new users
                }
            )
            
            print(f"[DEBUG] User {'created' if created else 'found'}: {username} (ID: {user.id})")
            
        except Exception as e:
            print(f"[ERROR] Failed to create/update user {username}: {e}")
            raise
    
    def get_instance(self, instance_loader, row):
        """Get existing Profile instance based on username"""
        username = row.get('username')
        if not username:
            return None
        
        username = str(username).strip()
        
        try:
            user = User.objects.get(username=username)
            try:
                profile = Profile.objects.get(user=user)
                print(f"[DEBUG] Found existing profile for {username}")
                return profile
            except Profile.DoesNotExist:
                print(f"[DEBUG] No existing profile for {username}")
                return None
        except User.DoesNotExist:
            print(f"[DEBUG] User {username} does not exist")
            return None
    
    def import_obj(self, obj, data, dry_run, **kwargs):
        """Import Profile object with User relationship based on username"""
        username = data.get('username')
        if not username or not str(username).strip():
            print(f"[ERROR] No username provided for Profile import")
            return None
        
        username = str(username).strip()
        print(f"[DEBUG] import_obj for username: {username}")
        
        # Get the user based on username
        try:
            user = User.objects.get(username=username)
            print(f"[DEBUG] Found user: {user.username} (ID: {user.id})")
        except User.DoesNotExist:
            print(f"[ERROR] User {username} not found during profile import")
            return None
        
        # Create or update Profile and ensure user is linked
        if obj is None:
            obj = Profile(user=user)
            print(f"[DEBUG] Creating new profile for {username}")
        else:
            obj.user = user  # Ensure user is linked
            print(f"[DEBUG] Updating existing profile for {username}")
        
        # Set Profile-specific fields only
        obj.telefonszam = data.get('telefonszam', '') or None
        obj.medias = self._convert_boolean(data.get('medias', True))
        obj.admin_type = data.get('admin_type', 'none') or 'none'
        obj.special_role = data.get('special_role', 'none') or 'none'
        
        print(f"[DEBUG] Profile import completed for {username}, user_id will be: {user.id}")
        return obj
    
    def _convert_boolean(self, value):
        """Convert various boolean representations to actual boolean"""
        if isinstance(value, str):
            value = value.strip().upper()
            return value in ['IGAZ', 'TRUE', '1', 'YES', 'Y']
        return bool(value)
    
    # Dehydrate methods for export
    def dehydrate_username(self, profile):
        return profile.user.username if profile.user else ''
    
    def dehydrate_stab_name(self, profile):
        return profile.stab.name if profile.stab else ''
    
    def dehydrate_radio_stab_team(self, profile):
        return profile.radio_stab.team_code if profile.radio_stab else ''
    
    def dehydrate_osztaly(self, profile):
        if profile.osztaly:
            return f"{profile.osztaly.startYear}-{profile.osztaly.szekcio}"
        return ""


# ============================================================================
# 🏫 EDUCATIONAL SYSTEM RESOURCES  
# ============================================================================

class TanevResource(resources.ModelResource):
    """School year import/export"""
    
    start_date = fields.Field(
        column_name='start_date',
        attribute='start_date',
        widget=DateWidget(format='%Y-%m-%d')
    )
    end_date = fields.Field(
        column_name='end_date',
        attribute='end_date',
        widget=DateWidget(format='%Y-%m-%d')
    )
    
    class Meta:
        model = Tanev
        fields = ('id', 'start_date', 'end_date')
        export_order = ('id', 'start_date', 'end_date')


class OsztalyResource(resources.ModelResource):
    """Class import/export with school year relationship"""
    
    tanev_display = fields.Field(
        column_name='tanev_display',
        attribute='tanev',
        readonly=True
    )
    
    class Meta:
        model = Osztaly
        fields = ('id', 'startYear', 'szekcio', 'tanev_display')
        export_order = ('id', 'startYear', 'szekcio', 'tanev_display')


class StabResource(resources.ModelResource):
    """Team import/export"""
    
    class Meta:
        model = Stab
        fields = ('id', 'name')
        export_order = ('id', 'name')


class RadioStabResource(resources.ModelResource):
    """Radio team import/export"""
    
    class Meta:
        model = RadioStab
        fields = ('id', 'name', 'team_code', 'description')
        export_order = ('id', 'name', 'team_code', 'description')


# ============================================================================
# 🤝 PARTNER RESOURCES
# ============================================================================

class PartnerTipusResource(resources.ModelResource):
    """Partner type import/export"""
    
    class Meta:
        model = PartnerTipus
        fields = ('id', 'name')
        export_order = ('id', 'name')


class PartnerResource(resources.ModelResource):
    """Partner import/export with institution relationship"""
    
    institution_name = fields.Field(
        column_name='institution_name',
        attribute='institution',
        widget=ForeignKeyWidget(PartnerTipus, 'name')
    )
    
    class Meta:
        model = Partner
        fields = ('id', 'name', 'address', 'institution_name', 'imgUrl')
        export_order = ('id', 'name', 'address', 'institution_name', 'imgUrl')


class ContactPersonResource(resources.ModelResource):
    """Contact person import/export"""
    
    class Meta:
        model = ContactPerson
        fields = ('id', 'name', 'email', 'phone', 'context')
        export_order = ('id', 'name', 'email', 'phone', 'context')


# ============================================================================
# 🎯 EQUIPMENT RESOURCES
# ============================================================================

class EquipmentTipusResource(resources.ModelResource):
    """Equipment type import/export"""
    
    class Meta:
        model = EquipmentTipus
        fields = ('id', 'name', 'emoji')
        export_order = ('id', 'name', 'emoji')


class EquipmentResource(resources.ModelResource):
    """Equipment import/export with type relationship"""
    
    equipment_type_name = fields.Field(
        column_name='equipment_type_name',
        attribute='equipmentType',
        widget=ForeignKeyWidget(EquipmentTipus, 'name')
    )
    
    class Meta:
        model = Equipment
        fields = (
            'id', 'nickname', 'brand', 'model', 'serialNumber',
            'equipment_type_name', 'functional', 'notes'
        )
        export_order = (
            'id', 'nickname', 'brand', 'model', 'serialNumber',
            'equipment_type_name', 'functional', 'notes'
        )


# ============================================================================
# 🎬 PRODUCTION RESOURCES
# ============================================================================

class ForgatásResource(resources.ModelResource):
    """Filming session import/export with all relationships"""
    
    date = fields.Field(
        column_name='date',
        attribute='date',
        widget=DateWidget(format='%Y-%m-%d')
    )
    timeFrom = fields.Field(
        column_name='timeFrom',
        attribute='timeFrom',
        widget=TimeWidget(format='%H:%M')
    )
    timeTo = fields.Field(
        column_name='timeTo',
        attribute='timeTo', 
        widget=TimeWidget(format='%H:%M')
    )
    location_name = fields.Field(
        column_name='location_name',
        attribute='location',
        widget=ForeignKeyWidget(Partner, 'name')
    )
    riporter_username = fields.Field(
        column_name='riporter_username',
        attribute='riporter',
        widget=ForeignKeyWidget(User, 'username')
    )
    contact_person_name = fields.Field(
        column_name='contact_person_name',
        attribute='contactPerson',
        widget=ForeignKeyWidget(ContactPerson, 'name')
    )
    tanev_display = fields.Field(
        column_name='tanev_display',
        attribute='tanev',
        readonly=True
    )
    equipment_names = fields.Field(
        column_name='equipment_names',
        attribute='equipments',
        widget=ManyToManyWidget(Equipment, field='nickname', separator='|')
    )
    
    class Meta:
        model = Forgatas
        fields = (
            'id', 'name', 'description', 'date', 'timeFrom', 'timeTo',
            'location_name', 'riporter_username', 'contact_person_name',
            'notes', 'forgTipus', 'tanev_display', 'equipment_names'
        )
        export_order = (
            'id', 'name', 'description', 'date', 'timeFrom', 'timeTo',
            'location_name', 'riporter_username', 'contact_person_name',
            'notes', 'forgTipus', 'tanev_display', 'equipment_names'
        )


# ============================================================================
# 📚 ABSENCE RESOURCES
# ============================================================================

class AbsenceResource(resources.ModelResource):
    """Absence import/export with relationships"""
    
    diak_username = fields.Field(
        column_name='diak_username',
        attribute='diak',
        widget=ForeignKeyWidget(User, 'username')
    )
    diak_full_name = fields.Field(
        column_name='diak_full_name',
        attribute='diak__first_name',
        readonly=True
    )
    forgatas_name = fields.Field(
        column_name='forgatas_name',
        attribute='forgatas',
        widget=ForeignKeyWidget(Forgatas, 'name')
    )
    date = fields.Field(
        column_name='date',
        attribute='date',
        widget=DateWidget(format='%Y-%m-%d')
    )
    timeFrom = fields.Field(
        column_name='timeFrom',
        attribute='timeFrom',
        widget=TimeWidget(format='%H:%M')
    )
    timeTo = fields.Field(
        column_name='timeTo',
        attribute='timeTo',
        widget=TimeWidget(format='%H:%M')
    )
    affected_classes_display = fields.Field(
        column_name='affected_classes',
        readonly=True
    )
    
    class Meta:
        model = Absence
        fields = (
            'id', 'diak_username', 'diak_full_name', 'forgatas_name',
            'date', 'timeFrom', 'timeTo', 'excused', 'unexcused',
            'auto_generated', 'affected_classes_display'
        )
        export_order = (
            'id', 'diak_username', 'diak_full_name', 'forgatas_name',
            'date', 'timeFrom', 'timeTo', 'excused', 'unexcused',
            'auto_generated', 'affected_classes_display'
        )
        
    def dehydrate_affected_classes_display(self, absence):
        """Export affected classes as readable format"""
        classes = absence.get_affected_classes()
        return ', '.join([f"{hour}. óra" for hour in classes]) if classes else 'Nincs'


class TavolletResource(resources.ModelResource):
    """Absence request import/export"""
    
    user_username = fields.Field(
        column_name='user_username',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    user_full_name = fields.Field(
        column_name='user_full_name',
        readonly=True
    )
    start_date = fields.Field(
        column_name='start_date',
        attribute='start_date',
        widget=DateTimeWidget(format='%Y-%m-%d %H:%M:%S')
    )
    end_date = fields.Field(
        column_name='end_date',
        attribute='end_date',
        widget=DateTimeWidget(format='%Y-%m-%d %H:%M:%S')
    )
    duration_days = fields.Field(
        column_name='duration_days',
        readonly=True
    )
    
    class Meta:
        model = Tavollet
        fields = (
            'id', 'user_username', 'user_full_name', 'start_date', 'end_date',
            'duration_days', 'reason', 'denied', 'approved'
        )
        export_order = (
            'id', 'user_username', 'user_full_name', 'start_date', 'end_date',
            'duration_days', 'reason', 'denied', 'approved'
        )
        
    def dehydrate_user_full_name(self, tavollet):
        """Export user full name"""
        return tavollet.user.get_full_name() or tavollet.user.username
        
    def dehydrate_duration_days(self, tavollet):
        """Export duration in days"""
        start_date = tavollet.start_date.date() if hasattr(tavollet.start_date, 'date') else tavollet.start_date
        end_date = tavollet.end_date.date() if hasattr(tavollet.end_date, 'date') else tavollet.end_date
        return (end_date - start_date).days + 1


# ============================================================================
# 📻 RADIO SYSTEM RESOURCES
# ============================================================================

class RadioSessionResource(resources.ModelResource):
    """Radio session import/export"""
    
    radio_stab_name = fields.Field(
        column_name='radio_stab_name',
        attribute='radio_stab',
        widget=ForeignKeyWidget(RadioStab, 'name')
    )
    date = fields.Field(
        column_name='date',
        attribute='date',
        widget=DateWidget(format='%Y-%m-%d')
    )
    time_from = fields.Field(
        column_name='time_from',
        attribute='time_from',
        widget=TimeWidget(format='%H:%M')
    )
    time_to = fields.Field(
        column_name='time_to',
        attribute='time_to',
        widget=TimeWidget(format='%H:%M')
    )
    participants_usernames = fields.Field(
        column_name='participants_usernames',
        attribute='participants',
        widget=ManyToManyWidget(User, field='username', separator='|')
    )
    tanev_display = fields.Field(
        column_name='tanev_display',
        attribute='tanev',
        readonly=True
    )
    
    class Meta:
        model = RadioSession
        fields = (
            'id', 'radio_stab_name', 'date', 'time_from', 'time_to',
            'description', 'participants_usernames', 'tanev_display'
        )
        export_order = (
            'id', 'radio_stab_name', 'date', 'time_from', 'time_to',
            'description', 'participants_usernames', 'tanev_display'
        )


# ============================================================================
# 🎭 ROLE SYSTEM RESOURCES
# ============================================================================

class SzerepkorResource(resources.ModelResource):
    """Role import/export"""
    
    class Meta:
        model = Szerepkor
        fields = ('id', 'name', 'ev')
        export_order = ('id', 'name', 'ev')


class SzerepkorRelaciokResource(resources.ModelResource):
    """Role assignment import/export"""
    
    user_username = fields.Field(
        column_name='user_username',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    user_full_name = fields.Field(
        column_name='user_full_name',
        readonly=True
    )
    szerepkor_name = fields.Field(
        column_name='szerepkor_name',
        attribute='szerepkor',
        widget=ForeignKeyWidget(Szerepkor, 'name')
    )
    
    class Meta:
        model = SzerepkorRelaciok
        fields = ('id', 'user_username', 'user_full_name', 'szerepkor_name')
        export_order = ('id', 'user_username', 'user_full_name', 'szerepkor_name')
        
    def dehydrate_user_full_name(self, relation):
        """Export user full name"""
        return relation.user.get_full_name() or relation.user.username


class BeosztasResource(resources.ModelResource):
    """Assignment import/export"""
    
    author_username = fields.Field(
        column_name='author_username',
        attribute='author',
        widget=ForeignKeyWidget(User, 'username')
    )
    tanev_display = fields.Field(
        column_name='tanev_display',
        attribute='tanev',
        readonly=True
    )
    forgatas_name = fields.Field(
        column_name='forgatas_name',
        attribute='forgatas',
        widget=ForeignKeyWidget(Forgatas, 'name')
    )
    stab_name = fields.Field(
        column_name='stab_name',
        attribute='stab',
        widget=ForeignKeyWidget(Stab, 'name')
    )
    szerepkor_relaciok_ids = fields.Field(
        column_name='szerepkor_relaciok_ids',
        attribute='szerepkor_relaciok',
        widget=ManyToManyWidget(SzerepkorRelaciok, field='id', separator='|')
    )
    
    class Meta:
        model = Beosztas
        fields = (
            'id', 'kesz', 'author_username', 'tanev_display',
            'forgatas_name', 'stab_name', 'szerepkor_relaciok_ids', 'created_at'
        )
        export_order = (
            'id', 'kesz', 'author_username', 'tanev_display',
            'forgatas_name', 'stab_name', 'szerepkor_relaciok_ids', 'created_at'
        )


# ============================================================================
# 📢 COMMUNICATION RESOURCES
# ============================================================================

class AnnouncementResource(resources.ModelResource):
    """Announcement import/export"""
    
    author_username = fields.Field(
        column_name='author_username',
        attribute='author',
        widget=ForeignKeyWidget(User, 'username')
    )
    author_full_name = fields.Field(
        column_name='author_full_name',
        readonly=True
    )
    cimzettek_usernames = fields.Field(
        column_name='cimzettek_usernames',
        attribute='cimzettek',
        widget=ManyToManyWidget(User, field='username', separator='|')
    )
    
    class Meta:
        model = Announcement
        fields = (
            'id', 'title', 'body', 'author_username', 'author_full_name',
            'cimzettek_usernames', 'created_at', 'updated_at'
        )
        export_order = (
            'id', 'title', 'body', 'author_username', 'author_full_name',
            'cimzettek_usernames', 'created_at', 'updated_at'
        )
        
    def dehydrate_author_full_name(self, announcement):
        """Export author full name"""
        if announcement.author:
            return announcement.author.get_full_name() or announcement.author.username
        return ''


# ============================================================================
# ⚙️ SYSTEM CONFIGURATION RESOURCES
# ============================================================================

class ConfigResource(resources.ModelResource):
    """System configuration import/export"""
    
    class Meta:
        model = Config
        fields = ('id', 'active', 'allowEmails')
        export_order = ('id', 'active', 'allowEmails')
