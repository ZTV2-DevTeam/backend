import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Profile

print('Total Users:', User.objects.count())
print('Total Profiles:', Profile.objects.count())

u4 = User.objects.filter(id=4).first()
u160 = User.objects.filter(id=160).first()

print(f'\nUser 4: {u4.username if u4 else "NOT FOUND"}')
p4 = Profile.objects.filter(user__id=4).first() if u4 else None
print(f'Profile 4: {"EXISTS" if p4 else "NOT FOUND"}')

print(f'\nUser 160: {u160.username if u160 else "NOT FOUND"}')
p160 = Profile.objects.filter(user__id=160).first() if u160 else None
print(f'Profile 160: {"EXISTS" if p160 else "NOT FOUND"}')
