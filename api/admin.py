from django.contrib import admin
from django.contrib.auth.models import User
from .models import *

# Register your models here.

@admin.register(Tanev)
class TanevAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'start_date', 'end_date']
    list_filter = ['start_date', 'end_date']
    search_fields = ['start_date', 'end_date']
    filter_horizontal = ['osztalyok']
    readonly_fields = ['start_year', 'end_year']
    fieldsets = (
        ('Alapadatok', {
            'fields': ('start_date', 'end_date')
        }),
        ('Kapcsolatok', {
            'fields': ('osztalyok',)
        }),
        ('Csak olvasható', {
            'fields': ('start_year', 'end_year'),
            'classes': ('collapse',)
        })
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user_full_name', 'telefonszam', 'medias', 'osztaly', 'stab', 'radio_stab', 'admin_type', 'special_role', 'password_set']
    list_filter = ['medias', 'osztaly', 'stab', 'radio_stab', 'admin_type', 'special_role', 'password_set']
    search_fields = ['user__first_name', 'user__last_name', 'user__username', 'telefonszam']
    autocomplete_fields = ['user', 'osztaly', 'stab', 'radio_stab']
    readonly_fields = ['is_admin', 'is_developer_admin', 'is_teacher_admin', 'is_system_admin', 'is_production_leader']
    
    fieldsets = (
        ('Felhasználó', {
            'fields': ('user', 'telefonszam', 'medias', 'password_set')
        }),
        ('Oktatási kapcsolatok', {
            'fields': ('osztaly', 'stab', 'radio_stab')
        }),
        ('Jogosultságok', {
            'fields': ('admin_type', 'special_role', 'osztalyfonok')
        }),
        ('Első bejelentkezés', {
            'fields': ('first_login_token', 'first_login_sent_at'),
            'classes': ('collapse',)
        }),
        ('Számított mezők', {
            'fields': ('is_admin', 'is_developer_admin', 'is_teacher_admin', 'is_system_admin', 'is_production_leader'),
            'classes': ('collapse',)
        })
    )
    
    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Teljes név'

@admin.register(Osztaly)
class OsztalyAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'startYear', 'szekcio', 'tanev']
    list_filter = ['szekcio', 'startYear', 'tanev']
    search_fields = ['szekcio']
    autocomplete_fields = ['tanev']

@admin.register(Stab)
class StabAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(RadioStab)
class RadioStabAdmin(admin.ModelAdmin):
    list_display = ['name', 'team_code', 'member_count']
    list_filter = ['team_code']
    search_fields = ['name', 'team_code', 'description']
    
    def member_count(self, obj):
        return obj.get_members().count()
    member_count.short_description = 'Tagok száma'

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution', 'address']
    list_filter = ['institution']
    search_fields = ['name', 'address']
    autocomplete_fields = ['institution']

@admin.register(PartnerTipus)
class PartnerTipusAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ['active', 'allowEmails']
    list_filter = ['active', 'allowEmails']

@admin.register(Forgatas)
class ForgatásAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'timeFrom', 'timeTo', 'forgTipus', 'location', 'tanev']
    list_filter = ['forgTipus', 'date', 'tanev', 'location']
    search_fields = ['name', 'description', 'notes']
    autocomplete_fields = ['location', 'contactPerson', 'relatedKaCsa', 'tanev']
    filter_horizontal = ['equipments']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Alapadatok', {
            'fields': ('name', 'description', 'forgTipus', 'tanev')
        }),
        ('Időpont', {
            'fields': ('date', 'timeFrom', 'timeTo')
        }),
        ('Helyszín és kapcsolatok', {
            'fields': ('location', 'contactPerson')
        }),
        ('Kapcsolódó forgatás', {
            'fields': ('relatedKaCsa',),
            'classes': ('collapse',)
        }),
        ('Eszközök', {
            'fields': ('equipments',)
        }),
        ('Megjegyzések', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )

@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ['diak', 'forgatas', 'date', 'timeFrom', 'timeTo', 'excused', 'unexcused']
    list_filter = ['excused', 'unexcused', 'date', 'forgatas']
    search_fields = ['diak__first_name', 'diak__last_name', 'forgatas__name']
    autocomplete_fields = ['diak', 'forgatas']
    date_hierarchy = 'date'
    
    readonly_fields = ['get_affected_classes_display']
    
    def get_affected_classes_display(self, obj):
        return ', '.join([f"{hour}. óra" for hour in obj.get_affected_classes()])
    get_affected_classes_display.short_description = 'Érintett órák'

@admin.register(EquipmentTipus)
class EquipmentTipusAdmin(admin.ModelAdmin):
    list_display = ['name', 'emoji']
    search_fields = ['name']

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['nickname', 'brand', 'model', 'equipmentType', 'functional']
    list_filter = ['equipmentType', 'functional', 'brand']
    search_fields = ['nickname', 'brand', 'model', 'serialNumber']
    autocomplete_fields = ['equipmentType']
    
    fieldsets = (
        ('Alapadatok', {
            'fields': ('nickname', 'equipmentType', 'functional')
        }),
        ('Részletek', {
            'fields': ('brand', 'model', 'serialNumber')
        }),
        ('Megjegyzések', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )

@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone']
    search_fields = ['name', 'email', 'phone']

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'updated_at', 'recipient_count']
    list_filter = ['created_at', 'updated_at', 'author']
    search_fields = ['title', 'body']
    autocomplete_fields = ['author']
    filter_horizontal = ['cimzettek']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    def recipient_count(self, obj):
        return obj.cimzettek.count()
    recipient_count.short_description = 'Címzettek száma'

@admin.register(Tavollet)
class TavolletAdmin(admin.ModelAdmin):
    list_display = ['user', 'start_date', 'end_date', 'denied']
    list_filter = ['denied', 'start_date', 'end_date']
    search_fields = ['user__first_name', 'user__last_name', 'reason']
    autocomplete_fields = ['user']
    date_hierarchy = 'start_date'

@admin.register(RadioSession)
class RadioSessionAdmin(admin.ModelAdmin):
    list_display = ['radio_stab', 'date', 'time_from', 'time_to', 'participant_count', 'tanev']
    list_filter = ['radio_stab', 'date', 'tanev']
    search_fields = ['radio_stab__name', 'description']
    autocomplete_fields = ['radio_stab', 'tanev']
    filter_horizontal = ['participants']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Résztvevők száma'

@admin.register(Beosztas)
class BeosztasAdmin(admin.ModelAdmin):
    list_display = ['id', 'kesz', 'author', 'tanev', 'created_at', 'szerepkor_count']
    list_filter = ['kesz', 'tanev', 'created_at', 'author']
    search_fields = ['author__first_name', 'author__last_name']
    autocomplete_fields = ['author', 'tanev']
    filter_horizontal = ['szerepkor_relaciok']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    def szerepkor_count(self, obj):
        return obj.szerepkor_relaciok.count()
    szerepkor_count.short_description = 'Szerepkörök száma'

@admin.register(Szerepkor)
class SzerepkorAdmin(admin.ModelAdmin):
    list_display = ['name', 'ev']
    list_filter = ['ev']
    search_fields = ['name']

@admin.register(SzerepkorRelaciok)
class SzerepkorRelaciokAdmin(admin.ModelAdmin):
    list_display = ['user', 'szerepkor']
    list_filter = ['szerepkor']
    search_fields = ['user__first_name', 'user__last_name', 'szerepkor__name']
    autocomplete_fields = ['user', 'szerepkor']