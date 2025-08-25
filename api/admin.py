from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django import forms
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from .models import *
from .resources import *

# ============================================================================
# � USER MANAGEMENT WITH IMPORT/EXPORT
# ============================================================================

class CustomUserChangeForm(UserChangeForm):
    """Custom user change form with proper password handling"""
    password = forms.CharField(
        label="Jelszó",
        widget=forms.PasswordInput(attrs={'placeholder': 'Új jelszó (hagyja üresen, ha nem változtatja)'}),
        required=False,
        help_text="Írjon be egy új jelszót, ha meg szeretné változtatni. Hagyja üresen, ha nem szeretné módosítani."
    )
    
    class Meta:
        model = User
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the default password field help text and widget
        if 'password' in self.fields:
            self.fields['password'].help_text = "Írjon be egy új jelszót, ha meg szeretné változtatni."
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            # Only validate if a new password is provided
            try:
                validate_password(password, self.instance)
            except ValidationError as e:
                raise ValidationError(' '.join(e.messages))
        return password
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        if password:
            # Check if the password is already hashed
            if not password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$')):
                # Only hash unhashed passwords
                user.set_password(password)
            else:
                # If it's already hashed (shouldn't happen with our form), use as is
                user.password = password
        
        if commit:
            user.save()
        return user

class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with proper password handling"""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user

# Unregister the default User admin and add our own with import/export
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    resource_class = UserResource
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ['username', 'last_name', 'first_name', 'email', 'password_status', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    readonly_fields = ['date_joined', 'last_login', 'password_info']
    
    fieldsets = (
        ('👤 Felhasználó adatok', {
            'fields': ('username', 'password', 'password_info')
        }),
        ('📝 Személyes adatok', {
            'fields': ('last_name', 'first_name', 'email')
        }),
        ('🔐 Jogosultságok', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('📊 Fontos dátumok', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        })
    )
    
    add_fieldsets = (
        ('👤 Új felhasználó', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'last_name', 'first_name', 'password1', 'password2'),
        }),
        ('🔐 Jogosultságok', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups'),
        }),
    )
    
    def password_status(self, obj):
        """Show password status in list view (dark mode support)"""
        if obj.has_usable_password():
            return format_html(
                '<span style="color: #4caf50; font-weight: bold; background: #222; padding: 2px 6px; border-radius: 3px;">✅ Beállítva</span>'
            )
        else:
            return format_html(
                '<span style="color: #f44336; font-weight: bold; background: #222; padding: 2px 6px; border-radius: 3px;">❌ Nincs jelszó</span>'
            )
    password_status.short_description = 'Jelszó státusz'

    def password_info(self, obj):
        """Show password information in detail view (dark mode support)"""
        if obj.has_usable_password():
            if obj.password:
                algorithm = obj.password.split('$')[0] if '$' in obj.password else 'unknown'
                return format_html(
                    '<div style="background: #222; color: #eee; padding: 10px; border-radius: 5px;">'
                    '<strong style="color: #4caf50;">✅ Jelszó beállítva</strong><br>'
                    '<small>Algoritmus: {}<br>'
                    'Hash: {}...</small>'
                    '</div>',
                    algorithm, obj.password[:20]
                )
            return format_html(
                '<span style="color: #4caf50; background: #222; padding: 2px 6px; border-radius: 3px;">✅ Jelszó beállítva</span>'
            )
        else:
            return format_html(
                '<div style="background: #330000; color: #ffcccc; padding: 10px; border-radius: 5px;">'
                '<strong>❌ Nincs használható jelszó</strong><br>'
                '<small>A felhasználó nem tud bejelentkezni</small>'
                '</div>'
            )
    password_info.short_description = 'Jelszó információ'

    def save_model(self, request, obj, form, change):
        """Override save to ensure proper password handling"""
        if change:  # Editing existing user
            password = form.cleaned_data.get('password')
            if password:
                # Check if password is already hashed
                if not password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$')):
                    # Hash the unhashed password
                    obj.set_password(password)
                # If already hashed, it was set in the form's save method
        
        super().save_model(request, obj, form, change)


# ============================================================================
# �📚 OKTATÁSI RENDSZER (CORE ACADEMIC MODELS)
# ============================================================================

@admin.register(Tanev)
class TanevAdmin(ImportExportModelAdmin):
    resource_class = TanevResource
    list_display = ['display_tanev', 'start_date', 'end_date', 'is_active', 'osztaly_count']
    list_filter = ['start_date', 'end_date']
    search_fields = ['start_date', 'end_date']
    filter_horizontal = ['osztalyok']
    readonly_fields = ['start_year', 'end_year']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('📅 Tanév időszaka', {
            'fields': ('start_date', 'end_date'),
            'description': 'A tanév kezdő és befejező dátuma'
        }),
        ('🏫 Osztályok', {
            'fields': ('osztalyok',),
            'description': 'A tanévhez tartozó osztályok'
        }),
        ('📊 Számított adatok', {
            'fields': ('start_year', 'end_year'),
            'classes': ('collapse',),
            'description': 'Automatikusan számított mezők'
        })
    )
    
    def display_tanev(self, obj):
        if obj.get_active() == obj:
            return format_html('<strong style="color: green;">🎯 {} (Aktív)</strong>', str(obj))
        return str(obj)
    display_tanev.short_description = 'Tanév'
    
    def is_active(self, obj):
        return obj.get_active() == obj
    is_active.short_description = 'Aktív'
    is_active.boolean = True
    
    def osztaly_count(self, obj):
        return obj.osztalyok.count()
    osztaly_count.short_description = 'Osztályok száma'

@admin.register(Osztaly)
class OsztalyAdmin(ImportExportModelAdmin):
    resource_class = OsztalyResource
    list_display = ['display_osztaly', 'startYear', 'szekcio', 'tanev', 'student_count', 'fonok_count']
    list_filter = ['szekcio', 'startYear', 'tanev']
    search_fields = ['szekcio', 'startYear']
    autocomplete_fields = ['tanev']
    filter_horizontal = ['osztaly_fonokei']
    
    fieldsets = (
        ('🏫 Osztály adatok', {
            'fields': ('startYear', 'szekcio', 'tanev'),
            'description': 'Az osztály alapvető azonosítói'
        }),
        ('👨‍🏫 Osztályfőnökök', {
            'fields': ('osztaly_fonokei',),
            'description': 'Az osztály fő- és helyettes osztályfőnökei'
        })
    )
    
    def display_osztaly(self, obj):
        return format_html('<strong style="color: #0066cc;">{}</strong>', str(obj))
    display_osztaly.short_description = 'Osztály'
    
    def student_count(self, obj):
        count = Profile.objects.filter(osztaly=obj).count()
        return format_html('<span style="color: blue;">{} fő</span>', count)
    student_count.short_description = 'Diákok száma'
    
    def fonok_count(self, obj):
        return obj.osztaly_fonokei.count()
    fonok_count.short_description = 'Osztályfőnökök'

@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin):
    resource_classes = [ProfileResource]  # Use only ProfileResource which handles both osztaly_name and osztaly_display
    list_display = ['user_full_name', 'user_status', 'telefonszam', 'medias', 'display_osztaly', 'display_stab', 'admin_level', 'special_role_display']
    list_filter = [
        'medias', 'osztaly', 'stab', 'radio_stab', 'admin_type', 
        'special_role'
    ]
    search_fields = ['user__first_name', 'user__last_name', 'user__username', 'telefonszam']
    autocomplete_fields = ['user', 'osztaly', 'stab', 'radio_stab']
    readonly_fields = [
        'is_admin', 'is_developer_admin', 'is_teacher_admin', 
        'is_system_admin', 'is_production_leader', 'display_permissions'
    ]
    
    fieldsets = (
        ('👤 Felhasználó adatok', {
            'fields': ('user', 'telefonszam', 'medias'),
            'description': 'Alapvető felhasználói információk'
        }),
        ('🎓 Oktatási kapcsolatok', {
            'fields': ('osztaly', 'stab', 'radio_stab'),
            'description': 'Osztály és stáb besorolások'
        }),
        ('⚡ Jogosultságok és szerepek', {
            'fields': ('admin_type', 'special_role'),
            'description': 'Adminisztrátor jogosultságok és különleges szerepek'
        }),
        ('📊 Számított jogosultságok', {
            'fields': ('is_admin', 'is_developer_admin', 'is_teacher_admin', 'is_system_admin', 'is_production_leader', 'display_permissions'),
            'classes': ('collapse',),
            'description': 'Automatikusan számított jogosultságok'
        })
    )
    
    def user_full_name(self, obj):
        return format_html('<strong>{}</strong>', obj.user.get_full_name() or obj.user.username)
    user_full_name.short_description = 'Teljes név'
    
    def user_status(self, obj):
        if not obj.user.has_usable_password():
            return format_html('<span style="color: orange;">⚠️ Jelszó nincs beállítva</span>')
        elif obj.is_admin:
            return format_html('<span style="color: red;">👑 Admin</span>')
        elif obj.is_osztaly_fonok:
            return format_html('<span style="color: blue;">👨‍🏫 Osztályfőnök</span>')
        return format_html('<span style="color: green;">✓ Aktív</span>')
    user_status.short_description = 'Státusz'
    
    def display_osztaly(self, obj):
        if obj.osztaly:
            return format_html('<span style="color: #0066cc;">{}</span>', str(obj.osztaly))
        return '-'
    display_osztaly.short_description = 'Osztály'
    
    def display_stab(self, obj):
        parts = []
        if obj.stab:
            parts.append(f'📹 {obj.stab.name}')
        if obj.radio_stab:
            parts.append(f'📻 {obj.radio_stab.name}')
        return ' | '.join(parts) if parts else '-'
    display_stab.short_description = 'Stábok'
    
    def admin_level(self, obj):
        if obj.admin_type != 'none':
            colors = {
                'developer': 'red',
                'teacher': 'blue', 
                'system_admin': 'purple'
            }
            color = colors.get(obj.admin_type, 'gray')
            return format_html('<span style="color: {};">● {}</span>', color, obj.get_admin_type_display())
        return '-'
    admin_level.short_description = 'Admin szint'
    
    def special_role_display(self, obj):
        if obj.special_role != 'none':
            return format_html('<span style="color: orange;">⭐ {}</span>', obj.get_special_role_display())
        return '-'
    special_role_display.short_description = 'Különleges szerep'
    
    def display_permissions(self, obj):
        perms = []
        if obj.is_admin:
            perms.append('🔑 Adminisztrátor')
        if obj.is_osztaly_fonok:
            perms.append('👨‍🏫 Osztályfőnök')
        if obj.is_production_leader:
            perms.append('🎬 Gyártásvezető')
        return format_html('<br>'.join(perms)) if perms else 'Nincs különleges jogosultság'
    display_permissions.short_description = 'Összes jogosultság'

# ============================================================================
# 🎬 GYÁRTÁS ÉS FORGATÁS (PRODUCTION MODELS)  
# ============================================================================

@admin.register(Forgatas)
class ForgatásAdmin(ImportExportModelAdmin):
    resource_class = ForgatásResource
    list_display = ['name_with_icon', 'date', 'time_display', 'forgTipus_display', 'location_display', 'equipment_count', 'riporter_display', 'tanev']
    list_filter = ['forgTipus', 'date', 'tanev', 'location', 'riporter']
    search_fields = ['name', 'description', 'notes', 'riporter__first_name', 'riporter__last_name']
    autocomplete_fields = ['location', 'contactPerson', 'relatedKaCsa', 'tanev', 'riporter']
    filter_horizontal = ['equipments']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('🎬 Forgatás alapadatok', {
            'fields': ('name', 'description', 'forgTipus', 'tanev', 'riporter'),
            'description': 'A forgatás alapvető információi'
        }),
        ('⏰ Időpont', {
            'fields': ('date', 'timeFrom', 'timeTo'),
            'description': 'A forgatás időbeli paraméterei'
        }),
        ('📍 Helyszín és kapcsolatok', {
            'fields': ('location', 'contactPerson'),
            'description': 'Helyszín és kapcsolattartó adatok'
        }),
        ('🔗 Kapcsolódó forgatás', {
            'fields': ('relatedKaCsa',),
            'classes': ('collapse',),
            'description': 'Rendes forgatások esetében, a kapcsolódó KaCsa Összejátszás'
        }),
        ('🎯 Eszközök', {
            'fields': ('equipments',),
            'description': 'A forgatáshoz szükséges eszközök'
        }),
        ('📝 Megjegyzések', {
            'fields': ('notes',),
            'classes': ('collapse',),
            'description': 'További információk és megjegyzések'
        })
    )
    
    def name_with_icon(self, obj):
        icons = {
            'kacsa': '🦆',
            'rendes': '🎬', 
            'rendezveny': '🎉',
            'egyeb': '📹'
        }
        icon = icons.get(obj.forgTipus, '📹')
        return format_html('{} <strong>{}</strong>', icon, obj.name)
    name_with_icon.short_description = 'Forgatás neve'
    
    def time_display(self, obj):
        return f"{obj.timeFrom.strftime('%H:%M')} - {obj.timeTo.strftime('%H:%M')}"
    time_display.short_description = 'Időintervallum'
    
    def forgTipus_display(self, obj):
        colors = {
            'kacsa': '#ff6b35',
            'rendes': '#004e89',
            'rendezveny': '#7209b7', 
            'egyeb': '#6c757d'
        }
        color = colors.get(obj.forgTipus, '#6c757d')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_forgTipus_display())
    forgTipus_display.short_description = 'Típus'

    def riporter_display(self, obj):
        if obj.riporter:
            return format_html('<span style="color: #7209b7;">🎤 {}</span>', obj.riporter.get_full_name() or obj.riporter.username)
        return '-'
    riporter_display.short_description = 'Riporter'
    
    def location_display(self, obj):
        if obj.location:
            return format_html('📍 {}', obj.location.name)
        return '-'
    location_display.short_description = 'Helyszín'
    
    def equipment_count(self, obj):
        count = obj.equipments.count()
        if count > 0:
            return format_html('<span style="color: green;">🎯 {} db</span>', count)
        return format_html('<span style="color: red;">⚠️ Nincs</span>')
    equipment_count.short_description = 'Eszközök'

@admin.register(Beosztas)
class BeosztasAdmin(ImportExportModelAdmin):
    resource_class = BeosztasResource
    list_display = ['beosztas_display', 'kesz_status', 'author', 'tanev', 'forgatas_link', 'created_at', 'szerepkor_count']
    list_filter = ['kesz', 'tanev', 'created_at', 'author']
    search_fields = ['author__first_name', 'author__last_name', 'forgatas__name']
    autocomplete_fields = ['author', 'tanev', 'forgatas']
    filter_horizontal = ['szerepkor_relaciok']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('📋 Beosztás adatok', {
            'fields': ('kesz', 'author', 'tanev', 'forgatas'),
            'description': 'A beosztás alapvető információi'
        }),
        ('👥 Szerepkör relációk', {
            'fields': ('szerepkor_relaciok',),
            'description': 'A beosztáshoz tartozó szerepkör-felhasználó párosítások'
        }),
        ('📊 Metaadatok', {
            'fields': ('created_at',),
            'classes': ('collapse',),
            'description': 'Automatikusan generált adatok'
        })
    )
    
    def beosztas_display(self, obj):
        return format_html('📋 <strong>Beosztás #{}</strong>', obj.id)
    beosztas_display.short_description = 'Beosztás'
    
    def kesz_status(self, obj):
        if obj.kesz:
            return format_html('<span style="color: green; font-weight: bold;">✅ Kész</span>')
        return format_html('<span style="color: orange; font-weight: bold;">⏳ Folyamatban</span>')
    kesz_status.short_description = 'Státusz'
    
    def forgatas_link(self, obj):
        if obj.forgatas:
            url = reverse('admin:api_forgatas_change', args=[obj.forgatas.id])
            return format_html('<a href="{}" target="_blank">🎬 {}</a>', url, obj.forgatas.name)
        return '-'
    forgatas_link.short_description = 'Kapcsolódó forgatás'
    
    def szerepkor_count(self, obj):
        count = obj.szerepkor_relaciok.count()
        return format_html('<span style="color: blue;">👥 {} db</span>', count)
    szerepkor_count.short_description = 'Szerepkörök száma'

# ============================================================================
# 📻 RÁDIÓS RENDSZER (RADIO SYSTEM)
# ============================================================================

@admin.register(RadioStab)
class RadioStabAdmin(ImportExportModelAdmin):
    resource_class = RadioStabResource
    list_display = ['stab_display', 'team_code_display', 'member_count', 'session_count']
    list_filter = ['team_code']
    search_fields = ['name', 'team_code', 'description']
    
    fieldsets = (
        ('📻 Rádiós stáb adatok', {
            'fields': ('name', 'team_code'),
            'description': 'A rádiós stáb alapvető azonosítói'
        }),
        ('📝 Leírás', {
            'fields': ('description',),
            'description': 'A stáb részletes leírása'
        })
    )
    
    def stab_display(self, obj):
        return format_html('📻 <strong>{}</strong>', obj.name)
    stab_display.short_description = 'Stáb neve'
    
    def team_code_display(self, obj):
        colors = {'A1': '#ff6b35', 'A2': '#f7931e', 'B3': '#0066cc', 'B4': '#004e89'}
        color = colors.get(obj.team_code, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">{}</span>', color, obj.team_code)
    team_code_display.short_description = 'Csapat kód'
    
    def member_count(self, obj):
        count = obj.get_members().count()
        return format_html('<span style="color: blue;">👥 {} fő</span>', count)
    member_count.short_description = 'Tagok száma'
    
    def session_count(self, obj):
        count = RadioSession.objects.filter(radio_stab=obj).count()
        return format_html('<span style="color: green;">📻 {} alkalom</span>', count)
    session_count.short_description = 'Összejátszások'

@admin.register(RadioSession)
class RadioSessionAdmin(ImportExportModelAdmin):
    resource_class = RadioSessionResource
    list_display = ['session_display', 'radio_stab', 'date', 'time_display', 'participant_count', 'tanev']
    list_filter = ['radio_stab', 'date', 'tanev']
    search_fields = ['radio_stab__name', 'description']
    autocomplete_fields = ['radio_stab', 'tanev']
    filter_horizontal = ['participants']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('📻 Rádiós összejátszás', {
            'fields': ('radio_stab', 'tanev'),
            'description': 'Melyik rádiós stáb összejátszása'
        }),
        ('⏰ Időpont', {
            'fields': ('date', 'time_from', 'time_to'),
            'description': 'Az összejátszás időbeli paraméterei'
        }),
        ('👥 Résztvevők', {
            'fields': ('participants',),
            'description': 'Az összejátszásban résztvevő diákok'
        }),
        ('📝 Leírás', {
            'fields': ('description',),
            'description': 'Az összejátszás részletes leírása'
        }),
        ('📊 Metaadatok', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def session_display(self, obj):
        return format_html('📻 <strong>Összejátszás #{}</strong>', obj.id)
    session_display.short_description = 'Összejátszás'
    
    def time_display(self, obj):
        return f"{obj.time_from.strftime('%H:%M')} - {obj.time_to.strftime('%H:%M')}"
    time_display.short_description = 'Időintervallum'
    
    def participant_count(self, obj):
        count = obj.participants.count()
        return format_html('<span style="color: blue;">👥 {} fő</span>', count)
    participant_count.short_description = 'Résztvevők száma'

# ============================================================================
# 🎯 ESZKÖZÖK ÉS FELSZERELÉS (EQUIPMENT SYSTEM)
# ============================================================================

@admin.register(Equipment)
class EquipmentAdmin(ImportExportModelAdmin):
    resource_class = EquipmentResource
    list_display = ['equipment_display', 'brand', 'model', 'equipmentType', 'functional_status', 'usage_count']
    list_filter = ['equipmentType', 'functional', 'brand']
    search_fields = ['nickname', 'brand', 'model', 'serialNumber']
    autocomplete_fields = ['equipmentType']
    
    fieldsets = (
        ('🎯 Eszköz alapadatok', {
            'fields': ('nickname', 'equipmentType', 'functional'),
            'description': 'Az eszköz alapvető azonosítói és státusza'
        }),
        ('🏷️ Gyártó adatok', {
            'fields': ('brand', 'model', 'serialNumber'),
            'description': 'Az eszköz gyártói és technikai adatai'
        }),
        ('📝 Megjegyzések', {
            'fields': ('notes',),
            'classes': ('collapse',),
            'description': 'További információk az eszközről'
        })
    )
    
    def equipment_display(self, obj):
        icon = obj.equipmentType.emoji if obj.equipmentType and obj.equipmentType.emoji else '🎯'
        return format_html('{} <strong>{}</strong>', icon, obj.nickname)
    equipment_display.short_description = 'Eszköz neve'
    
    def functional_status(self, obj):
        if obj.functional:
            return format_html('<span style="color: green; font-weight: bold;">✅ Működik</span>')
        return format_html('<span style="color: red; font-weight: bold;">❌ Hibás</span>')
    functional_status.short_description = 'Állapot'
    
    def usage_count(self, obj):
        count = obj.forgatasok.count()
        return format_html('<span style="color: blue;">🎬 {} forgatás</span>', count)
    usage_count.short_description = 'Használat'

@admin.register(EquipmentTipus)
class EquipmentTipusAdmin(ImportExportModelAdmin):
    resource_class = EquipmentTipusResource
    list_display = ['tipus_display', 'equipment_count']
    search_fields = ['name']
    
    def tipus_display(self, obj):
        emoji = obj.emoji if obj.emoji else '🎯'
        return format_html('{} <strong>{}</strong>', emoji, obj.name)
    tipus_display.short_description = 'Eszköz típus'
    
    def equipment_count(self, obj):
        count = obj.equipments.count()
        return format_html('<span style="color: blue;">🎯 {} db</span>', count)
    equipment_count.short_description = 'Eszközök száma'

# ============================================================================
# 🤝 PARTNEREK ÉS KAPCSOLATOK (PARTNERS & CONTACTS)
# ============================================================================

@admin.register(Partner)
class PartnerAdmin(ImportExportModelAdmin):
    resource_class = PartnerResource
    list_display = ['partner_display', 'institution', 'address_short', 'forgatas_count']
    list_filter = ['institution']
    search_fields = ['name', 'address']
    autocomplete_fields = ['institution']
    
    fieldsets = (
        ('🤝 Partner adatok', {
            'fields': ('name', 'institution'),
            'description': 'A partner alapvető azonosítói'
        }),
        ('📍 Elérhetőség', {
            'fields': ('address', 'imgUrl'),
            'description': 'A partner címe és képe'
        })
    )
    
    def partner_display(self, obj):
        return format_html('🤝 <strong>{}</strong>', obj.name)
    partner_display.short_description = 'Partner neve'
    
    def address_short(self, obj):
        if obj.address:
            return obj.address[:50] + '...' if len(obj.address) > 50 else obj.address
        return '-'
    address_short.short_description = 'Cím'
    
    def forgatas_count(self, obj):
        count = Forgatas.objects.filter(location=obj).count()
        return format_html('<span style="color: green;">🎬 {} forgatás</span>', count)
    forgatas_count.short_description = 'Forgatások száma'

@admin.register(PartnerTipus)
class PartnerTipusAdmin(ImportExportModelAdmin):
    resource_class = PartnerTipusResource
    list_display = ['tipus_display', 'partner_count']
    search_fields = ['name']
    
    def tipus_display(self, obj):
        return format_html('🏢 <strong>{}</strong>', obj.name)
    tipus_display.short_description = 'Intézmény típus'
    
    def partner_count(self, obj):
        count = obj.partners.count()
        return format_html('<span style="color: blue;">🤝 {} partner</span>', count)
    partner_count.short_description = 'Partnerek száma'

@admin.register(ContactPerson)
class ContactPersonAdmin(ImportExportModelAdmin):
    resource_class = ContactPersonResource
    list_display = ['contact_display', 'email', 'phone', 'forgatas_count']
    search_fields = ['name', 'email', 'phone']
    
    def contact_display(self, obj):
        return format_html('👤 <strong>{}</strong>', obj.name)
    contact_display.short_description = 'Kapcsolattartó'
    
    def forgatas_count(self, obj):
        count = Forgatas.objects.filter(contactPerson=obj).count()
        return format_html('<span style="color: green;">🎬 {} forgatás</span>', count)
    forgatas_count.short_description = 'Forgatások száma'

# ============================================================================
# 📢 KOMMUNIKÁCIÓ (COMMUNICATIONS)
# ============================================================================

@admin.register(Announcement)
class AnnouncementAdmin(ImportExportModelAdmin):
    resource_class = AnnouncementResource
    list_display = ['announcement_display', 'author', 'created_at', 'updated_at', 'recipient_count']
    list_filter = ['created_at', 'updated_at', 'author']
    search_fields = ['title', 'body']
    autocomplete_fields = ['author']
    filter_horizontal = ['cimzettek']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('📢 Közlemény adatok', {
            'fields': ('title', 'author'),
            'description': 'A közlemény címe és szerzője'
        }),
        ('📝 Tartalom', {
            'fields': ('body',),
            'description': 'A közlemény szövege'
        }),
        ('👥 Címzettek', {
            'fields': ('cimzettek',),
            'description': 'A közleményt megkapó felhasználók'
        }),
        ('📊 Metaadatok', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def announcement_display(self, obj):
        return format_html('📢 <strong>{}</strong>', obj.title)
    announcement_display.short_description = 'Közlemény címe'
    
    def recipient_count(self, obj):
        count = obj.cimzettek.count()
        return format_html('<span style="color: blue;">👥 {} fő</span>', count)
    recipient_count.short_description = 'Címzettek száma'

# ============================================================================
# 📚 HIÁNYZÁSOK ÉS TÁVOLLÉTEK (ABSENCES)
# ============================================================================

@admin.register(Absence)
class AbsenceAdmin(ImportExportModelAdmin):
    resource_class = AbsenceResource
    list_display = ['absence_display', 'diak', 'forgatas_link', 'date', 'time_display', 'status_display', 'auto_generated_display', 'affected_classes']
    list_filter = ['excused', 'unexcused', 'auto_generated', 'date', 'forgatas']
    search_fields = ['diak__first_name', 'diak__last_name', 'forgatas__name']
    autocomplete_fields = ['diak', 'forgatas']
    date_hierarchy = 'date'
    
    readonly_fields = ['get_affected_classes_display']
    
    fieldsets = (
        ('📚 Hiányzás adatok', {
            'fields': ('diak', 'forgatas'),
            'description': 'A hiányzó diák és a forgatás'
        }),
        ('⏰ Időpont', {
            'fields': ('date', 'timeFrom', 'timeTo'),
            'description': 'A hiányzás időbeli paraméterei'
        }),
        ('✅ Státusz', {
            'fields': ('excused', 'unexcused', 'auto_generated'),
            'description': 'A hiányzás igazoltsági státusza és típusa'
        }),
        ('📊 Érintett órák', {
            'fields': ('get_affected_classes_display',),
            'classes': ('collapse',)
        })
    )
    
    def absence_display(self, obj):
        return format_html('📚 <strong>Hiányzás #{}</strong>', obj.id)
    absence_display.short_description = 'Hiányzás'
    
    def forgatas_link(self, obj):
        url = reverse('admin:api_forgatas_change', args=[obj.forgatas.id])
        return format_html('<a href="{}" target="_blank">🎬 {}</a>', url, obj.forgatas.name)
    forgatas_link.short_description = 'Forgatás'
    
    def time_display(self, obj):
        return f"{obj.timeFrom.strftime('%H:%M')} - {obj.timeTo.strftime('%H:%M')}"
    time_display.short_description = 'Időintervallum'
    
    def status_display(self, obj):
        if obj.excused:
            return format_html('<span style="color: green; font-weight: bold;">✅ Igazolt</span>')
        elif obj.unexcused:
            return format_html('<span style="color: red; font-weight: bold;">❌ Igazolatlan</span>')
        return format_html('<span style="color: orange; font-weight: bold;">⏳ Függőben</span>')
    status_display.short_description = 'Státusz'
    
    def auto_generated_display(self, obj):
        if obj.auto_generated:
            return format_html('<span style="color: blue; font-weight: bold;">🤖 Auto</span>')
        return format_html('<span style="color: gray; font-weight: bold;">👤 Kézi</span>')
    auto_generated_display.short_description = 'Típus'
    
    def affected_classes(self, obj):
        classes = obj.get_affected_classes()
        return ', '.join([f"{hour}. óra" for hour in classes]) if classes else 'Nincs'
    affected_classes.short_description = 'Érintett órák'
    
    def get_affected_classes_display(self, obj):
        return ', '.join([f"{hour}. óra" for hour in obj.get_affected_classes()])
    get_affected_classes_display.short_description = 'Érintett órák'

@admin.register(Tavollet)
class TavolletAdmin(ImportExportModelAdmin):
    resource_class = TavolletResource
    list_display = ['tavollet_display', 'user', 'date_range', 'duration_days', 'status_display']
    list_filter = ['denied', 'start_date', 'end_date']
    search_fields = ['user__first_name', 'user__last_name', 'reason']
    autocomplete_fields = ['user']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('👤 Távollét adatok', {
            'fields': ('user',),
            'description': 'A távollétben lévő felhasználó'
        }),
        ('📅 Időszak', {
            'fields': ('start_date', 'end_date'),
            'description': 'A távollét kezdete és vége'
        }),
        ('📝 Indoklás és státusz', {
            'fields': ('reason', 'denied'),
            'description': 'A távollét oka és jóváhagyási státusza'
        })
    )
    
    def tavollet_display(self, obj):
        return format_html('🏠 <strong>Távollét #{}</strong>', obj.id)
    tavollet_display.short_description = 'Távollét'
    
    def date_range(self, obj):
        return f"{obj.start_date} - {obj.end_date}"
    date_range.short_description = 'Időszak'
    
    def duration_days(self, obj):
        duration = (obj.end_date - obj.start_date).days + 1
        return format_html('<span style="color: blue;">📅 {} nap</span>', duration)
    duration_days.short_description = 'Időtartam'
    
    def status_display(self, obj):
        if obj.denied:
            return format_html('<span style="color: red; font-weight: bold;">❌ Elutasítva</span>')
        return format_html('<span style="color: green; font-weight: bold;">✅ Jóváhagyva</span>')
    status_display.short_description = 'Státusz'

# ============================================================================
# 🏢 SZERVEZETI EGYSÉGEK (ORGANIZATIONAL UNITS)
# ============================================================================

@admin.register(Stab)
class StabAdmin(ImportExportModelAdmin):
    resource_class = StabResource
    list_display = ['stab_display', 'member_count']
    search_fields = ['name']
    
    def stab_display(self, obj):
        return format_html('🎬 <strong>{}</strong>', obj.name)
    stab_display.short_description = 'Stáb neve'
    
    def member_count(self, obj):
        count = obj.tagok.count()
        return format_html('<span style="color: blue;">👥 {} fő</span>', count)
    member_count.short_description = 'Tagok száma'

# ============================================================================
# ⚙️ RENDSZER KONFIGURÁCIÓ (SYSTEM CONFIGURATION)
# ============================================================================

@admin.register(Config)
class ConfigAdmin(ImportExportModelAdmin):
    resource_class = ConfigResource
    list_display = ['config_display', 'active_status', 'email_status']
    list_filter = ['active', 'allowEmails']
    
    fieldsets = (
        ('⚙️ Rendszer konfiguráció', {
            'fields': ('active', 'allowEmails'),
            'description': 'Alapvető rendszer beállítások'
        }),
    )
    
    def config_display(self, obj):
        return format_html('⚙️ <strong>Rendszer konfiguráció #{}</strong>', obj.id)
    config_display.short_description = 'Konfiguráció'
    
    def active_status(self, obj):
        if obj.active:
            return format_html('<span style="color: green; font-weight: bold;">✅ Aktív</span>')
        return format_html('<span style="color: red; font-weight: bold;">❌ Inaktív</span>')
    active_status.short_description = 'Rendszer státusz'
    
    def email_status(self, obj):
        if obj.allowEmails:
            return format_html('<span style="color: green; font-weight: bold;">📧 Engedélyezve</span>')
        return format_html('<span style="color: red; font-weight: bold;">🚫 Letiltva</span>')
    email_status.short_description = 'Email státusz'

# ============================================================================
# 🔧 SZEREPKÖR RENDSZER (ROLE SYSTEM) - Ritkábban használt
# ============================================================================

@admin.register(Szerepkor)
class SzerepkorAdmin(ImportExportModelAdmin):
    resource_class = SzerepkorResource
    list_display = ['szerepkor_display', 'ev', 'usage_count']
    list_filter = ['ev']
    search_fields = ['name']
    
    def szerepkor_display(self, obj):
        return format_html('🎭 <strong>{}</strong>', obj.name)
    szerepkor_display.short_description = 'Szerepkör'
    
    def usage_count(self, obj):
        count = SzerepkorRelaciok.objects.filter(szerepkor=obj).count()
        return format_html('<span style="color: blue;">👥 {} hozzárendelés</span>', count)
    usage_count.short_description = 'Használat'

# ============================================================================
# 🔗 KAPCSOLÓTÁBLÁK (RELATION TABLES) - Ritkán szerkesztett
# ============================================================================

class SzerepkorRelaciokAdmin(ImportExportModelAdmin):
    """
    Szerepkör relációk - Ritkán használt kapcsolótábla
    Általában a Beosztas-on keresztül kezelendő
    """
    resource_class = SzerepkorRelaciokResource
    list_display = ['relacio_display', 'user', 'szerepkor']
    list_filter = ['szerepkor']
    search_fields = ['user__first_name', 'user__last_name', 'szerepkor__name']
    autocomplete_fields = ['user', 'szerepkor']
    
    def relacio_display(self, obj):
        return format_html('🔗 <strong>#{}</strong>', obj.id)
    relacio_display.short_description = 'Reláció'
    
    def has_module_permission(self, request):
        """Csak superuser-ek láthatják az admin menüben"""
        return request.user.is_superuser
        
# Regisztráljuk, de ne jelenjen meg az admin menüben alapértelmezetten
admin.site.register(SzerepkorRelaciok, SzerepkorRelaciokAdmin)

# ============================================================================
# ADMIN SITE TESTRESZABÁS
# ============================================================================

# Admin site címek és leírások testreszabása
admin.site.site_header = '🎬 FTV Adminisztráció'
admin.site.site_title = 'FTV Admin'
admin.site.index_title = 'FTV Rendszer Adminisztráció'

# Register Atigazolas model
@admin.register(Atigazolas)
class AtigazolasAdmin(ImportExportModelAdmin):
    resource_class = AtigazolasResource if 'AtigazolasResource' in globals() else None
    list_display = ['profile', 'previous_stab', 'previous_radio_stab', 'new_stab', 'new_radio_stab', 'datetime']
    search_fields = ['profile__user__username', 'profile__user__first_name', 'profile__user__last_name', 'previous_stab', 'new_stab', 'previous_radio_stab', 'new_radio_stab']
    list_filter = ['previous_stab', 'new_stab', 'previous_radio_stab', 'new_radio_stab', 'datetime']