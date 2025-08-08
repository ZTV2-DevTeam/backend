from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

# Create your models here.


class Profile(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    telefonszam = models.CharField(max_length=20, blank=True, null=True)
    medias = models.BooleanField(default=True)
    stab = models.ForeignKey('Stab', related_name='tagok', on_delete=models.SET_NULL, blank=True, null=True)
    osztaly = models.ForeignKey('Osztaly', on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name()

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

    institution = models.ForeignKey('PartnerTipus', on_delete=models.SET_NULL, related_name='partners', blank=True, null=True)
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
    location = models.ForeignKey('Partner', on_delete=models.SET_NULL, blank=True, null=True)
    contactPerson = models.ForeignKey('ContactPerson', on_delete=models.SET_NULL, blank=True, null=True)
    notes = models.TextField(max_length=500, blank=True, null=True)

    tipusok = [
        ('kacsa', 'KaCsa'),
        ('rendes', 'Rendes'),
        ('rendezveny', 'Rendezvény'),
        ('egyeb', 'Egyéb'),
    ]

    forgTipus = models.CharField(max_length=150, choices=tipusok, blank=False, null=False)

    relatedKaCsa = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='related_forgatas', limit_choices_to={'forgTipus': 'kacsa'})
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
    equipmentType = models.ForeignKey('EquipmentTipus', on_delete=models.SET_NULL, related_name='equipments', blank=True, null=True)
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