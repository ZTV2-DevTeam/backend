"""
Django Import-Export Resources for all models.
Comprehensive import/export functionality for the FTV system.
"""

from import_export import resources, fields, widgets
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, DateWidget, TimeWidget, BooleanWidget
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
            return None
            
        value = str(value).strip()
        
        # Try direct format: "startYear-szekcio" (e.g., "2023-F")
        if '-' in value:
            try:
                start_year, szekcio = value.split('-', 1)
                return self.model.objects.get(
                    startYear=int(start_year),
                    szekcio=szekcio.upper()
                )
            except (ValueError, self.model.DoesNotExist):
                pass
        
        # Try dynamic format: "9F", "10A", etc.
        # For F section: extract year number and calculate startYear
        if value.upper().endswith('F') and len(value) >= 2:
            try:
                year_number = int(value[:-1])
                if 8 <= year_number <= 12:  # Valid F class years
                    from datetime import datetime
                    current_year = datetime.now().year
                    is_first_semester = datetime.now().month >= 9
                    
                    # Calculate startYear based on current year and class year
                    if is_first_semester:
                        start_year = current_year - (year_number - 8)
                    else:
                        start_year = current_year - (year_number - 8) - 1
                    
                    return self.model.objects.get(
                        startYear=start_year,
                        szekcio='F'
                    )
            except (ValueError, self.model.DoesNotExist):
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
                
                return self.model.objects.get(
                    startYear=start_year,
                    szekcio=szekcio
                )
            except (ValueError, self.model.DoesNotExist):
                pass
        
        # If all else fails, raise an error
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
    
    # Custom field for password that won't be directly assigned
    password = fields.Field(column_name='password', attribute=None, readonly=False)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'date_joined')
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
        
    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        """Set password after the instance is created"""
        if instance and not kwargs.get('dry_run', False):
            # Get the password from the current row being processed
            if hasattr(self, '_current_row_data'):
                password = self._current_row_data.get('password')
                if password and str(password).strip():
                    # Use set_password to properly hash the password
                    instance.set_password(str(password).strip())
                    instance.save()
                    print(f"Password set for user: {instance.username}")
                elif new:  # Only set random password for new users
                    random_password = get_random_string(8)
                    instance.set_password(random_password)
                    instance.save()
                    print(f"Random password set for new user: {instance.username}")
    
    def import_obj(self, obj, data, dry_run, **kwargs):
        """Store row data for password processing and prevent password from being set directly"""
        # Store the current row data for use in after_import_instance
        self._current_row_data = data.copy()
        
        # Remove password from data so it's not set directly on the model
        if 'password' in data:
            data_copy = data.copy()
            del data_copy['password']
        else:
            data_copy = data
        
        # Call the default import without password
        return super().import_obj(obj, data_copy, dry_run, **kwargs)
            
    def dehydrate_password(self, user):
        """Don't export actual password hashes for security"""
        return "*** HIDDEN ***"


class ProfileResource(resources.ModelResource):
    """Profile import/export with user relationship and related objects"""
    
    # User fields
    username = fields.Field(
        column_name='username',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    user_first_name = fields.Field(
        column_name='user_first_name',
        attribute='user__first_name',
        readonly=True
    )
    user_last_name = fields.Field(
        column_name='user_last_name', 
        attribute='user__last_name',
        readonly=True
    )
    user_email = fields.Field(
        column_name='user_email',
        attribute='user__email',
        readonly=True
    )
    
    # Related objects by name
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
        readonly=True
    )
    
    # Import/Export field for osztaly using the string representation
    osztaly_name = fields.Field(
        column_name='osztaly_name',
        attribute='osztaly',
        widget=OsztalyWidget(Osztaly)
    )
    
    class Meta:
        model = Profile
        fields = (
            'id', 'username', 'user_first_name', 'user_last_name', 'user_email',
            'telefonszam', 'medias', 'admin_type', 'special_role',
            'stab_name', 'radio_stab_team', 'osztaly_display', 'osztaly_name'
        )
        export_order = (
            'id', 'username', 'user_first_name', 'user_last_name', 'user_email',
            'telefonszam', 'medias', 'admin_type', 'special_role',
            'stab_name', 'radio_stab_team', 'osztaly_display', 'osztaly_name'
        )


class UserProfileCombinedResource(resources.ModelResource):
    """
    Combined User + Profile resource for importing both from a single file.
    This allows creating users and their profiles from one CSV/Excel file.
    Includes password handling functionality.
    """
    
    # User fields - these will be handled in the import logic, not as model fields
    username = fields.Field(column_name='username', readonly=True)
    first_name = fields.Field(column_name='first_name', readonly=True)
    last_name = fields.Field(column_name='last_name', readonly=True)
    email = fields.Field(column_name='email', readonly=True)
    password = fields.Field(column_name='password', readonly=True)
    is_active = fields.Field(column_name='is_active', widget=BooleanWidget(), readonly=True)
    
    # Profile fields
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
    osztaly_name = fields.Field(
        column_name='osztaly_name',
        attribute='osztaly',
        widget=OsztalyWidget(Osztaly)
    )
    
    class Meta:
        model = Profile
        fields = (
            'username', 'first_name', 'last_name', 'email', 'password', 'is_active',
            'telefonszam', 'medias', 'admin_type', 'special_role',
            'stab_name', 'radio_stab_team', 'osztaly_name'
        )
        # Note: User fields (username, first_name, etc.) are handled in import_obj method
    
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
        """Create or update user before creating/updating profile"""
        username = row.get('username')
        
        # Skip empty rows - if no username provided, skip processing
        if not username or not str(username).strip():
            return
            
        # Also check if other required fields are empty
        first_name = row.get('first_name', '')
        last_name = row.get('last_name', '')
        email = row.get('email', '')
        
        # Skip if all key fields are empty
        if not any([str(field).strip() for field in [username, first_name, last_name, email] if field]):
            return
            
        password = row.get('password')
        
        # Handle password processing
        if password:
            hashed_password = make_password(password)
        else:
            # Generate random password if none provided
            random_password = get_random_string(8)
            hashed_password = make_password(random_password)
            row['generated_password'] = random_password  # Store for logging/reference
        
        # Generate unique username if this one already exists
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        
        # Update the row with the unique username
        if username != base_username:
            row['username'] = username
        
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': row.get('first_name', ''),
                'last_name': row.get('last_name', ''),
                'email': row.get('email', ''),
                'password': hashed_password,
                'is_active': row.get('is_active', True) if row.get('is_active') else True
            }
        )
        if not created:
            # Update existing user
            user.first_name = row.get('first_name', user.first_name)
            user.last_name = row.get('last_name', user.last_name)
            user.email = row.get('email', user.email)
            if password:  # Only update password if provided
                user.password = hashed_password
            if row.get('is_active') is not None:
                user.is_active = row.get('is_active')
            user.save()
    
    def import_obj(self, obj, data, dry_run, **kwargs):
        """Custom import logic to handle user-profile relationship"""
        username = data.get('username')
        
        # Skip empty rows - if no username provided, skip processing
        if not username or not str(username).strip():
            return None
            
        # Also check if other required fields are empty
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        email = data.get('email', '')
        
        # Skip if all key fields are empty
        if not any([str(field).strip() for field in [username, first_name, last_name, email] if field]):
            return None
            
        try:
            user = User.objects.get(username=username)
            # Get or create profile for this user
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Update profile fields
            for field_name in ['telefonszam', 'medias', 'admin_type', 'special_role']:
                if field_name in data and data[field_name] is not None:
                    setattr(profile, field_name, data[field_name])
            
            # Handle foreign key relationships
            if data.get('stab_name'):
                try:
                    stab = Stab.objects.get(name=data['stab_name'])
                    profile.stab = stab
                except Stab.DoesNotExist:
                    pass
            
            if data.get('radio_stab_team'):
                try:
                    radio_stab = RadioStab.objects.get(team_code=data['radio_stab_team'])
                    profile.radio_stab = radio_stab
                except RadioStab.DoesNotExist:
                    pass
            
            if data.get('osztaly_name'):
                try:
                    widget = OsztalyWidget(Osztaly)
                    osztaly = widget.clean(data['osztaly_name'])
                    profile.osztaly = osztaly
                except (ValueError, Osztaly.DoesNotExist):
                    pass
            
            if not dry_run:
                profile.save()
            
            return profile
                
        except User.DoesNotExist:
            pass
        
        return super().import_obj(obj, data, dry_run, **kwargs)


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
        widget=DateWidget(format='%Y-%m-%d')
    )
    end_date = fields.Field(
        column_name='end_date',
        attribute='end_date',
        widget=DateWidget(format='%Y-%m-%d')
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
        return (tavollet.end_date - tavollet.start_date).days + 1


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
    szerepkor_relaciok_ids = fields.Field(
        column_name='szerepkor_relaciok_ids',
        attribute='szerepkor_relaciok',
        widget=ManyToManyWidget(SzerepkorRelaciok, field='id', separator='|')
    )
    
    class Meta:
        model = Beosztas
        fields = (
            'id', 'kesz', 'author_username', 'tanev_display',
            'forgatas_name', 'szerepkor_relaciok_ids', 'created_at'
        )
        export_order = (
            'id', 'kesz', 'author_username', 'tanev_display',
            'forgatas_name', 'szerepkor_relaciok_ids', 'created_at'
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
