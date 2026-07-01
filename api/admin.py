from django.contrib import admin
from django.contrib.auth.models import User, Group
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
from django.forms.widgets import CheckboxSelectMultiple
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from .models import *
from .resources import *
import secrets
import string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from datetime import timedelta
from django.db.models import Q

# ============================================================================
# 🔐 PASSWORD GENERATION AND EMAIL UTILITIES
# ============================================================================

def generate_secure_short_password(length=8):
    """
    Generate a secure but short password with letters and numbers
    
    Args:
        length (int): Password length (default: 8)
        
    Returns:
        str: Generated password
    """
    # Use both uppercase, lowercase letters and digits
    alphabet = string.ascii_letters + string.digits
    # Ensure at least one digit and one letter
    password = secrets.choice(string.ascii_lowercase) + secrets.choice(string.digits)
    # Fill the rest randomly
    password += ''.join(secrets.choice(alphabet) for _ in range(length - 2))
    
    # Shuffle the password to avoid predictable patterns
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)
    return ''.join(password_list)

def send_login_info_email(user, password):
    """
    Send login information email to user with HTML formatting
    
    Args:
        user (User): User instance
        password (str): Generated password
        
    Returns:
        bool: Success status
    """
    subject = "FTV - Új bejelentkezési adatok"
    
    # Import email templates
    from backend.email_templates import (
        get_base_email_template, 
        get_login_info_email_content
    )
    
    # Get user name
    user_name = user.get_full_name() if user.get_full_name() else user.username
    
    # Generate email content using the new template system
    content = get_login_info_email_content(user_name, user.username, password)
    
    # Create complete HTML email
    html_message = get_base_email_template(
        title="Új bejelentkezési adatok",
        content=content,
        button_text="FTV Rendszer megnyitása",
        button_url="https://ftv.szlg.info"
    )
    
    # Create plain text version
    plain_message = f"""
Kedves {user_name}!

Új jelszót generáltunk az Ön FTV rendszerbeli fiókjához.

Bejelentkezési adatok:
Felhasználónév: {user.username}
Új jelszó: {password}

FONTOS BIZTONSÁGI TUDNIVALÓK:
- Kérjük, változtassa meg a jelszót első bejelentkezéskor
- Használjon erős, egyedi jelszót
- Ne ossza meg senkivel a bejelentkezési adatait
- Tartsa biztonságban ezt az emailt

Bejelentkezés: https://ftv.szlg.info

Ha kérdése van, vagy problémája adódna, kérjük vegye fel a kapcsolatot az adminisztrátorral.

Ez egy automatikus email, kérjük ne válaszoljon rá.

© 2025 FTV. Minden jog fenntartva.
    """
    
    # Debug email sending details
    print(f"       📧 Email címzett: {user.email}")
    print(f"       📧 Email feladó: {settings.DEFAULT_FROM_EMAIL}")
    print(f"       📧 Email tárgy: {subject}")
    print(f"       📝 Jelszó az emailben: {password}")
    
    try:
        print(f"       🚀 Email küldés megkezdése...")
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        print(f"       ✅ Email sikeresen elküldve!")
        return True
    except Exception as e:
        print(f"       ❌ Email küldés sikertelen!")
        print(f"       🔍 Hiba típusa: {type(e).__name__}")
        print(f"       💬 Hiba üzenet: {str(e)}")
        
        # Check for common email configuration issues
        if "Connection refused" in str(e):
            print(f"       🔧 Lehetséges ok: SMTP szerver nem elérhető")
        elif "Authentication failed" in str(e):
            print(f"       🔧 Lehetséges ok: Hibás email hitelesítési adatok")
        elif "Invalid sender" in str(e):
            print(f"       🔧 Lehetséges ok: Hibás feladó email cím")
        
        return False

def generate_password_and_notify(modeladmin, request, queryset):
    """
    Bulk action to generate new passwords and send email notifications
    
    Args:
        modeladmin: The admin class
        request: The HTTP request
        queryset: Selected User objects
    """
    import datetime
    
    # Initialize counters and lists
    success_count = 0
    error_count = 0
    email_errors = []
    processed_users = []
    
    # Terminal debug: Start of bulk action
    print("=" * 80)
    print(f"🔐 [DEBUG] JELSZÓ GENERÁLÁS ÉS ÉRTESÍTÉS KEZDŐDIK")
    print(f"📅 Időpont: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 Kezdeményező admin: {request.user.username}")
    print(f"📊 Kiválasztott felhasználók száma: {queryset.count()}")
    
    # Email configuration debug
    try:
        print(f"⚙️  EMAIL KONFIGURÁCIÓ:")
        print(f"   📧 EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Nincs beállítva')}")
        print(f"   📧 DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Nincs beállítva')}")
        print(f"   📧 EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Nincs beállítva')}")
        print(f"   📧 EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Nincs beállítva')}")
        print(f"   📧 EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Nincs beállítva')}")
    except Exception as e:
        print(f"   ❌ Hiba az email konfiguráció betöltésénél: {e}")
    
    print("=" * 80)
    
    # Show initial warning message in Django admin
    messages.warning(
        request,
        f"⏳ FELDOLGOZÁS FOLYAMATBAN: {queryset.count()} felhasználó jelszó generálása és email értesítése elkezdődött. "
        f"Kérjük várjon türelmesen, a művelet eltarthat néhány percig. Az eredmény a feldolgozás végén fog megjelenni."
    )
    
    for index, user in enumerate(queryset, 1):
        print(f"\n📝 [{index}/{queryset.count()}] Feldolgozás: {user.username}")
        print(f"   📧 Email: {user.email or 'NINCS EMAIL'}")
        print(f"   👤 Név: {user.get_full_name() or 'Név nincs megadva'}")
        
        try:
            # Check if user has email
            if not user.email:
                error_count += 1
                print(f"   ❌ Hiba: Nincs email cím megadva")
                email_errors.append(f"{user.username} (nincs email)")
                continue
            
            # Generate new password
            print(f"   🔑 Jelszó generálása...")
            new_password = generate_secure_short_password()
            print(f"   ✅ Jelszó generálva: {new_password}")
            
            # Set the new password
            print(f"   💾 Jelszó mentése az adatbázisba...")
            user.set_password(new_password)
            user.save()
            print(f"   ✅ Jelszó sikeresen mentve")
            
            # Send email with login information
            print(f"   📧 Email küldése...")
            if send_login_info_email(user, new_password):
                success_count += 1
                processed_users.append(f"{user.username} ({user.email})")
                print(f"   ✅ Email sikeresen elküldve: {user.email}")
            else:
                email_errors.append(f"{user.username} (email küldése sikertelen)")
                print(f"   ❌ Email küldése sikertelen: {user.email}")
                
        except Exception as e:
            error_count += 1
            print(f"   ❌ HIBA történt: {str(e)}")
            print(f"   🔍 Hiba típusa: {type(e).__name__}")
            email_errors.append(f"{user.username} (hiba: {str(e)})")
    
    # Terminal debug: Summary
    print("\n" + "=" * 80)
    print(f"📊 JELSZÓ GENERÁLÁS ÖSSZEFOGLALÓ")
    print(f"✅ Sikeresek: {success_count}")
    print(f"❌ Hibák: {error_count}")
    print(f"📧 Email hibák: {len(email_errors)}")
    print(f"📝 Feldolgozott felhasználók:")
    for user_info in processed_users:
        print(f"   - {user_info}")
    if email_errors:
        print(f"📧 Email hibák a következő felhasználóknál:")
        for username in email_errors:
            print(f"   - {username}")
    print("=" * 80)
    
    # Show comprehensive final summary messages in Django admin
    total_processed = queryset.count()
    
    # Main result summary
    if success_count == total_processed and error_count == 0 and len(email_errors) == 0:
        messages.success(
            request,
            f"🏆 TELJES SIKER: Mind a {total_processed} kiválasztott felhasználónál sikeresen megtörtént a jelszó generálás és email értesítés!"
        )
    elif success_count > 0:
        messages.success(
            request, 
            f"✅ RÉSZLEGES SIKER: {success_count}/{total_processed} felhasználónál sikeresen generáltunk új jelszót és küldtünk email értesítést."
        )
    else:
        messages.error(
            request,
            f"❌ TELJES KUDARC: Egyetlen felhasználónál sem sikerült a jelszó generálás és értesítés! ({total_processed} megpróbálva)"
        )
    
    # Detailed success information
    if success_count > 0:
        if len(processed_users) <= 15:  # Show details if not too many users
            user_list = ", ".join([user.split(" (")[0] for user in processed_users])
            messages.info(
                request,
                f"📋 Sikeres felhasználók ({success_count}): {user_list}"
            )
        else:
            messages.info(
                request,
                f"📋 {success_count} felhasználónál sikeres volt a művelet. A részletes lista megtalálható a terminál kimenetében."
            )
    
    # Show errors and problems with details
    if email_errors:
        error_details = []
        no_email_users = []
        email_failed_users = []
        other_errors = []
        
        for error in email_errors:
            if "(nincs email)" in error:
                no_email_users.append(error.split(" (")[0])
            elif "(email küldése sikertelen)" in error:
                email_failed_users.append(error.split(" (")[0])
            else:
                other_errors.append(error)
        
        if no_email_users:
            messages.warning(
                request,
                f"⚠️ NINCS EMAIL CÍM: {len(no_email_users)} felhasználónál nincs email cím megadva: {', '.join(no_email_users)}"
            )
        
        if email_failed_users:
            messages.error(
                request,
                f"� EMAIL KÜLDÉSI HIBA: {len(email_failed_users)} felhasználónál sikertelen volt az email küldés: {', '.join(email_failed_users)}"
            )
        
        if other_errors:
            messages.error(
                request,
                f"💥 EGYÉB HIBÁK: {len(other_errors)} felhasználónál egyéb hiba történt. Részletek a terminál kimenetében."
            )
    
    # Performance and timing info
    messages.info(
        request,
        f"📊 ÖSSZESÍTÉS: Feldolgozva {total_processed} felhasználó | "
        f"Sikeres: {success_count} | "
        f"Hibás: {len(email_errors)} | "
        f"A részletes naplók a szerver terminálján tekinthetők meg."
    )

generate_password_and_notify.short_description = "Új jelszó generálása és értesítés"

# ============================================================================
# 👤 USER MANAGEMENT WITH IMPORT/EXPORT
# ============================================================================

class LastLoginFilter(admin.SimpleListFilter):
    """Custom filter for User last_login field with special handling for null values"""
    title = 'utolsó bejelentkezés'
    parameter_name = 'last_login'

    def lookups(self, request, model_admin):
        return (
            ('never', 'Sosem jelentkezett be (NULL)'),
            ('today', 'Ma'),
            ('week', 'Egy héten belül'),
            ('month', '30 napon belül'),
            ('3months', '3 hónapon belül'),
            ('6months', '6 hónapon belül'),
            ('year', '1 éven belül'),
            ('older', '1 évnél régebben'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'never':
            return queryset.filter(last_login__isnull=True)
        elif self.value() == 'today':
            return queryset.filter(
                last_login__date=now.date(),
                last_login__isnull=False
            )
        elif self.value() == 'week':
            return queryset.filter(
                last_login__gte=now - timedelta(days=7),
                last_login__isnull=False
            )
        elif self.value() == 'month':
            return queryset.filter(
                last_login__gte=now - timedelta(days=30),
                last_login__isnull=False
            )
        elif self.value() == '3months':
            return queryset.filter(
                last_login__gte=now - timedelta(days=90),
                last_login__isnull=False
            )
        elif self.value() == '6months':
            return queryset.filter(
                last_login__gte=now - timedelta(days=180),
                last_login__isnull=False
            )
        elif self.value() == 'year':
            return queryset.filter(
                last_login__gte=now - timedelta(days=365),
                last_login__isnull=False
            )
        elif self.value() == 'older':
            return queryset.filter(
                last_login__lt=now - timedelta(days=365),
                last_login__isnull=False
            )
        
        return queryset

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
            # Only set password if a new one was provided
            if not password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$')):
                # Hash the new password
                user.set_password(password)
            else:
                # If it's already hashed (shouldn't happen with our form), use as is
                user.password = password
        else:
            # If no password provided, preserve the existing password
            # Get the original user from database to preserve password
            if user.pk:
                try:
                    original_user = User.objects.get(pk=user.pk)
                    user.password = original_user.password
                except User.DoesNotExist:
                    pass  # New user, no existing password to preserve
        
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
    
    list_display = ['username', 'last_name', 'first_name', 'email', 'last_login_display', 'groups_display', 'is_active', 'is_staff', 'is_superuser']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'groups', 'date_joined', LastLoginFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    readonly_fields = ['date_joined', 'last_login', 'password_info']
    actions = [generate_password_and_notify]
    filter_horizontal = ['groups', 'user_permissions']
    
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
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
        ('👥 Csoportok és jogosultságok', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
    )
    
    def groups_display(self, obj):
        """Show user's groups in list view"""
        groups = obj.groups.all()
        if not groups:
            return format_html('<span style="color: #666; font-style: italic;">Nincs csoport</span>')
        
        group_html_parts = []
        for group in groups[:3]:  # Show first 3 groups
            # Color code based on group name
            if 'admin' in group.name.lower() or 'superuser' in group.name.lower():
                color = '#dc3545'  # Red for admin
                icon = '👑'
            elif 'staff' in group.name.lower() or 'teacher' in group.name.lower() or 'tanár' in group.name.lower():
                color = '#007bff'  # Blue for staff
                icon = '👨‍💼'
            else:
                color = '#6c757d'  # Gray for others
                icon = '👥'
            
            group_html_parts.append(
                '<span style="background: {}; color: white; padding: 1px 4px; border-radius: 2px; font-size: 11px; margin-right: 2px; white-space: nowrap;">{} {}</span>'.format(
                    color, icon, group.name
                )
            )
        
        # Add "and X more" if there are more groups
        if len(groups) > 3:
            group_html_parts.append(
                '<span style="color: #666; font-style: italic;">+{} további</span>'.format(len(groups) - 3)
            )
        
        return mark_safe(''.join(group_html_parts))
    groups_display.short_description = '👥 Csoportok'

    def last_login_display(self, obj):
        """Show last login with nice formatting and null handling"""
        if not obj.last_login:
            return format_html('<span style="color: #dc3545; font-weight: bold;">❌ Sosem</span>')
        
        now = timezone.now()
        login_time = obj.last_login
        time_diff = now - login_time
        
        # Format the display based on how recent the login was
        if time_diff.days == 0:
            if time_diff.seconds < 3600:  # Less than 1 hour
                return format_html(
                    '<span style="color: #28a745; font-weight: bold;">🟢 {} perc</span>',
                    time_diff.seconds // 60
                )
            else:  # Same day but more than 1 hour
                return format_html(
                    '<span style="color: #28a745;">✅ Ma {}</span>',
                    login_time.strftime('%H:%M')
                )
        elif time_diff.days == 1:
            return format_html(
                '<span style="color: #6f42c1;">📅 Tegnap {}</span>',
                login_time.strftime('%H:%M')
            )
        elif time_diff.days <= 7:
            return format_html(
                '<span style="color: #0066cc;">📅 {} nap</span>',
                time_diff.days
            )
        elif time_diff.days <= 30:
            return format_html(
                '<span style="color: #fd7e14;">📅 {} nap ({})</span>',
                time_diff.days, login_time.strftime('%m-%d')
            )
        elif time_diff.days <= 365:
            return format_html(
                '<span style="color: #e83e8c;">📅 {} nap ({})</span>',
                time_diff.days, login_time.strftime('%Y-%m-%d')
            )
        else:
            return format_html(
                '<span style="color: #dc3545;">⚠️ {} nap ({})</span>',
                time_diff.days, login_time.strftime('%Y-%m-%d')
            )
    last_login_display.short_description = '🕒 Utolsó bejelentkezés'

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
        # Password handling is now done in the form's save method
        # No need to duplicate password processing here
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
    list_display = ['display_osztaly', 'startYear', 'szekcio', 'display_tanev', 'student_count', 'fonok_count']
    list_filter = ['szekcio', 'startYear', 'tanevek']
    search_fields = ['szekcio', 'startYear']
    filter_horizontal = ['osztaly_fonokei']
    
    fieldsets = (
        ('🏫 Osztály adatok', {
            'fields': ('startYear', 'szekcio'),
            'description': 'Az osztály alapvető azonosítói. A tanévhez rendelést a Tanév képernyőn kell kezelni.'
        }),
        ('👨‍🏫 Osztályfőnökök', {
            'fields': ('osztaly_fonokei',),
            'description': 'Az osztály fő- és helyettes osztályfőnökei'
        })
    )
    
    def display_osztaly(self, obj):
        return format_html('<strong style="color: #0066cc;">{}</strong>', str(obj))
    display_osztaly.short_description = 'Osztály'

    def display_tanev(self, obj):
        tanev = obj.tanev
        return str(tanev) if tanev else '-'
    display_tanev.short_description = 'Tanév'
    
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
    list_display = ['user_full_name', 'user_status', 'telefonszam', 'medias', 'display_osztaly', 'display_stab', 'admin_level', 'special_role_display', 'szerkeszto_status']
    list_filter = [
        'medias', 'osztaly', 'stab', 'radio_stab', 'admin_type', 
        'special_role', 'szerkeszto'
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
            'fields': ('admin_type', 'special_role', 'szerkeszto'),
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
    
    def szerkeszto_status(self, obj):
        if obj.szerkeszto:
            return format_html('<span style="color: green; font-weight: bold;">✏️ Igen</span>')
        return format_html('<span style="color: gray;">❌ Nem</span>')
    szerkeszto_status.short_description = 'Szerkesztő'
    
    def display_permissions(self, obj):
        perms = []
        if obj.is_admin:
            perms.append('🔑 Adminisztrátor')
        if obj.is_osztaly_fonok:
            perms.append('👨‍🏫 Osztályfőnök')
        if obj.is_production_leader:
            perms.append('🎬 Gyártásvezető')
        if obj.szerkeszto:
            perms.append('✏️ Szerkesztő')
        return format_html('<br>'.join(perms)) if perms else 'Nincs különleges jogosultság'
    display_permissions.short_description = 'Összes jogosultság'

# ============================================================================
# 🎬 GYÁRTÁS ÉS FORGATÁS (PRODUCTION MODELS)  
# ============================================================================

@admin.register(Forgatas)
class ForgatásAdmin(ImportExportModelAdmin):
    resource_class = ForgatásResource
    list_display = ['name_with_icon', 'date', 'time_display', 'forgTipus_display', 'location_display', 'equipment_count', 'szerkeszto_display', 'tanev']
    list_filter = ['forgTipus', 'date', 'tanev', 'location', 'szerkeszto']
    search_fields = ['name', 'description', 'notes', 'szerkeszto__first_name', 'szerkeszto__last_name']
    autocomplete_fields = ['location', 'contactPerson', 'relatedKaCsa', 'tanev', 'szerkeszto']
    filter_horizontal = ['equipments']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('🎬 Forgatás alapadatok', {
            'fields': ('name', 'description', 'forgTipus', 'tanev', 'szerkeszto'),
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
            'description': 'KaCsa forgatások esetében, a kapcsolódó KaCsa Összejátszás'
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

    def szerkeszto_display(self, obj):
        if obj.szerkeszto:
            return format_html('<span style="color: #7209b7;">🎤 {}</span>', obj.szerkeszto.get_full_name() or obj.szerkeszto.username)
        return '-'
    szerkeszto_display.short_description = 'Szerkesztő'
    
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

def sync_absence_records_for_beosztas(modeladmin, request, queryset):
    """
    Admin action to manually sync absence records for selected Beosztas instances.
    Useful for fixing any inconsistencies or ensuring all auto-created absences are up to date.
    """
    total_processed = 0
    total_created = 0
    total_deleted = 0
    
    for beosztas in queryset:
        if beosztas.forgatas:
            # Force update absence records (works for both draft and finalized)
            beosztas.update_absence_records()
            total_processed += 1
            
            # Count created absences for this assignment
            current_absences = Absence.objects.filter(
                forgatas=beosztas.forgatas,
                auto_generated=True
            ).count()
            total_created += current_absences
    
    if total_processed > 0:
        messages.success(
            request,
            f"✅ {total_processed} beosztás hiányzás rekordjait szinkronizáltuk. "
            f"Összesen {total_created} automatikus hiányzás rekord lett ellenőrizve/létrehozva."
        )
    else:
        messages.warning(
            request,
            "⚠️ Egy beoszstás sem volt alkalmas a szinkronizációra (szükséges: forgatas)"
        )

sync_absence_records_for_beosztas.short_description = "Hiányzás rekordok szinkronizálása"

@admin.register(Beosztas)
class BeosztasAdmin(ImportExportModelAdmin):
    resource_class = BeosztasResource
    list_display = ['beosztas_display', 'kesz_status', 'author', 'tanev', 'forgatas_link', 'stab_display', 'created_at', 'szerepkor_count', 'absence_count']
    list_filter = ['kesz', 'tanev', 'stab', 'created_at', 'author']
    search_fields = ['author__first_name', 'author__last_name', 'forgatas__name', 'stab__name']
    autocomplete_fields = ['author', 'tanev', 'forgatas', 'stab']
    filter_horizontal = ['szerepkor_relaciok']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'absence_status_info']
    actions = [sync_absence_records_for_beosztas]
    
    fieldsets = (
        ('📋 Beosztás adatok', {
            'fields': ('kesz', 'author', 'tanev', 'forgatas', 'stab'),
            'description': 'A beosztás alapvető információi'
        }),
        ('👥 Szerepkör relációk', {
            'fields': ('szerepkor_relaciok',),
            'description': 'A beosztáshoz tartozó szerepkör-felhasználó párosítások'
        }),
        ('� Automatikus hiányzások', {
            'fields': ('absence_status_info',),
            'classes': ('collapse',),
            'description': 'Az automatikusan generált hiányzás rekordok státusza'
        }),
        ('�📊 Metaadatok', {
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
    
    def stab_display(self, obj):
        if obj.stab:
            return format_html('🎬 <span style="color: #0066cc;">{}</span>', obj.stab.name)
        return '-'
    stab_display.short_description = 'Stáb'
    
    def szerepkor_count(self, obj):
        count = obj.szerepkor_relaciok.count()
        return format_html('<span style="color: blue;">👥 {} db</span>', count)
    szerepkor_count.short_description = 'Szerepkörök száma'
    
    def absence_count(self, obj):
        """Display count of auto-generated absence records for this assignment"""
        if obj.forgatas:
            count = Absence.objects.filter(
                forgatas=obj.forgatas,
                auto_generated=True
            ).count()
            if count > 0:
                return format_html('<span style="color: green;">📚 {} hiányzás</span>', count)
            else:
                return format_html('<span style="color: gray;">📚 Nincs hiányzás</span>')
        return '-'
    absence_count.short_description = 'Auto hiányzások'
    
    def absence_status_info(self, obj):
        """Detailed information about auto-generated absence records"""
        if not obj.forgatas:
            return format_html(
                '<div style="background: #ffeaa7; padding: 10px; border-radius: 5px;">'
                '<strong>⚠️ Nincs forgatás</strong><br>'
                '<small>Hiányzás rekordok csak forgatással rendelkező beosztásokhoz generálódnak</small>'
                '</div>'
            )
        
        # Show draft status info but don't prevent processing
        draft_warning = ""
        if not obj.kesz:
            draft_warning = '<div style="background: #fff3cd; padding: 5px; border-radius: 3px; margin-bottom: 5px;"><small>📝 <strong>Piszkozat:</strong> Ez a beosztás még nincs véglegesítve, de hiányzások automatikusan kezelve vannak.</small></div>'
        
        # Count absence records
        auto_absences = Absence.objects.filter(
            forgatas=obj.forgatas,
            auto_generated=True
        )
        manual_absences = Absence.objects.filter(
            forgatas=obj.forgatas,
            auto_generated=False
        )
        
        assigned_users = [relacio.user for relacio in obj.szerepkor_relaciok.all()]
        
        # Check if all assigned users have absence records
        users_with_absences = set()
        for absence in auto_absences:
            users_with_absences.add(absence.diak)
        
        missing_absences = set(assigned_users) - users_with_absences
        
        if len(missing_absences) == 0:
            status_color = "#d4edda"
            status_icon = "✅"
            status_text = "Minden beosztott felhasználónak van automatikus hiányzás rekordja"
        else:
            status_color = "#f8d7da" 
            status_icon = "⚠️"
            status_text = f"{len(missing_absences)} felhasználónak hiányzik a hiányzás rekord"
        
        return format_html(
            '{}'
            '<div style="background: {}; padding: 10px; border-radius: 5px;">'
            '<strong>{} {}</strong><br>'
            '<small>Automatikus hiányzások: {} | Kézi hiányzások: {} | Beosztott felhasználók: {}</small>'
            '{}'
            '</div>',
            draft_warning,
            status_color, status_icon, status_text,
            auto_absences.count(), manual_absences.count(), len(assigned_users),
            '<br><small style="color: red;">Hiányzó hiányzások: {}</small>'.format(
                ', '.join([user.get_full_name() for user in missing_absences])
            ) if missing_absences else ''
        )
    absence_status_info.short_description = 'Hiányzás státusz részletek'
    
    def save_model(self, request, obj, form, change):
        """Override save_model to provide feedback about absence creation"""
        super().save_model(request, obj, form, change)
        
        if obj.forgatas:
            # Count created absences (works for both draft and finalized)
            absence_count = Absence.objects.filter(
                forgatas=obj.forgatas,
                auto_generated=True
            ).count()
            
            assigned_count = obj.szerepkor_relaciok.count()
            
            status_text = "kész" if obj.kesz else "piszkozat"
            
            if absence_count > 0:
                messages.success(
                    request,
                    f"✅ Beosztás mentve ({status_text})! {absence_count} automatikus hiányzás rekord lett "
                    f"létrehozva/frissítve a {assigned_count} beosztott felhasználó számára."
                )
            else:
                if assigned_count > 0:
                    messages.warning(
                        request,
                        f"⚠️ Beosztás mentve ({status_text}), de nem lett hiányzás rekord létrehozva. "
                        f"Ellenőrizd a beosztott felhasználókat és a forgatás adatait."
                    )
                else:
                    messages.info(
                        request,
                        f"ℹ️ Beosztás mentve ({status_text}), de nincs még beosztott felhasználó."
                    )

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
        colors = {'A1': '#0066cc', 'A2': '#004e89', 'B3': '#28a745', 'B4': '#1e7e34'}
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

def validate_auto_generated_absences(modeladmin, request, queryset):
    """
    Admin action to validate that auto-generated absences are consistent with their assignments
    """
    inconsistencies = []
    validated_count = 0
    
    for absence in queryset.filter(auto_generated=True):
        # Check if there's still an assignment for this user and forgatas
        assignments = Beosztas.objects.filter(
            forgatas=absence.forgatas,
            kesz=True,
            szerepkor_relaciok__user=absence.diak
        )
        
        if not assignments.exists():
            inconsistencies.append(f"{absence.diak.get_full_name()} - {absence.forgatas.name}")
        else:
            validated_count += 1
    
    if inconsistencies:
        messages.warning(
            request,
            f"⚠️ {len(inconsistencies)} automatikus hiányzás esetében nincs megfelelő beosztás: "
            f"{', '.join(inconsistencies[:5])}"
            f"{'...' if len(inconsistencies) > 5 else ''}"
        )
    
    if validated_count > 0:
        messages.success(
            request,
            f"✅ {validated_count} automatikus hiányzás helyesen kapcsolódik beosztáshoz."
        )

validate_auto_generated_absences.short_description = "Automatikus hiányzások validálása"

@admin.register(Absence)
class AbsenceAdmin(ImportExportModelAdmin):
    resource_class = AbsenceResource
    list_display = ['absence_display', 'diak', 'forgatas_link', 'date', 'time_display', 'status_display', 'auto_generated_display', 'affected_classes']
    list_filter = ['excused', 'unexcused', 'auto_generated', 'date', 'forgatas']
    search_fields = ['diak__first_name', 'diak__last_name', 'forgatas__name']
    autocomplete_fields = ['diak', 'forgatas']
    date_hierarchy = 'date'
    actions = [validate_auto_generated_absences]
    
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

@admin.register(TavolletTipus)
class TavolletTipusAdmin(ImportExportModelAdmin):
    resource_class = TavolletTipusResource
    list_display = ['tipus_display', 'ignored_counts_as_display', 'usage_count']
    list_filter = ['ignored_counts_as']
    search_fields = ['name', 'explanation']
    
    fieldsets = (
        ('📝 Típus adatok', {
            'fields': ('name', 'explanation'),
            'description': 'A távolléti típus neve és részletes magyarázata'
        }),
        ('⚖️ Elbírálási beállítás', {
            'fields': ('ignored_counts_as',),
            'description': 'Meghatározza, hogy figyelmen kívül hagyáskor jóváhagyottnak vagy elutasítottnak számít-e'
        })
    )
    
    def tipus_display(self, obj):
        return format_html('📋 <strong>{}</strong>', obj.name)
    tipus_display.short_description = 'Típus neve'
    
    def ignored_counts_as_display(self, obj):
        if obj.ignored_counts_as == 'approved':
            return format_html('<span style="color: green; font-weight: bold;">✅ Jóváhagyott</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">❌ Elutasított</span>')
    ignored_counts_as_display.short_description = 'Figyelmen kívül hagyáskor'
    
    def usage_count(self, obj):
        count = Tavollet.objects.filter(tipus=obj).count()
        return format_html('<span style="color: blue;">🏠 {} használat</span>', count)
    usage_count.short_description = 'Használatok száma'

@admin.register(Tavollet)
class TavolletAdmin(ImportExportModelAdmin):
    resource_class = TavolletResource
    list_display = ['tavollet_display', 'user', 'tipus_display', 'date_range', 'duration_days', 'status_display']
    list_filter = ['denied', 'approved', 'tipus', 'start_date', 'end_date']
    search_fields = ['user__first_name', 'user__last_name', 'reason']
    autocomplete_fields = ['user', 'tipus']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('👤 Távollét adatok', {
            'fields': ('user', 'tipus'),
            'description': 'A távollétben lévő felhasználó és a távollét típusa'
        }),
        ('📅 Időszak', {
            'fields': ('start_date', 'end_date'),
            'description': 'A távollét kezdete és vége'
        }),
        ('📝 Indoklás és státusz', {
            'fields': ('reason', 'denied', 'approved'),
            'description': 'A távollét oka és jóváhagyási státusza'
        })
    )
    
    def tipus_display(self, obj):
        if obj.tipus:
            return format_html('<span style="color: #0066cc;">📋 {}</span>', obj.tipus.name)
        return format_html('<span style="color: #999; font-style: italic;">Nincs megadva</span>')
    tipus_display.short_description = 'Típus'
    
    def tavollet_display(self, obj):
        return format_html('🏠 <strong>Távollét #{}</strong>', obj.id)
    tavollet_display.short_description = 'Távollét'
    
    def date_range(self, obj):
        start_str = obj.start_date.strftime("%Y-%m-%d %H:%M") if obj.start_date else "N/A"
        end_str = obj.end_date.strftime("%Y-%m-%d %H:%M") if obj.end_date else "N/A"
        return f"{start_str} - {end_str}"
    date_range.short_description = 'Időszak'
    
    def duration_days(self, obj):
        if obj.start_date and obj.end_date:
            start_date = obj.start_date.date() if hasattr(obj.start_date, 'date') else obj.start_date
            end_date = obj.end_date.date() if hasattr(obj.end_date, 'date') else obj.end_date
            duration = (end_date - start_date).days + 1
            return format_html('<span style="color: blue;">📅 {} nap</span>', duration)
        return "N/A"
    duration_days.short_description = 'Időtartam'
    
    def status_display(self, obj):
        if obj.denied:
            return format_html('<span style="color: red; font-weight: bold;">❌ Elutasítva</span>')
        elif obj.approved:
            return format_html('<span style="color: green; font-weight: bold;">✅ Jóváhagyva</span>')
        else:
            return format_html('<span style="color: orange; font-weight: bold;">⏳ Függőben</span>')
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
class AtigazolasAdmin(admin.ModelAdmin):
    list_display = ['profile', 'previous_stab', 'previous_radio_stab', 'new_stab', 'new_radio_stab', 'datetime']
    search_fields = ['profile__user__username', 'profile__user__first_name', 'profile__user__last_name', 'previous_stab', 'new_stab', 'previous_radio_stab', 'new_radio_stab']
    list_filter = ['previous_stab', 'new_stab', 'previous_radio_stab', 'new_radio_stab', 'datetime']

# Register SystemMessage model
@admin.register(SystemMessage)
class SystemMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_severity_display', 'get_messageType_display', 'showFrom', 'showTo', 'is_currently_active', 'created_at', 'updated_at']
    list_filter = ['severity', 'messageType', 'showFrom', 'showTo', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'showFrom'
    
    fieldsets = (
        ('📢 Rendszerüzenet adatok', {
            'fields': ('title', 'message'),
            'description': 'A rendszerüzenet címe és tartalma'
        }),
        ('🏷️ Kategorizálás', {
            'fields': ('severity', 'messageType'),
            'description': 'Az üzenet súlyossága és célközönsége'
        }),
        ('⏰ Megjelenítési időszak', {
            'fields': ('showFrom', 'showTo'),
            'description': 'Az üzenet mikor legyen látható a felhasználók számára'
        }),
        ('📊 Metaadatok', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_currently_active(self, obj):
        """Show if message is currently active"""
        if obj.is_active():
            return format_html('<span style="color: green; font-weight: bold;">✅ Aktív</span>')
        return format_html('<span style="color: gray; font-weight: bold;">❌ Inaktív</span>')
    is_currently_active.short_description = 'Jelenleg aktív'
    
    def get_severity_display(self, obj):
        """Display severity with color coding"""
        severity_colors = {
            'info': '#17a2b8',      # Blue
            'warning': '#ffc107',   # Yellow
            'error': '#dc3545'      # Red
        }
        severity_icons = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌'
        }
        color = severity_colors.get(obj.severity, '#6c757d')
        icon = severity_icons.get(obj.severity, '📝')
        display_name = obj.get_severity_display()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, display_name
        )
    get_severity_display.short_description = 'Súlyosság'
    
    def get_messageType_display(self, obj):
        """Display message type with icons"""
        type_icons = {
            'user': '👤',
            'developer': '👨‍💻',
            'operator': '⚙️',
            'support': '🛠️'
        }
        icon = type_icons.get(obj.messageType, '📝')
        display_name = obj.get_messageType_display()
        return format_html('{} {}', icon, display_name)
    get_messageType_display.short_description = 'Üzenet típusa'