from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

# Create your models here.


class Profile(models.Model):
    ADMIN_TYPES = [
        ('none', 'Nincs adminisztrátor jogosultság'),
        ('developer', 'Administrator-Developer'),
        ('teacher', 'Administrator-Teacher (Médiatanár)'),
    ]
    
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    telefonszam = models.CharField(max_length=20, blank=True, null=True)
    medias = models.BooleanField(default=True)
    stab = models.ForeignKey('Stab', related_name='tagok', on_delete=models.PROTECT, blank=True, null=True)
    radio_stab = models.ForeignKey('RadioStab', related_name='tagok', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Rádiós stáb')
    osztaly = models.ForeignKey('Osztaly', on_delete=models.PROTECT, blank=True, null=True)
    admin_type = models.CharField(max_length=20, choices=ADMIN_TYPES, default='none', verbose_name='Adminisztrátor típus')

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
    
    def has_admin_permission(self, permission_type):
        """
        Check if user has specific admin permission
        permission_type can be: 'developer', 'teacher', 'any'
        """
        if permission_type == 'any':
            return self.is_admin
        elif permission_type == 'developer':
            return self.is_developer_admin
        elif permission_type == 'teacher':
            return self.is_teacher_admin
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
        
        # Check regular absences
        start_date = start_datetime.date() if hasattr(start_datetime, 'date') else start_datetime
        end_date = end_datetime.date() if hasattr(end_datetime, 'date') else end_datetime
        
        # Check if user has marked absence during this period
        absence_overlap = Tavollet.objects.filter(
            user=self.user,
            start_date__lte=end_date,
            end_date__gte=start_date,
            denied=False
        ).exists()
        
        if absence_overlap:
            return False
        
        # If this is a second year radio student, check for radio sessions
        if self.is_second_year_radio_student:
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

class Osztaly(models.Model):
    startYear = models.IntegerField(blank=False, null=False)
    szekcio = models.CharField(max_length=1, blank=False, null=False)

    def __str__(self):
        current_year = datetime.now().year
        elso_felev = datetime.now().month >= 9
        if self.szekcio.upper() == 'F':
            if self.startYear == current_year and datetime.now().month < 9:
                return 'Bejövő NYF'
            
            year_diff = current_year - self.startYear 
            year_diff += 8 if elso_felev else 7

            return f'{year_diff}F'
        return f'{self.startYear[:-2]}{self.szekcio.upper()}'
            
class Stab(models.Model):
    name = models.CharField(max_length=50, unique=True, blank=False, null=False)

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
    
    name = models.CharField(max_length=50, blank=False, null=False, verbose_name='Stáb név')
    team_code = models.CharField(max_length=2, choices=RADIO_TEAMS, unique=True, verbose_name='Csapat kód')
    description = models.TextField(max_length=300, blank=True, null=True, verbose_name='Leírás')
    
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
    name = models.CharField(max_length=150, unique=True, blank=False, null=False)
    address = models.CharField(max_length=500, blank=True, null=True)

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

    institution = models.ForeignKey('PartnerTipus', on_delete=models.PROTECT, related_name='partners', blank=True, null=True)
    imgUrl = models.URLField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Partner"
        verbose_name_plural = "Partnerek"
        ordering = ['name']

class PartnerTipus(models.Model):
    name = models.CharField(max_length=150, unique=True, blank=False, null=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Partner Típus"
        verbose_name_plural = "Partner Típusok"

class Config(models.Model):
    active = models.BooleanField(default=False)

    allowEmails = models.BooleanField(default=False)

    def __str__(self):
        return f'active: {self.active}'
    
    class Meta:
        verbose_name = "Konfiguráció"
        verbose_name_plural = "Konfigurációk"

class Forgatas(models.Model):
    name = models.CharField(max_length=150, blank=False, null=False)
    description = models.TextField(max_length=500, blank=False, null=False)
    date = models.DateField(blank=False, null=False)
    timeFrom = models.TimeField(blank=False, null=False)
    timeTo = models.TimeField(blank=False, null=False)
    location = models.ForeignKey('Partner', on_delete=models.PROTECT, blank=True, null=True)
    contactPerson = models.ForeignKey('ContactPerson', on_delete=models.PROTECT, blank=True, null=True)
    notes = models.TextField(max_length=500, blank=True, null=True)

    tipusok = [
        ('kacsa', 'KaCsa'),
        ('rendes', 'Rendes'),
        ('rendezveny', 'Rendezvény'),
        ('egyeb', 'Egyéb'),
    ]

    forgTipus = models.CharField(max_length=150, choices=tipusok, blank=False, null=False)

    relatedKaCsa = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True, related_name='related_forgatas', limit_choices_to={'forgTipus': 'kacsa'})
    equipments = models.ManyToManyField('Equipment', blank=True, related_name='forgatasok')

    def __str__(self):
        return f'{self.name} ({self.date})'
    
    class Meta:
        verbose_name = "Forgatás"
        verbose_name_plural = "Forgatások"
        ordering = ['date', 'timeFrom']

class EquipmentTipus(models.Model):
    name = models.CharField(max_length=150, unique=True, blank=False, null=False)
    emoji = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f'{self.name} ({self.emoji})'
    
    class Meta:
        verbose_name = "Eszköz Típus"
        verbose_name_plural = "Eszköz Típusok"

class Equipment(models.Model):
    nickname = models.CharField(max_length=150, unique=True, blank=False, null=False)
    brand = models.CharField(max_length=150, blank=True, null=True)
    model = models.CharField(max_length=150, blank=True, null=True)
    serialNumber = models.CharField(max_length=150, unique=True, blank=True, null=True)
    equipmentType = models.ForeignKey('EquipmentTipus', on_delete=models.PROTECT, related_name='equipments', blank=True, null=True)
    functional = models.BooleanField(default=True)
    notes = models.TextField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f'{self.nickname} ({self.brand} {self.model})'
    
    class Meta:
        verbose_name = "Felaszerelés"
        verbose_name_plural = "Felaszerelések"
        ordering = ['nickname']

    def is_available_for(self, start_datetime, end_datetime):
        return not self.forgatas.filter(
            start_time__lt=end_datetime,
            end_time__gt=start_datetime
        ).exists()

class ContactPerson(models.Model):
    name = models.CharField(max_length=150, blank=False, null=False)
    email = models.EmailField(max_length=254, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kapcsolattartó"
        verbose_name_plural = "Kapcsolattartók"

class Announcement(models.Model):
    author = models.ForeignKey('auth.user', related_name='announcements', on_delete=models.PROTECT, blank=True, null=True)
    title = models.CharField(max_length=200, blank=False, null=False)
    body = models.TextField(max_length=5000, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cimzettek = models.ManyToManyField('auth.User', related_name='uzenetek', blank=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Közlemény"
        verbose_name_plural = "Közlemények"
        ordering = ['-created_at']

class Tavollet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField(blank=False, null=False)
    end_date = models.DateField(blank=False, null=False)
    reason = models.TextField(max_length=500, blank=True, null=True)
    denied = models.BooleanField(default=False)


    def __str__(self):
        return f'{self.user.get_full_name()}: {self.start_date} - {self.end_date}'
    
    class Meta:
        verbose_name = "Távollét"
        verbose_name_plural = "Távollétek"
        ordering = ['start_date']

class RadioSession(models.Model):
    """
    Rádiós összejátszások kezelése másodéves (9F) diákok számára
    """
    radio_stab = models.ForeignKey('RadioStab', on_delete=models.CASCADE, verbose_name='Rádiós stáb')
    date = models.DateField(blank=False, null=False, verbose_name='Dátum')
    time_from = models.TimeField(blank=False, null=False, verbose_name='Kezdés ideje')
    time_to = models.TimeField(blank=False, null=False, verbose_name='Befejezés ideje')
    description = models.TextField(max_length=500, blank=True, null=True, verbose_name='Leírás')
    participants = models.ManyToManyField('auth.User', related_name='radio_sessions', blank=True, verbose_name='Résztvevők')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.radio_stab.name} rádiós összejátszás - {self.date} {self.time_from}-{self.time_to}'
    
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
        
        session_start = datetime.combine(self.date, self.time_from)
        session_end = datetime.combine(self.date, self.time_to)
        
        return session_start < end_datetime and session_end > start_datetime
    
    class Meta:
        verbose_name = "Rádiós összejátszás"
        verbose_name_plural = "Rádiós összejátszások"
        ordering = ['date', 'time_from']

class Beosztas(models.Model):
    kesz = models.BooleanField(default=False)
    szerepkor_relaciok = models.ManyToManyField('SzerepkorRelaciok', related_name='beosztasok', blank=True)
    author = models.ForeignKey('auth.User', related_name='beosztasok', on_delete=models.PROTECT, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Beosztás {self.id} - Kész: {self.kesz}'
    
    class Meta:
        verbose_name = "Beosztás"
        verbose_name_plural = "Beosztások"
        ordering = ['-created_at']

class SzerepkorRelaciok(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    szerepkor = models.ForeignKey('Szerepkor', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.user.get_full_name()} - {self.szerepkor.name}'
    
    class Meta:
        verbose_name = "Szerepkör Reláció"
        verbose_name_plural = "Szerepkör Relációk"
        ordering = ['user__last_name', 'user__first_name']

class Szerepkor(models.Model):
    name = models.CharField(max_length=150, unique=True, blank=False, null=False)
    ev = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Szerepkör"
        verbose_name_plural = "Szerepkörök"
        ordering = ['name']
        