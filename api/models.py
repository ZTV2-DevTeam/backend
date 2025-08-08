from django.db import models


# Create your models here.

class Partner(models.Model):
    name = models.CharField(max_length=150, unique=True, blank=False, null=False)
    address = models.CharField(max_length=500, blank=True, null=True)

    intezmeny_tipusok = [
        ('iskola', 'Iskola'),
        ('kutatóintézet', 'Kutatóintézet'),
        ('kozossegi_haz', 'Közösségi Ház'),
        ('kulturalis_kozpont', 'Kulturális Központ'),
        ('muzeum', 'Múzeum'),
        ('konyvtar', 'Könyvtár'),
        ('egyesulet', 'Egyesület'),
        ('vallalat', 'Vállalat'),
        ('onkormanyzat', 'Önkormányzat'),
        ('egyeb', 'Egyéb'),
    ]

    institution = models.CharField(max_length=150, blank=False, null=False, default="egyeb", choices=intezmeny_tipusok)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Partner"
        verbose_name_plural = "Partnerek"
        ordering = ['name']