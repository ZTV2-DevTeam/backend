from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, date, timedelta, time
from django.db.models.signals import m2m_changed, pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password

# ============================================================================
# Utility Functions for Timezone Handling
# ============================================================================

def convert_to_local_naive_datetime(dt):
    """
    Convert a timezone-aware datetime to Europe/Budapest local time and make it naive.
    This is needed because USE_TZ=False and SQLite doesn't support timezone-aware datetimes.
    
    Args:
        dt: datetime object (timezone-aware or naive)
        
    Returns:
        naive datetime in Europe/Budapest timezone
    """
    if dt is None:
        return None
    
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        # Convert timezone-aware datetime to Europe/Budapest, then make naive
        from zoneinfo import ZoneInfo
        budapest_tz = ZoneInfo('Europe/Budapest')
        return dt.astimezone(budapest_tz).replace(tzinfo=None)
    
    # Already naive - assume it's in local time
    return dt

# ============================================================================
# USER MODEL CUSTOMIZATION
# ============================================================================

# Monkey patch Django's User model to change get_full_name format
def get_full_name_flipped(self):
    """
    Return the last_name + ', ' + first_name, with a space in between.
    If either name is missing, return the available name.
    If both are missing, return empty string.
    """
    if self.last_name and self.first_name:
        return f"{self.last_name} {self.first_name}"
    elif self.last_name:
        return self.last_name
    elif self.first_name:
        return self.first_name
    else:
        return ""

# Apply the monkey patch
User.get_full_name = get_full_name_flipped

# ============================================================================
# SIGNAL HANDLERS FOR USER PASSWORD MANAGEMENT
# ============================================================================

@receiver(pre_save, sender=User)
def hash_unhashed_password(sender, instance, **kwargs):
    """
    Automatically hash unhashed passwords when User is saved.
    Only hashes passwords that are not already hashed.
    """
    # Skip if no password is set
    if not instance.password:
        return
    
    # Check if password is already hashed (Django hash formats)
    if instance.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$', 'scrypt$')):
        return
    
    # Check if this is actually a password change
    try:
        if instance.pk:
            # Get the current instance from database
            old_instance = User.objects.get(pk=instance.pk)
            # If password hasn't changed, don't rehash
            if old_instance.password == instance.password:
                return
    except User.DoesNotExist:
        # New user, proceed with hashing
        pass
    
    # Hash the plain text password
    original_password = instance.password
    instance.password = make_password(instance.password)
    print(f"🔐 Password auto-hashed for user: {instance.username} (was: {original_password[:10]}...)")

# ============================================================================
# MODEL DEFINITIONS
# ============================================================================

# Create your models here.


class Tanev(models.Model):
    """
    Tanév modell: csak a kezdő és záró dátumot tároljuk.
    """
    start_date = models.DateField(verbose_name='Kezdő dátum', help_text='A tanév kezdő dátuma (pl. 2024-09-01)')
    end_date = models.DateField(verbose_name='Záró dátum', help_text='A tanév záró dátuma (pl. 2025-06-13)')
    osztalyok = models.ManyToManyField('Osztaly', blank=True, related_name='tanevek', verbose_name='Osztályok',
                                       help_text='A tanévhez tartozó osztályok')

    class Meta:
        verbose_name = "Tanév"
        verbose_name_plural = "Tanévek"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.start_date.year}/{self.end_date.year}"

    @property
    def start_year(self):
        return self.start_date.year

    @property
    def end_year(self):
        return self.end_date.year

    @classmethod
    def get_current_by_date(cls, check_date=None):
        """Visszaadja azt a tanévet, amelyik tartalmazza a megadott dátumot (alapból ma)."""
        if check_date is None:
            check_date = date.today()
        return cls.objects.filter(start_date__lte=check_date, end_date__gte=check_date).first()

    @classmethod
    def get_active(cls):
        """Az aktuális tanév (a mai dátum alapján)."""
        return cls.get_current_by_date()

    @classmethod
    def create_for_year(cls, start_year):
        """
        Létrehoz egy tanévet a megadott kezdő évvel (szeptember 1-től következő év június 15-ig).
        """
        start_date = date(start_year, 9, 1)
        end_date = date(start_year + 1, 6, 15)
        return cls.objects.create(start_date=start_date, end_date=end_date)
    
    def add_osztaly(self, osztaly):
        """Hozzáad egy osztályt a tanévhez"""
        self.osztalyok.add(osztaly)
    
    def remove_osztaly(self, osztaly):
        """Eltávolít egy osztályt a tanévből"""
        self.osztalyok.remove(osztaly)
    
    def get_active_osztalyok(self):
        """Visszaadja a tanévhez tartozó összes osztályt"""
        return self.osztalyok.all()
    
    def get_osztalyok_by_szekcio(self, szekcio):
        """Visszaadja a tanévhez tartozó osztályokat szekció szerint"""
        return self.osztalyok.filter(szekcio=szekcio)


class Profile(models.Model):
    ADMIN_TYPES = [
        ('none', 'Nincs adminisztrátor jogosultság'),
        ('developer', 'Administrator-Developer'),
        ('teacher', 'Administrator-Teacher (Médiatanár)'),
        ('system_admin', 'Rendszeradminisztrátor'),
    ]
    
    SPECIAL_ROLES = [
        ('none', 'Nincs különleges szerep'),
        ('production_leader', 'Gyártásvezető'),
    ]
    
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, verbose_name='Felhasználó', 
                                  help_text='A profilhoz tartozó felhasználói fiók')
    telefonszam = models.CharField(max_length=20, blank=True, null=True, verbose_name='Telefonszám', 
                                   help_text='A felhasználó telefonszáma')
    medias = models.BooleanField(default=True, verbose_name='Médiás-e?', 
                                help_text='Jelöli, hogy a felhasználó médiás-e')
    stab = models.ForeignKey('Stab', related_name='tagok', on_delete=models.PROTECT, blank=True, null=True, 
                            verbose_name='Stáb', help_text='A felhasználó stábja')
    radio_stab = models.ForeignKey('RadioStab', related_name='tagok', on_delete=models.PROTECT, blank=True, null=True, 
                                  verbose_name='Rádiós stáb', help_text='A felhasználó rádiós stábja (9F diákok számára)')
    osztaly = models.ForeignKey('Osztaly', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Osztály', 
                               help_text='A felhasználó osztálya')
    admin_type = models.CharField(max_length=20, choices=ADMIN_TYPES, default='none', verbose_name='Adminisztrátor típus',
                                 help_text='A felhasználó adminisztrátori jogosultságainak típusa')
    special_role = models.CharField(max_length=20, choices=SPECIAL_ROLES, default='none', verbose_name='Különleges szerep',
                                   help_text='A felhasználó különleges szerepe a rendszerben')
    szerkeszto = models.BooleanField(default=False, verbose_name='Szerkesztő', 
                                   help_text='Jelöli, hogy a felhasználó kiírhat-e forgatásokat')

    class Meta:
        verbose_name = 'Profil'
        verbose_name_plural = 'Profilok'

    def save(self, *args, **kwargs):
        creating = self.pk is None
        previous_stab = None
        previous_radio_stab = None
        if not creating:
            old = Profile.objects.get(pk=self.pk)
            previous_stab = old.stab.name if old.stab else None
            previous_radio_stab = old.radio_stab.name if old.radio_stab else None
        super().save(*args, **kwargs)
        if not creating:
            new_stab = self.stab.name if self.stab else None
            new_radio_stab = self.radio_stab.name if self.radio_stab else None
            stab_changed = previous_stab != new_stab and previous_stab is not None
            radio_stab_changed = previous_radio_stab != new_radio_stab and previous_radio_stab is not None
            if stab_changed or radio_stab_changed:
                from api.models import Atigazolas
                Atigazolas.objects.create(
                    profile=self,
                    previous_stab=previous_stab if stab_changed else None,
                    previous_radio_stab=previous_radio_stab if radio_stab_changed else None,
                    new_stab=new_stab if stab_changed else None,
                    new_radio_stab=new_radio_stab if radio_stab_changed else None
                )

    def __str__(self):
        return self.user.get_full_name()
    
    @property
    def is_admin(self):
        """Check if user has any admin permissions"""
        return self.admin_type != 'none'
    
    @property
    def is_developer_admin(self):
        """Check if user is a developer admin"""
        return self.admin_type == 'developer'
    
    @property
    def is_teacher_admin(self):
        """Check if user is a teacher admin (Médiatanár)"""
        return self.admin_type == 'teacher'
    
    @property
    def is_system_admin(self):
        """Check if user is a system admin (Rendszeradminisztrátor)"""
        return self.admin_type == 'system_admin'
    
    @property
    def is_production_leader(self):
        """Check if user is a production leader (Gyártásvezető)"""
        return self.special_role == 'production_leader'
    
    @property
    def can_create_forgatas(self):
        """Check if user can create new forgatások (filming sessions)"""
        # Check if user is in current 10F class
        if self.is_current_10f_student():
            return True
        
        # Check if user is production leader
        if self.is_production_leader:
            return True
        
        # Check if user has editor permission
        if self.szerkeszto:
            return True
        
        # Check if user has any admin permissions
        if self.is_admin:
            return True
        
        return False
    
    def is_current_10f_student(self):
        """Check if user is currently in 10F class"""
        if not self.osztaly or self.osztaly.szekcio.upper() != 'F':
            return False
        
        current_year = datetime.now().year
        elso_felev = datetime.now().month >= 9
        
        year_diff = current_year - self.osztaly.startYear 
        year_diff += 8 if elso_felev else 7
        return year_diff == 10  # 10F class
    
    @property
    def is_osztaly_fonok(self):
        """Check if user is assigned to any class as osztályfőnök (class teacher)"""
        # Check if the user is assigned to any class as a teacher
        try:
            from api.models import Osztaly
            return Osztaly.objects.filter(osztaly_fonokei=self.user).exists()
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error in is_osztaly_fonok: {e}")
            return False
    
    @property 
    def osztalyfonok(self):
        """Backward compatibility property - returns same as is_osztaly_fonok"""
        return self.is_osztaly_fonok
    
    def get_owned_osztalyok(self):
        """Get all classes where this user is assigned as class teacher"""
        return Osztaly.objects.filter(osztaly_fonokei=self.user)
    
    def has_admin_permission(self, permission_type):
        """
        Check if user has specific admin permission
        permission_type can be: 'developer', 'teacher', 'system_admin', 'any'
        """
        if permission_type == 'any':
            return self.is_admin
        elif permission_type == 'developer':
            return self.is_developer_admin
        elif permission_type == 'teacher':
            return self.is_teacher_admin
        elif permission_type == 'system_admin':
            return self.is_system_admin
        return False
    
    @property
    def is_second_year_radio_student(self):
        """Check if this is a second year student (9F) who has a radio stab assignment"""
        if not self.osztaly or not self.radio_stab:
            return False
        
        current_year = datetime.now().year
        elso_felev = datetime.now().month >= 9
        
        if self.osztaly.szekcio.upper() == 'F':
            year_diff = current_year - self.osztaly.startYear 
            year_diff += 8 if elso_felev else 7
            return year_diff == 9  # 9F class with radio stab assignment
        return False
    
    def is_available_for_datetime(self, start_datetime, end_datetime):
        """
        Check if user is available during given datetime range
        Considers both regular absences (Tavollet) and radio sessions
        """
        from datetime import datetime, date
        
        # Ensure we have datetime objects
        if isinstance(start_datetime, date) and not isinstance(start_datetime, datetime):
            start_datetime = datetime.combine(start_datetime, datetime.min.time())
        if isinstance(end_datetime, date) and not isinstance(end_datetime, datetime):
            end_datetime = datetime.combine(end_datetime, datetime.max.time())
        
        # Convert to local naive datetimes for SQLite compatibility
        start_datetime = convert_to_local_naive_datetime(start_datetime)
        end_datetime = convert_to_local_naive_datetime(end_datetime)
        
        # Check if user has marked absence during this period
        # Now using datetime comparison for more precise overlaps
        absence_overlap = Tavollet.objects.filter(
            user=self.user,
            start_date__lt=end_datetime,
            end_date__gt=start_datetime,
            denied=False
        ).exists()
        
        if absence_overlap:
            return False
        
        # If this is a second year radio student, check for radio sessions
        if self.is_second_year_radio_student:
            # Extract date components for radio session filtering
            start_date = start_datetime.date() if hasattr(start_datetime, 'date') else start_datetime
            end_date = end_datetime.date() if hasattr(end_datetime, 'date') else end_datetime
            
            radio_session_overlap = RadioSession.objects.filter(
                participants=self.user
            ).filter(
                date__gte=start_date,
                date__lte=end_date
            )
            
            for session in radio_session_overlap:
                if session.overlaps_with_datetime(start_datetime, end_datetime):
                    return False
        
        return True
    
    def get_radio_sessions_for_period(self, start_date, end_date):
        """Get all radio sessions for this user in a given period"""
        if not self.is_second_year_radio_student:
            return RadioSession.objects.none()
        
        return RadioSession.objects.filter(
            participants=self.user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date', 'time_from')

class Atigazolas(models.Model):
    # Atigazolas records get automatically generated via saving the Profile and stores, whether the Stáb or Rádiós stáb fields got changed and if they did, it keeps track of the previous values. Does not apply for null -> data
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='atigazolasok')
    previous_stab = models.CharField(max_length=100, blank=True, null=True)
    previous_radio_stab = models.CharField(max_length=100, blank=True, null=True)
    new_stab = models.CharField(max_length=100, blank=True, null=True)
    new_radio_stab = models.CharField(max_length=100, blank=True, null=True)
    datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Átigazolas'
        verbose_name_plural = 'Átigazolasok'

    def __str__(self):
        return f'Átigazolas: {self.profile} - {self.datetime}'

class Osztaly(models.Model):
    startYear = models.IntegerField(blank=False, null=False, verbose_name='Indulási év', 
                                   help_text='Az év, amikor az osztály első alkalommal megkezdte tanulmányait')
    szekcio = models.CharField(max_length=1, blank=False, null=False, verbose_name='Szekció', 
                              help_text='Az osztály szekciója (pl. F, A, B, stb.)')
    tanev = models.ForeignKey('Tanev', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Tanév', 
                              help_text='Az a tanév, amikor ez az osztály aktív volt/lesz')
    osztaly_fonokei = models.ManyToManyField('auth.User', blank=True, related_name='osztaly_fonokei', 
                                           verbose_name='Osztályfőnökei', 
                                           help_text='Az osztályfőnök és helyettese')

    def __str__(self):
        current_year = datetime.now().year
        month = datetime.now().month
        szekcio = self.szekcio.upper()
        if szekcio == 'F':
            if self.startYear == current_year and month < 9:
                return 'NYF'
            year_diff = current_year - self.startYear + (9 if month >= 9 else 8) - 1
            return 'NYF' if year_diff <= 8 else f'{year_diff}F'
        return f'{str(self.startYear)[:-2]}{szekcio}'
    
    def get_current_year_name(self, reference_tanev=None):
        """Get the class name for a specific school year"""
        if reference_tanev is None:
            reference_tanev = Tanev.get_active()
        
        if not reference_tanev:
            return str(self)  # Fallback to original logic
        
        if self.szekcio.upper() == 'F':
            year_diff = reference_tanev.start_year - self.startYear + 7
            if year_diff < 8:
                return 'Bejövő NYF'
            return f'{year_diff}F'
        return f'{self.startYear[:-2]}{self.szekcio.upper()}'
    
    def get_osztaly_fonokei(self):
        """Get all users assigned as class teachers for this class"""
        return self.osztaly_fonokei.all()
    
    def get_fo_osztaly_fonok(self):
        """Get the main class teacher (first one added, could be customized later)"""
        return self.osztaly_fonokei.first()
    
    def add_osztaly_fonok(self, user):
        """Add a user as class teacher to this class"""
        self.osztaly_fonokei.add(user)
        # User is now assigned as class teacher via the ManyToMany relationship
        # The is_osztaly_fonok property will calculate this automatically
        pass
    
    def remove_osztaly_fonok(self, user):
        """Remove a user as class teacher from this class"""
        self.osztaly_fonokei.remove(user)
        # User is no longer class teacher of this specific class
        # The is_osztaly_fonok property will automatically reflect this change
        pass
    
    def is_user_osztaly_fonok(self, user):
        """Check if a user is class teacher of this class"""
        return self.osztaly_fonokei.filter(id=user.id).exists()
    
    class Meta:
        verbose_name = "Osztály"
        verbose_name_plural = "Osztályok"
        ordering = ['startYear', 'szekcio']
            
class Stab(models.Model):
    name = models.CharField(max_length=50, unique=True, blank=False, null=False, verbose_name='Stáb neve', 
                           help_text='A stáb egyedi neve')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Stáb"
        verbose_name_plural = "Stábok"
        ordering = ['name']

class RadioStab(models.Model):
    """
    Rádiós stábok kezelése másodéves (9F) diákok számára
    A1, A2, B3, B4 csapatok
    """
    RADIO_TEAMS = [
        ('A1', 'A1 rádió csapat'),
        ('A2', 'A2 rádió csapat'),  
        ('B3', 'B3 rádió csapat'),
        ('B4', 'B4 rádió csapat'),
    ]
    
    name = models.CharField(max_length=50, blank=False, null=False, verbose_name='Stáb név',
                           help_text='A rádiós stáb neve')
    team_code = models.CharField(max_length=2, choices=RADIO_TEAMS, unique=True, verbose_name='Csapat kód',
                                help_text='A rádiós csapat egyedi kódja (A1, A2, B3, B4)')
    description = models.TextField(max_length=300, blank=True, null=True, verbose_name='Leírás',
                                  help_text='A rádiós stáb részletes leírása (maximum 300 karakter)')
    
    def __str__(self):
        return f"{self.name} ({self.team_code})"
    
    def get_members(self):
        """Get all profiles assigned to this radio stab"""
        return self.tagok.filter(
            osztaly__szekcio='F',
            radio_stab=self
        ).select_related('user', 'osztaly')
    
    def get_active_sessions(self, start_date=None, end_date=None):
        """Get all radio sessions for this stab in a given period"""
        sessions = RadioSession.objects.filter(radio_stab=self)
        if start_date:
            sessions = sessions.filter(date__gte=start_date)
        if end_date:
            sessions = sessions.filter(date__lte=end_date)
        return sessions.order_by('date', 'time_from')
    
    class Meta:
        verbose_name = "Rádiós Stáb"
        verbose_name_plural = "Rádiós Stábok"
        ordering = ['team_code']
            
class Partner(models.Model):
    name = models.CharField(max_length=150, unique=True, blank=False, null=False, verbose_name='Partner neve', 
                           help_text='A partner szervezet vagy intézmény neve')
    address = models.CharField(max_length=500, blank=True, null=True, verbose_name='Cím', 
                              help_text='A partner szervezet címe (maximum 500 karakter)')

    # intezmeny_tipusok = [
    #     ('iskola', 'Iskola'),
    #     ('kutatóintézet', 'Kutatóintézet'),
    #     ('kozossegi_haz', 'Közösségi Ház'),
    #     ('kulturalis_kozpont', 'Kulturális Központ'),
    #     ('muzeum', 'Múzeum'),
    #     ('konyvtar', 'Könyvtár'),
    #     ('egyesulet', 'Egyesület'),
    #     ('vallalat', 'Vállalat'),
    #     ('onkormanyzat', 'Önkormányzat'),
    #     ('egyeb', 'Egyéb'),
    # ]

    institution = models.ForeignKey('PartnerTipus', on_delete=models.PROTECT, related_name='partners', blank=True, null=True, 
                                   verbose_name='Intézmény típusa', help_text='A partner intézmény típusa')
    imgUrl = models.URLField(max_length=1000, blank=True, null=True, verbose_name='Kép URL', 
                            help_text='A partnerhez tartozó kép webcíme (opcionális, maximum 1000 karakter)')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Partner"
        verbose_name_plural = "Partnerek"
        ordering = ['name']

class PartnerTipus(models.Model):
    name = models.CharField(max_length=150, unique=True, blank=False, null=False, verbose_name='Típus neve', 
                           help_text='A partner típus neve (pl. Iskola, Múzeum, Vállalat, stb.)')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Partner Típus"
        verbose_name_plural = "Partner Típusok"

class Config(models.Model):
    active = models.BooleanField(default=False, verbose_name='Aktív', 
                                help_text='Jelöli, hogy a rendszer aktív-e')

    allowEmails = models.BooleanField(default=False, verbose_name='E-mailek engedélyezése', 
                                     help_text='Jelöli, hogy a rendszer küldhet-e e-maileket')

    def __str__(self):
        return f'active: {self.active}'
    
    class Meta:
        verbose_name = "Konfiguráció"
        verbose_name_plural = "Konfigurációk"

class Forgatas(models.Model):
    name = models.CharField(max_length=150, blank=False, null=False, verbose_name='Forgatás neve', 
                           help_text='A forgatás egyedi neve')
    description = models.TextField(max_length=500, blank=False, null=False, verbose_name='Leírás', 
                                  help_text='A forgatás részletes leírása (maximum 500 karakter)')
    date = models.DateField(blank=False, null=False, verbose_name='Dátum', 
                           help_text='A forgatás dátuma')
    timeFrom = models.TimeField(blank=False, null=False, verbose_name='Kezdés ideje', 
                               help_text='A forgatás kezdési időpontja')
    timeTo = models.TimeField(blank=False, null=False, verbose_name='Befejezés ideje', 
                             help_text='A forgatás befejezésének időpontja')
    location = models.ForeignKey('Partner', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Helyszín', 
                                help_text='A forgatás helyszíne (partnerintézmény)')
    szerkeszto = models.ForeignKey('auth.User', null=True, blank=True, verbose_name='Szerkesztő', help_text='A forgatás szerkesztője', on_delete=models.PROTECT)
    contactPerson = models.ForeignKey('ContactPerson', on_delete=models.PROTECT, blank=True, null=True, 
                                     verbose_name='Kapcsolattartó', help_text='A forgatáshoz tartozó kapcsolattartó személy')
    notes = models.TextField(max_length=500, blank=True, null=True, verbose_name='Megjegyzések', 
                            help_text='További megjegyzések a forgatáshoz (maximum 500 karakter)')
    tanev = models.ForeignKey('Tanev', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Tanév',
                              help_text='A forgatás tanéve (automatikusan meghatározva a dátum alapján)')

    tipusok = [
        ('kacsa', 'KaCsa'),
        ('rendes', 'Rendes'),
        ('rendezveny', 'Rendezvény'),
        ('egyeb', 'Egyéb'),
    ]

    forgTipus = models.CharField(max_length=150, choices=tipusok, blank=False, null=False, verbose_name='Forgatás típusa', 
                                help_text='A forgatás típusának kategóriája')

    relatedKaCsa = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True, related_name='related_forgatas', 
                                    limit_choices_to={'forgTipus': 'kacsa'}, verbose_name='Kapcsolódó KaCsa', 
                                    help_text='A forgatáshoz kapcsolódó KaCsa típusú forgatás')
    equipments = models.ManyToManyField('Equipment', blank=True, related_name='forgatasok', verbose_name='Felszerelések', 
                                       help_text='A forgatáshoz szükséges felszerelések')

    def __str__(self):
        return f'{self.name} ({self.date})'
    
    def save(self, *args, **kwargs):
        # Store old values for comparison if updating
        old_date = None
        old_timeFrom = None
        old_timeTo = None
        if self.pk:
            try:
                old_forgatas = Forgatas.objects.get(pk=self.pk)
                old_date = old_forgatas.date
                old_timeFrom = old_forgatas.timeFrom
                old_timeTo = old_forgatas.timeTo
            except Forgatas.DoesNotExist:
                pass
        
        # Auto-assign school year based on date
        if not self.tanev and self.date:
            self.tanev = Tanev.get_current_by_date(self.date)
        
        super().save(*args, **kwargs)
        
        # Update related absence records if timing changed
        if old_date is not None and (
            old_date != self.date or 
            old_timeFrom != self.timeFrom or 
            old_timeTo != self.timeTo
        ):
            self.update_related_absences()
    
    def update_related_absences(self):
        """Update all absence records related to this forgatas when timing changes"""
        Absence.objects.filter(forgatas=self).update(
            date=self.date,
            timeFrom=self.timeFrom,
            timeTo=self.timeTo
        )
    
    class Meta:
        verbose_name = "Forgatás"
        verbose_name_plural = "Forgatások"
        ordering = ['date', 'timeFrom']

class Absence(models.Model):
    diak = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='Diák', 
                            help_text='A hiányzó diák')
    forgatas = models.ForeignKey('Forgatas', on_delete=models.CASCADE, verbose_name='Forgatás', 
                                help_text='A forgatás, ami miatt hiányzik')
    date = models.DateField(verbose_name='Dátum', help_text='A hiányzás dátuma')
    timeFrom = models.TimeField(verbose_name='Kezdés ideje', help_text='A hiányzás kezdési időpontja')
    timeTo = models.TimeField(verbose_name='Befejezés ideje', help_text='A hiányzás befejezési időpontja')
    excused = models.BooleanField(default=False, verbose_name='Igazolt', 
                                 help_text='Jelöli, hogy a hiányzás igazolt-e')
    unexcused = models.BooleanField(default=False, verbose_name='Igazolatlan', 
                                   help_text='Jelöli, hogy a hiányzás igazolatlan-e')
    auto_generated = models.BooleanField(default=True, verbose_name='Automatikusan generált',
                                        help_text='Jelöli, hogy ez a hiányzás automatikusan lett-e létrehozva beosztás alapján. Ha ez a mező hamis, az azt jelenti, hogy a hiányzást egy diák kézi kiegészítése.')
    
    # Student-submitted extra time fields
    student_extra_time_before = models.IntegerField(default=0, verbose_name='Diák által beküldött extra idő előtte (perc)',
                                                   help_text='A diák által megadott extra idő percben a forgatás előtt')
    student_extra_time_after = models.IntegerField(default=0, verbose_name='Diák által beküldött extra idő utána (perc)',
                                                  help_text='A diák által megadott extra idő percben a forgatás után')
    student_edited = models.BooleanField(default=False, verbose_name='Diák által szerkesztett',
                                        help_text='Jelöli, hogy a diák módosította-e a hiányzás adatait')
    student_edit_timestamp = models.DateTimeField(null=True, blank=True, verbose_name='Diák szerkesztés időpontja',
                                                 help_text='Mikor módosította a diák utoljára a hiányzást')
    student_edit_note = models.TextField(max_length=500, blank=True, null=True, verbose_name='Diák megjegyzés',
                                        help_text='A diák által megadott indoklás az extra időre (maximum 500 karakter)')

    # Érintett tanórák kiszámítása
    # Csengetési rend:
    # 0. óra - 7:30-8:15
    # 1. óra - 8:25-9:10
    # 2. óra - 9:20-10:05
    # 3. óra - 10:20-11:05
    # 4. óra - 11:15-12:00
    # 5. óra - 12:20-13:05
    # 6. óra - 13:25-14:10
    # 7. óra - 14:20-15:05
    # 8. óra - 15:15-16:00
    # Dict, amiben a tanórák sorszáma van, amelyekbe belelóg a forgatás

    affected_classes = {
        0: (time(7, 30), time(8, 15)),
        1: (time(8, 25), time(9, 10)),
        2: (time(9, 20), time(10, 5)),
        3: (time(10, 20), time(11, 5)),
        4: (time(11, 15), time(12, 0)),
        5: (time(12, 20), time(13, 5)),
        6: (time(13, 25), time(14, 10)),
        7: (time(14, 20), time(15, 5)),
        8: (time(15, 15), time(16, 0)),
    }

    def get_affected_classes(self):
        affected = []
        # Check if timeFrom and timeTo are not None to avoid TypeError
        if self.timeFrom is None or self.timeTo is None:
            return affected
        
        for hour, (start, end) in self.affected_classes.items():
            if start < self.timeTo and end > self.timeFrom:
                affected.append(hour)
        return affected
    
    def get_effective_time_from(self):
        """Get the effective start time including student's extra time before."""
        if self.student_extra_time_before > 0:
            from datetime import datetime, timedelta
            base_datetime = datetime.combine(self.date, self.timeFrom)
            adjusted_datetime = base_datetime - timedelta(minutes=self.student_extra_time_before)
            return adjusted_datetime.time()
        return self.timeFrom
    
    def get_effective_time_to(self):
        """Get the effective end time including student's extra time after."""
        if self.student_extra_time_after > 0:
            from datetime import datetime, timedelta
            base_datetime = datetime.combine(self.date, self.timeTo)
            adjusted_datetime = base_datetime + timedelta(minutes=self.student_extra_time_after)
            return adjusted_datetime.time()
        return self.timeTo
    
    def get_affected_classes_with_student_time(self):
        """Get affected classes including student's extra time."""
        affected = []
        effective_start = self.get_effective_time_from()
        effective_end = self.get_effective_time_to()
        
        # Check if times are not None to avoid TypeError
        if effective_start is None or effective_end is None:
            return affected
        
        for hour, (start, end) in self.affected_classes.items():
            if start < effective_end and end > effective_start:
                affected.append(hour)
        return affected

    class Meta:
        verbose_name = "Hiányzás"
        verbose_name_plural = "Hiányzások"

    def __str__(self):
        return f'{self.diak.get_full_name()} - {self.date} ({self.timeFrom} - {self.timeTo})'

class EquipmentTipus(models.Model):
    name = models.CharField(max_length=150, unique=True, blank=False, null=False, verbose_name='Típus neve', 
                           help_text='Az eszköz típusának neve')
    emoji = models.CharField(max_length=10, blank=True, null=True, verbose_name='Emoji', 
                            help_text='Az eszköz típushoz tartozó emoji ikon (opcionális)')

    def __str__(self):
        return f'{self.name} ({self.emoji})'
    
    class Meta:
        verbose_name = "Eszköz Típus"
        verbose_name_plural = "Eszköz Típusok"

class Equipment(models.Model):
    nickname = models.CharField(max_length=150, blank=False, null=False, verbose_name='Becenév', 
                               help_text='Az eszköz egyedi beceneve (azonosításhoz)')
    brand = models.CharField(max_length=150, blank=True, null=True, verbose_name='Márka', 
                            help_text='Az eszköz gyártójának neve')
    model = models.CharField(max_length=150, blank=True, null=True, verbose_name='Modell', 
                            help_text='Az eszköz modell neve vagy száma')
    serialNumber = models.CharField(max_length=150, unique=True, blank=True, null=True, verbose_name='Sorozatszám', 
                                   help_text='Az eszköz gyári sorozatszáma (egyedi)')
    equipmentType = models.ForeignKey('EquipmentTipus', on_delete=models.PROTECT, related_name='equipments', blank=True, null=True, 
                                     verbose_name='Eszköz típusa', help_text='Az eszköz kategóriája')
    functional = models.BooleanField(default=True, verbose_name='Működőképes', 
                                    help_text='Jelöli, hogy az eszköz használható állapotban van-e')
    notes = models.TextField(max_length=500, blank=True, null=True, verbose_name='Megjegyzések', 
                            help_text='További információk az eszközről (maximum 500 karakter)')

    def __str__(self):
        return f'{self.nickname} ({self.brand} {self.model})'
    
    class Meta:
        verbose_name = "Felszerelés"
        verbose_name_plural = "Felszerelések"
        ordering = ['nickname']

    def is_available_for(self, start_date, start_time, end_date, end_time):
        """Check if equipment is available during the specified time period"""
        from datetime import datetime
        
        # If equipment is not functional, it's not available
        if not self.functional:
            return False
            
        # Find overlapping filming sessions
        overlapping_sessions = self.forgatasok.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        for session in overlapping_sessions:
            # Check for time overlap on the same date
            if session.date == start_date == end_date:
                # Same day - check time overlap
                if (session.timeFrom < end_time and session.timeTo > start_time):
                    return False
            elif session.date == start_date:
                # Start date - check if session ends after our start time
                if session.timeTo > start_time:
                    return False
            elif session.date == end_date:
                # End date - check if session starts before our end time
                if session.timeFrom < end_time:
                    return False
            elif start_date < session.date < end_date:
                # Session is completely within our date range
                return False
                
        return True
    
    def get_bookings_for_period(self, start_date, end_date=None):
        """Get all filming sessions where this equipment is booked for a given period"""
        if end_date is None:
            end_date = start_date
            
        return self.forgatasok.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date', 'timeFrom')
    
    def get_availability_schedule(self, start_date, end_date):
        """Get detailed availability schedule for a date range"""
        schedule = []
        bookings = self.get_bookings_for_period(start_date, end_date)
        
        for booking in bookings:
            schedule.append({
                'date': booking.date,
                'time_from': booking.timeFrom,
                'time_to': booking.timeTo,
                'forgatas_name': booking.name,
                'forgatas_id': booking.id,
                'forgatas_type': booking.forgTipus,
                'location': booking.location.name if booking.location else None,
                'available': False
            })
            
        return schedule

class ContactPerson(models.Model):
    name = models.CharField(max_length=150, blank=False, null=False, verbose_name='Név', 
                           help_text='A kapcsolattartó személy teljes neve')
    email = models.EmailField(max_length=254, blank=True, null=True, verbose_name='E-mail cím', 
                             help_text='A kapcsolattartó e-mail címe (opcionális)')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Telefonszám', 
                            help_text='A kapcsolattartó telefonszáma (opcionális)')
    context = models.CharField(max_length=100, blank=True, null=True, verbose_name='Kontextus', 
                              help_text='Rövid azonosító információ (pl. intézmény + szerepkör, maximum 100 karakter)')
    
    def __str__(self):
        if self.context:
            return f"{self.name} ({self.context})"
        return self.name

    class Meta:
        verbose_name = "Kapcsolattartó"
        verbose_name_plural = "Kapcsolattartók"

class Announcement(models.Model):
    author = models.ForeignKey('auth.user', related_name='announcements', on_delete=models.PROTECT, blank=True, null=True, 
                              verbose_name='Szerző', help_text='A közlemény szerzője')
    title = models.CharField(max_length=200, blank=False, null=False, verbose_name='Cím', 
                            help_text='A közlemény címe (maximum 200 karakter)')
    body = models.TextField(max_length=5000, blank=False, null=False, verbose_name='Tartalom', 
                           help_text='A közlemény tartalma (maximum 5000 karakter)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Létrehozva', 
                                     help_text='A közlemény létrehozásának időpontja')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Módosítva', 
                                     help_text='A közlemény utolsó módosításának időpontja')
    cimzettek = models.ManyToManyField('auth.User', related_name='uzenetek', blank=True, verbose_name='Címzettek', 
                                      help_text='A közlemény címzettjei')

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Közlemény"
        verbose_name_plural = "Közlemények"
        ordering = ['-created_at']

class Tavollet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Felhasználó', 
                            help_text='A távollétét jelző felhasználó')
    start_date = models.DateTimeField(blank=False, null=False, verbose_name='Kezdő időpont', 
                                     help_text='A távollét kezdő időpontja (dátum és idő)')
    end_date = models.DateTimeField(blank=False, null=False, verbose_name='Záró időpont', 
                                   help_text='A távollét záró időpontja (dátum és idő)')
    reason = models.TextField(max_length=500, blank=True, null=True, verbose_name='Indoklás', 
                             help_text='A távollét indoklása (opcionális, maximum 500 karakter)')
    denied = models.BooleanField(default=False, verbose_name='Elutasítva', 
                                help_text='Jelöli, hogy a távollét kérés el lett-e utasítva')
    approved = models.BooleanField(default=False, verbose_name='Jóváhagyva', 
                                   help_text='Jelöli, hogy a távollét kérés jóvá lett-e hagyva')

    def __str__(self):
        return f'{self.user.get_full_name()}: {self.start_date.strftime("%Y-%m-%d %H:%M")} - {self.end_date.strftime("%Y-%m-%d %H:%M")}'
    
    class Meta:
        verbose_name = "Távollét"
        verbose_name_plural = "Távollétek"
        ordering = ['start_date']

class RadioSession(models.Model):
    """
    Rádiós összejátszások kezelése másodéves (9F) diákok számára
    """
    radio_stab = models.ForeignKey('RadioStab', on_delete=models.CASCADE, verbose_name='Rádiós stáb',
                                  help_text='Az összejátszáshoz tartozó rádiós stáb')
    date = models.DateField(blank=False, null=False, verbose_name='Dátum',
                           help_text='Az összejátszás dátuma')
    time_from = models.TimeField(blank=False, null=False, verbose_name='Kezdés ideje',
                                help_text='Az összejátszás kezdési időpontja')
    time_to = models.TimeField(blank=False, null=False, verbose_name='Befejezés ideje',
                              help_text='Az összejátszás befejezési időpontja')
    description = models.TextField(max_length=500, blank=True, null=True, verbose_name='Leírás',
                                  help_text='Az összejátszás leírása (opcionális, maximum 500 karakter)')
    participants = models.ManyToManyField('auth.User', related_name='radio_sessions', blank=True, verbose_name='Résztvevők',
                                         help_text='Az összejátszásban résztvevő felhasználók')
    tanev = models.ForeignKey('Tanev', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Tanév',
                              help_text='A rádiós összejátszás tanéve (automatikusan meghatározva a dátum alapján)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Létrehozva',
                                     help_text='Az összejátszás létrehozásának időpontja')
    
    def __str__(self):
        return f'{self.radio_stab.name} rádiós összejátszás - {self.date} {self.time_from}-{self.time_to}'
    
    def save(self, *args, **kwargs):
        # Auto-assign school year based on date
        if not self.tanev and self.date:
            self.tanev = Tanev.get_current_by_date(self.date)
        super().save(*args, **kwargs)
    
    def get_participant_profiles(self):
        """Get profiles of participants who should be in 9F class"""
        return Profile.objects.filter(
            user__in=self.participants.all(),
            osztaly__szekcio='F'
        ).select_related('user', 'osztaly')
    
    def is_user_participating(self, user):
        """Check if a user is participating in this radio session"""
        return self.participants.filter(id=user.id).exists()
    
    def overlaps_with_datetime(self, start_datetime, end_datetime):
        """Check if this radio session overlaps with given datetime range"""
        from datetime import datetime, time
        from calendar import FRIDAY
        from datetime import timedelta
        
        session_start = datetime.combine(self.date, self.time_from)
        session_end = datetime.combine(self.date, self.time_to)
        
        # Convert to local naive datetimes for SQLite compatibility
        start_datetime = convert_to_local_naive_datetime(start_datetime)
        end_datetime = convert_to_local_naive_datetime(end_datetime)
        
        return session_start < end_datetime and session_end > start_datetime
    
    class Meta:
        verbose_name = "Rádiós összejátszás"
        verbose_name_plural = "Rádiós összejátszások"
        ordering = ['date', 'time_from']

class Beosztas(models.Model):
    kesz = models.BooleanField(default=False, verbose_name='Kész', 
                              help_text='Jelöli, hogy a beosztás elkészült és végleges-e')
    szerepkor_relaciok = models.ManyToManyField('SzerepkorRelaciok', related_name='beosztasok', blank=True, 
                                               verbose_name='Szerepkör relációk', 
                                               help_text='A beosztáshoz tartozó szerepkör hozzárendelések')
    author = models.ForeignKey('auth.User', related_name='beosztasok', on_delete=models.PROTECT, blank=True, null=True, 
                              verbose_name='Szerző', help_text='A beosztást végző felhasználó')
    tanev = models.ForeignKey('Tanev', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Tanév',
                              help_text='A beosztás tanéve')
    forgatas = models.ForeignKey('Forgatas', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Forgatás',
                                help_text='A beosztáshoz tartozó forgatás', related_name='beosztasok')
    stab = models.ForeignKey('Stab', related_name='beosztasok', on_delete=models.PROTECT, blank=True, null=True, 
                            verbose_name='Stáb', help_text='A beosztáshoz tartozó stáb')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Létrehozva', 
                                     help_text='A beosztás létrehozásának időpontja')
    
    def __str__(self):
        tanev_str = f" ({self.tanev})" if self.tanev else ""
        forgatas_str = f" - {self.forgatas.name}" if self.forgatas else ""
        stab_str = f" [{self.stab.name}]" if self.stab else ""
        return f'Beosztás {self.id}{tanev_str}{forgatas_str}{stab_str} - Kész: {self.kesz}'
    
    def save(self, *args, **kwargs):
        # Auto-assign current active school year if none specified
        if not self.tanev:
            self.tanev = Tanev.get_active()
        
        # Store old state for comparison if updating
        old_szerepkor_relaciok = None
        old_forgatas = None
        if self.pk:
            try:
                old_beosztas = Beosztas.objects.get(pk=self.pk)
                old_szerepkor_relaciok = set(old_beosztas.szerepkor_relaciok.all())
                old_forgatas = old_beosztas.forgatas
            except Beosztas.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Auto-manage absence records after save
        self.update_absence_records(old_szerepkor_relaciok, old_forgatas)
    
    def update_absence_records(self, old_szerepkor_relaciok=None, old_forgatas=None):
        """
        Automatically create/update/delete absence records based on assignment changes
        Creates absences for all assignments with forgatas, regardless of kesz status
        """
        print(f"[DEBUG] update_absence_records called for Beosztas {self.id}")
        print(f"[DEBUG] - forgatas: {self.forgatas}")
        print(f"[DEBUG] - kesz: {self.kesz}")
        
        if not self.forgatas:
            print(f"[DEBUG] No forgatas found, cleaning up existing absences")
            # If no forgatas, clean up any existing absences
            self.clean_absence_records()
            return
        
        # Get current users assigned to this forgatas
        current_users = set()
        for relacio in self.szerepkor_relaciok.all():
            current_users.add(relacio.user)
        
        print(f"[DEBUG] Current users assigned: {[u.get_full_name() for u in current_users]}")
        
        # Get old users if this was an update
        old_users = set()
        if old_szerepkor_relaciok:
            for relacio in old_szerepkor_relaciok:
                old_users.add(relacio.user)
        
        print(f"[DEBUG] Old users assigned: {[u.get_full_name() for u in old_users]}")
        
        # Create absence records for newly assigned users
        new_users = current_users - old_users
        print(f"[DEBUG] New users to create absences for: {[u.get_full_name() for u in new_users]}")
        for user in new_users:
            print(f"[DEBUG] Creating absence for user: {user.get_full_name()}")
            self.create_absence_for_user(user)
        
        # Remove absence records for users no longer assigned
        removed_users = old_users - current_users
        print(f"[DEBUG] Users to remove absences for: {[u.get_full_name() for u in removed_users]}")
        for user in removed_users:
            print(f"[DEBUG] Removing absence for user: {user.get_full_name()}")
            self.remove_absence_for_user(user)
        
        # For existing users, ensure they have absence records (in case they were missing)
        existing_users = current_users & old_users if old_users else current_users
        print(f"[DEBUG] Existing users to check/update: {[u.get_full_name() for u in existing_users]}")
        for user in existing_users:
            # Always ensure absence exists, create if missing
            if not Absence.objects.filter(diak=user, forgatas=self.forgatas, auto_generated=True).exists():
                print(f"[DEBUG] Missing absence for existing user {user.get_full_name()}, creating...")
                self.create_absence_for_user(user)
            else:
                print(f"[DEBUG] Absence exists for user {user.get_full_name()}, updating if needed...")
                self.update_absence_for_user(user)
        
        # Update existing absence records if forgatas details changed
        if old_forgatas and (
            old_forgatas.date != self.forgatas.date or 
            old_forgatas.timeFrom != self.forgatas.timeFrom or 
            old_forgatas.timeTo != self.forgatas.timeTo
        ):
            print(f"[DEBUG] Forgatas details changed, updating all existing absences")
            # Update all existing absence records with new timing
            for user in current_users:
                print(f"[DEBUG] Updating absence timing for user: {user.get_full_name()}")
                self.update_absence_for_user(user)
    
    def create_absence_for_user(self, user):
        """Create an absence record for a user assigned to this forgatas"""
        if not self.forgatas:
            print(f"[DEBUG] Cannot create absence - no forgatas")
            return
        
        print(f"[DEBUG] create_absence_for_user called for user: {user.get_full_name()}")
        print(f"[DEBUG] - forgatas: {self.forgatas.name}")
        print(f"[DEBUG] - date: {self.forgatas.date}")
        print(f"[DEBUG] - time: {self.forgatas.timeFrom} - {self.forgatas.timeTo}")
        
        # Check if auto-generated absence already exists to avoid duplicates
        existing_absence = Absence.objects.filter(
            diak=user,
            forgatas=self.forgatas,
            auto_generated=True
        ).first()
        
        if existing_absence:
            print(f"[DEBUG] Auto-generated absence already exists for {user.get_full_name()}, updating instead")
            # Update the existing one instead of creating duplicate
            existing_absence.date = self.forgatas.date
            existing_absence.timeFrom = self.forgatas.timeFrom
            existing_absence.timeTo = self.forgatas.timeTo
            existing_absence.save()
            print(f"[DEBUG] Updated existing absence #{existing_absence.id}")
        else:
            try:
                new_absence = Absence.objects.create(
                    diak=user,
                    forgatas=self.forgatas,
                    date=self.forgatas.date,
                    timeFrom=self.forgatas.timeFrom,
                    timeTo=self.forgatas.timeTo,
                    excused=False,  # Default to not excused
                    unexcused=False,
                    auto_generated=True  # Mark as auto-generated
                )
                print(f"[SUCCESS] Created new absence #{new_absence.id} for {user.get_full_name()}")
            except Exception as e:
                print(f"[ERROR] Failed to create absence for {user.get_full_name()}: {e}")
    
    def update_absence_for_user(self, user):
        """Update existing absence record for a user when forgatas details change"""
        if not self.forgatas:
            print(f"[DEBUG] Cannot update absence - no forgatas")
            return
        
        print(f"[DEBUG] update_absence_for_user called for user: {user.get_full_name()}")
        
        try:
            # Look for auto-generated absence first
            absence = Absence.objects.filter(
                diak=user,
                forgatas=self.forgatas,
                auto_generated=True
            ).first()
            
            if absence:
                print(f"[DEBUG] Found auto-generated absence #{absence.id}, updating...")
                # Update with new timing from forgatas
                absence.date = self.forgatas.date
                absence.timeFrom = self.forgatas.timeFrom
                absence.timeTo = self.forgatas.timeTo
                absence.save()
                print(f"[SUCCESS] Updated absence #{absence.id} for {user.get_full_name()}")
            else:
                print(f"[DEBUG] No auto-generated absence found for {user.get_full_name()}, creating new one")
                # If absence doesn't exist, create it
                self.create_absence_for_user(user)
        except Exception as e:
            print(f"[ERROR] Failed to update absence for {user.get_full_name()}: {e}")
            # Try to create if update fails
            self.create_absence_for_user(user)
    
    def remove_absence_for_user(self, user):
        """Remove absence record for a user no longer assigned to this forgatas"""
        if not self.forgatas:
            print(f"[DEBUG] Cannot remove absence - no forgatas")
            return
        
        print(f"[DEBUG] remove_absence_for_user called for user: {user.get_full_name()}")
        
        # Only remove auto-generated absence records
        deleted_count, _ = Absence.objects.filter(
            diak=user,
            forgatas=self.forgatas,
            auto_generated=True
        ).delete()
        
        if deleted_count > 0:
            print(f"[SUCCESS] Removed {deleted_count} auto-generated absence(s) for {user.get_full_name()}")
        else:
            print(f"[DEBUG] No auto-generated absences found to remove for {user.get_full_name()}")
    
    def clean_absence_records(self):
        """Remove all auto-generated absence records associated with this assignment"""
        print(f"[DEBUG] clean_absence_records called for Beosztas {self.id}")
        
        if self.forgatas:
            print(f"[DEBUG] Cleaning absences for forgatas: {self.forgatas.name}")
            
            # Get users currently in assignment
            users_in_assignment = set()
            for relacio in self.szerepkor_relaciok.all():
                users_in_assignment.add(relacio.user)
            
            print(f"[DEBUG] Users in assignment: {[u.get_full_name() for u in users_in_assignment]}")
            
            if users_in_assignment:
                # Only remove auto-generated absences for users in this assignment
                deleted_count, _ = Absence.objects.filter(
                    forgatas=self.forgatas,
                    diak__in=users_in_assignment,
                    auto_generated=True
                ).delete()
            else:
                # If no users in assignment, remove all auto-generated absences for this forgatas
                deleted_count, _ = Absence.objects.filter(
                    forgatas=self.forgatas,
                    auto_generated=True
                ).delete()
            
            if deleted_count > 0:
                print(f"[SUCCESS] Cleaned {deleted_count} auto-generated absences")
            else:
                print(f"[DEBUG] No auto-generated absences found to clean")
        else:
            print(f"[DEBUG] No forgatas to clean absences for")
    
    def get_assigned_users(self):
        """Get all users assigned to roles in this assignment"""
        return [relacio.user for relacio in self.szerepkor_relaciok.all()]
    
    @classmethod
    def sync_all_absence_records(cls):
        """
        Bulk synchronization method to update all absence records for all assignments
        Useful for initial setup or data cleanup
        """
        from django.db import transaction
        
        with transaction.atomic():
            print(f"[DEBUG] sync_all_absence_records started")
            
            # Get all assignments with forgatas (regardless of kesz status)
            assignments_with_forgatas = cls.objects.filter(forgatas__isnull=False)
            print(f"[DEBUG] Found {assignments_with_forgatas.count()} assignments with forgatas")
            
            # Delete existing auto-generated absence records for these forgatások
            forgatas_ids = [a.forgatas.id for a in assignments_with_forgatas]
            deleted_count = Absence.objects.filter(
                forgatas_id__in=forgatas_ids, 
                auto_generated=True
            ).delete()[0]
            print(f"[DEBUG] Deleted {deleted_count} existing auto-generated absences")
            
            # Recreate absence records for all current assignments
            created_count = 0
            for beosztas in assignments_with_forgatas:
                print(f"[DEBUG] Processing beosztas {beosztas.id}")
                for user in beosztas.get_assigned_users():
                    beosztas.create_absence_for_user(user)
                    created_count += 1
            
            print(f"[SUCCESS] sync_all_absence_records completed: deleted {deleted_count}, created {created_count}")
            return {'deleted': deleted_count, 'created': created_count}
    
    class Meta:
        verbose_name = "Beosztás"
        verbose_name_plural = "Beosztások"
        ordering = ['-created_at']

class SzerepkorRelaciok(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='Felhasználó', 
                            help_text='A szerepkört betöltő felhasználó')
    szerepkor = models.ForeignKey('Szerepkor', on_delete=models.CASCADE, verbose_name='Szerepkör', 
                                 help_text='A hozzárendelt szerepkör')

    def __str__(self):
        return f'{self.user.get_full_name()} - {self.szerepkor.name}'
    
    def save(self, *args, **kwargs):
        """Auto-update absence records when role assignments change"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update absence records for all assignments using this role relation
        if not is_new:
            self.update_related_assignments()
    
    def delete(self, *args, **kwargs):
        """Auto-update absence records when role assignments are deleted"""
        # Store assignments before deletion
        related_assignments = list(self.beosztasok.all())
        super().delete(*args, **kwargs)
        
        # Update absence records for affected assignments
        for beosztas in related_assignments:
            if beosztas.kesz and beosztas.forgatas:
                beosztas.remove_absence_for_user(self.user)
    
    def update_related_assignments(self):
        """Update absence records for all assignments that use this role relation"""
        for beosztas in self.beosztasok.all():
            if beosztas.kesz and beosztas.forgatas:
                beosztas.create_absence_for_user(self.user)
    
    class Meta:
        verbose_name = "Szerepkör Reláció"
        verbose_name_plural = "Szerepkör Relációk"
        ordering = ['user__last_name', 'user__first_name']

class Szerepkor(models.Model):
    name = models.CharField(max_length=150, unique=True, blank=False, null=False, verbose_name='Szerepkör neve', 
                           help_text='A szerepkör egyedi neve')
    ev = models.IntegerField(blank=True, null=True, verbose_name='Év', 
                            help_text='Az évfolyam, amelyre a szerepkör vonatkozik (opcionális)')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Szerepkör"
        verbose_name_plural = "Szerepkörök"
        ordering = ['name']


# Signal handlers for automatic absence management
@receiver(m2m_changed, sender=Beosztas.szerepkor_relaciok.through)
def handle_beosztas_szerepkor_change(sender, instance, action, pk_set, **kwargs):
    """
    Handle changes to the szerepkor_relaciok many-to-many field in Beosztas
    Automatically manage absence records when role assignments change
    Works for both draft and finalized assignments
    """
    print(f"[DEBUG] M2M signal handler called: action={action}, instance={instance.id}")
    
    if not instance.forgatas:
        print(f"[DEBUG] No forgatas, skipping absence management")
        return
    
    if action == 'post_add':
        print(f"[DEBUG] M2M post_add: {len(pk_set)} relations added")
        # New role relations added - create absence records for new users
        for relacio_pk in pk_set:
            try:
                relacio = SzerepkorRelaciok.objects.get(pk=relacio_pk)
                print(f"[DEBUG] Creating absence for added user: {relacio.user.get_full_name()}")
                instance.create_absence_for_user(relacio.user)
            except SzerepkorRelaciok.DoesNotExist:
                print(f"[WARNING] SzerepkorRelaciok with pk {relacio_pk} not found")
                pass
                
    elif action == 'post_remove':
        print(f"[DEBUG] M2M post_remove: {len(pk_set)} relations removed")
        # Role relations removed - delete absence records for removed users
        for relacio_pk in pk_set:
            try:
                relacio = SzerepkorRelaciok.objects.get(pk=relacio_pk)
                print(f"[DEBUG] Removing absence for removed user: {relacio.user.get_full_name()}")
                instance.remove_absence_for_user(relacio.user)
            except SzerepkorRelaciok.DoesNotExist:
                print(f"[WARNING] SzerepkorRelaciok with pk {relacio_pk} not found")
                pass
                
    elif action == 'post_clear':
        print(f"[DEBUG] M2M post_clear: clearing all absences")
        # All role relations cleared - remove all related absence records
        instance.clean_absence_records()


# ============================================================================
# Email Notification Signal Handlers
# ============================================================================

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

@receiver(post_save, sender=Announcement)
def send_announcement_email(sender, instance, created, **kwargs):
    """
    Send email notification when an announcement is created or updated.
    """
    if created:
        print(f"[DEBUG] ========== ANNOUNCEMENT CREATED SIGNAL ==========")
        print(f"[DEBUG] New announcement created: {instance.title}")
        
        try:
            # Import email function
            from backend.api_modules.authentication import send_announcement_notification_email
            
            # Determine recipients
            recipients = []
            if instance.cimzettek.exists():
                # Targeted announcement - notify specific recipients
                recipients = list(instance.cimzettek.filter(is_active=True))
                print(f"[DEBUG] Targeted announcement - {len(recipients)} specific recipients")
            else:
                # Global announcement - notify all active users
                recipients = list(User.objects.filter(is_active=True))
                print(f"[DEBUG] Global announcement - {len(recipients)} active users")
            
            if recipients:
                print(f"[DEBUG] Sending announcement email to {len(recipients)} recipients")
                email_sent = send_announcement_notification_email(instance, recipients)
                
                if email_sent:
                    print(f"[SUCCESS] Announcement email sent successfully: {instance.title}")
                else:
                    print(f"[WARNING] Failed to send announcement email: {instance.title}")
            else:
                print(f"[DEBUG] No recipients found for announcement email")
                
        except Exception as e:
            print(f"[ERROR] Announcement email signal failed: {str(e)}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")


@receiver(m2m_changed, sender=Announcement.cimzettek.through)
def announcement_recipients_changed(sender, instance, action, pk_set, **kwargs):
    """
    Send email notification when announcement recipients are changed after creation.
    """
    if action == 'post_add' and pk_set:
        print(f"[DEBUG] ========== ANNOUNCEMENT RECIPIENTS CHANGED ==========")
        print(f"[DEBUG] Recipients added to announcement: {instance.title}")
        
        try:
            # Import email function
            from backend.api_modules.authentication import send_announcement_notification_email
            
            # Get newly added recipients
            new_recipients = list(User.objects.filter(id__in=pk_set, is_active=True))
            
            if new_recipients:
                print(f"[DEBUG] Sending announcement email to {len(new_recipients)} new recipients")
                email_sent = send_announcement_notification_email(instance, new_recipients)
                
                if email_sent:
                    print(f"[SUCCESS] Announcement email sent to new recipients: {instance.title}")
                else:
                    print(f"[WARNING] Failed to send announcement email to new recipients: {instance.title}")
            else:
                print(f"[DEBUG] No new active recipients found")
                
        except Exception as e:
            print(f"[ERROR] Announcement recipients change email signal failed: {str(e)}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")


@receiver(post_save, sender=Beosztas)
def send_assignment_email(sender, instance, created, **kwargs):
    """
    Send email notification when an assignment is created or updated.
    """
    print(f"[DEBUG] ========== ASSIGNMENT SAVED SIGNAL ==========")
    print(f"[DEBUG] Assignment saved - Created: {created}, ID: {instance.id}")
    
    if not instance.forgatas:
        print(f"[DEBUG] No forgatas associated with assignment, skipping email")
        return
    
    # Skip email notifications for KaCsa type forgatások
    if instance.forgatas.forgTipus == 'kacsa':
        print(f"[DEBUG] Skipping email notification for KaCsa type forgatas: {instance.forgatas.name}")
        return
    
    try:
        # Import email function
        from backend.api_modules.authentication import send_assignment_change_notification_email
        
        # Get current assigned users
        current_users = []
        for relation in instance.szerepkor_relaciok.all():
            current_users.append(relation.user)
        
        print(f"[DEBUG] Current assigned users: {len(current_users)}")
        
        if created:
            # New assignment - notify all assigned users
            print(f"[DEBUG] New assignment created, notifying all assigned users")
            
            if current_users:
                email_sent = send_assignment_change_notification_email(
                    instance.forgatas,
                    current_users,  # added users
                    []  # no removed users for new assignment
                )
                
                if email_sent:
                    print(f"[SUCCESS] Assignment creation email sent: {instance.forgatas.name}")
                else:
                    print(f"[WARNING] Failed to send assignment creation email: {instance.forgatas.name}")
            else:
                print(f"[DEBUG] No users assigned to new assignment")
        else:
            # Assignment updated - we would need to track changes
            # For now, just notify if it's being finalized
            if instance.kesz:
                print(f"[DEBUG] Assignment finalized, notifying all assigned users")
                
                if current_users:
                    email_sent = send_assignment_change_notification_email(
                        instance.forgatas,
                        current_users,  # notify all assigned users about finalization
                        []  # no removed users
                    )
                    
                    if email_sent:
                        print(f"[SUCCESS] Assignment finalization email sent: {instance.forgatas.name}")
                    else:
                        print(f"[WARNING] Failed to send assignment finalization email: {instance.forgatas.name}")
                else:
                    print(f"[DEBUG] No users assigned to finalized assignment")
            else:
                print(f"[DEBUG] Assignment updated but not finalized, no email sent")
                
    except Exception as e:
        print(f"[ERROR] Assignment email signal failed: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")


@receiver(m2m_changed, sender=Beosztas.szerepkor_relaciok.through)
def assignment_users_changed(sender, instance, action, pk_set, **kwargs):
    """
    Send email notification when assignment users are changed.
    """
    if action in ['post_add', 'post_remove'] and pk_set and instance.forgatas:
        print(f"[DEBUG] ========== ASSIGNMENT USERS CHANGED ==========")
        print(f"[DEBUG] Assignment users changed - Action: {action}, Assignment ID: {instance.id}")
        
        # Skip email notifications for KaCsa type forgatások
        if instance.forgatas.forgTipus == 'kacsa':
            print(f"[DEBUG] Skipping email notification for KaCsa type forgatas: {instance.forgatas.name}")
            return
        
        try:
            # Import email function
            from backend.api_modules.authentication import send_assignment_change_notification_email
            
            if action == 'post_add':
                # Users added to assignment
                added_relations = SzerepkorRelaciok.objects.filter(id__in=pk_set)
                added_users = [rel.user for rel in added_relations]
                
                print(f"[DEBUG] Users added to assignment: {len(added_users)}")
                
                if added_users:
                    email_sent = send_assignment_change_notification_email(
                        instance.forgatas,
                        added_users,  # added users
                        []  # no removed users
                    )
                    
                    if email_sent:
                        print(f"[SUCCESS] Assignment addition email sent: {instance.forgatas.name}")
                    else:
                        print(f"[WARNING] Failed to send assignment addition email: {instance.forgatas.name}")
                        
            elif action == 'post_remove':
                # Users removed from assignment
                # Note: We can't get the relation objects after removal, so we'll skip removal emails for now
                # This is a limitation of the current approach - we'd need to store the old state before removal
                print(f"[DEBUG] Users removed from assignment - removal emails not implemented in signals yet")
                
        except Exception as e:
            print(f"[ERROR] Assignment users change email signal failed: {str(e)}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")

class SystemMessage(models.Model):
    # Severity choices
    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_ERROR = 'error'
    
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Információ'),
        (SEVERITY_WARNING, 'Figyelmeztetés'),
        (SEVERITY_ERROR, 'Hiba'),
    ]
    
    # Message type choices
    MESSAGE_TYPE_USER = 'user'
    MESSAGE_TYPE_DEVELOPER = 'developer'
    MESSAGE_TYPE_OPERATOR = 'operator'
    MESSAGE_TYPE_SUPPORT = 'support'
    
    MESSAGE_TYPE_CHOICES = [
        (MESSAGE_TYPE_USER, 'Felhasználó'),
        (MESSAGE_TYPE_DEVELOPER, 'Fejlesztő'),
        (MESSAGE_TYPE_OPERATOR, 'Operátor'),
        (MESSAGE_TYPE_SUPPORT, 'Támogatás'),
    ]
    
    title = models.CharField(max_length=200, blank=False, null=False, verbose_name='Cím', 
                            help_text='A rendszerüzenet címe (maximum 200 karakter)')
    message = models.TextField(max_length=2000, blank=False, null=False, verbose_name='Üzenet', 
                              help_text='A rendszerüzenet tartalma (maximum 2000 karakter)')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default=SEVERITY_INFO, 
                               verbose_name='Súlyosság', 
                               help_text='Az üzenet súlyossága (info/warning/error)')
    messageType = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default=MESSAGE_TYPE_USER,
                                  verbose_name='Üzenet típusa',
                                  help_text='Az üzenet célközönsége (user/developer/operator/support)')
    showFrom = models.DateTimeField(blank=False, null=False, verbose_name='Megjelenítés kezdete', 
                                   help_text='Az üzenet megjelenítésének kezdő időpontja')
    showTo = models.DateTimeField(blank=False, null=False, verbose_name='Megjelenítés vége', 
                                 help_text='Az üzenet megjelenítésének záró időpontja')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Létrehozva', 
                                     help_text='A rendszerüzenet létrehozásának időpontja')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Módosítva', 
                                     help_text='A rendszerüzenet utolsó módosításának időpontja')

    def __str__(self):
        return self.title
    
    @classmethod
    def get_active_messages(cls, check_datetime=None):
        """Get all system messages that should be displayed at the given datetime (default: now)"""
        if check_datetime is None:
            check_datetime = datetime.now()
        
        return cls.objects.filter(
            showFrom__lte=check_datetime,
            showTo__gte=check_datetime
        ).order_by('showFrom')
    
    def is_active(self, check_datetime=None):
        """Check if this message should be displayed at the given datetime (default: now)"""
        if check_datetime is None:
            check_datetime = datetime.now()
        
        return self.showFrom <= check_datetime <= self.showTo
    
    class Meta:
        verbose_name = "Rendszerüzenet"
        verbose_name_plural = "Rendszerüzenetek"
        ordering = ['-showFrom']
