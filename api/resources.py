"""
Django Import-Export Resources for all models.
Comprehensive import/export functionality for the FTV system.
"""

from import_export import resources, fields, widgets
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, DateWidget, TimeWidget, BooleanWidget
from django.contrib.auth.models import User
from .models import (
    Profile, Tanev, Osztaly, Stab, RadioStab, Partner, PartnerTipus,
    Equipment, EquipmentTipus, ContactPerson, Forgatas, Absence,
    Tavollet, RadioSession, Beosztas, SzerepkorRelaciok, Szerepkor,
    Announcement, Config
)


# ============================================================================
# 👤 USER AND PROFILE RESOURCES
# ============================================================================

class UserResource(resources.ModelResource):
    """User import/export with comprehensive fields"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'date_joined')
        export_order = ('id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'date_joined')


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
    
    class Meta:
        model = Profile
        fields = (
            'id', 'username', 'user_first_name', 'user_last_name', 'user_email',
            'telefonszam', 'medias', 'admin_type', 'special_role',
            'stab_name', 'radio_stab_team', 'osztaly_display'
        )
        export_order = (
            'id', 'username', 'user_first_name', 'user_last_name', 'user_email',
            'telefonszam', 'medias', 'admin_type', 'special_role',
            'stab_name', 'radio_stab_team', 'osztaly_display'
        )


class UserProfileCombinedResource(resources.ModelResource):
    """
    Combined User + Profile resource for importing both from a single file.
    This allows creating users and their profiles from one CSV/Excel file.
    """
    
    # User fields
    username = fields.Field(
        column_name='username',
        attribute='user__username'
    )
    first_name = fields.Field(
        column_name='first_name',
        attribute='user__first_name'
    )
    last_name = fields.Field(
        column_name='last_name',
        attribute='user__last_name'
    )
    email = fields.Field(
        column_name='email',
        attribute='user__email'
    )
    is_active = fields.Field(
        column_name='is_active',
        attribute='user__is_active',
        widget=BooleanWidget()
    )
    
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
    
    class Meta:
        model = Profile
        fields = (
            'username', 'first_name', 'last_name', 'email', 'is_active',
            'telefonszam', 'medias', 'admin_type', 'special_role',
            'stab_name', 'radio_stab_team'
        )
        
    def before_import_row(self, row, **kwargs):
        """Create or update user before creating/updating profile"""
        username = row.get('username')
        if username:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': row.get('first_name', ''),
                    'last_name': row.get('last_name', ''),
                    'email': row.get('email', ''),
                    'is_active': row.get('is_active', True)
                }
            )
            if not created:
                # Update existing user
                user.first_name = row.get('first_name', user.first_name)
                user.last_name = row.get('last_name', user.last_name)
                user.email = row.get('email', user.email)
                user.is_active = row.get('is_active', user.is_active)
                user.save()


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
