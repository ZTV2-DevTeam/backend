"""
Django Data Wizard configuration for importing data into essential tables.
"""
from data_wizard import registry
from django.contrib.auth.models import User
from .models import (
    Profile, Osztaly, Stab, RadioStab, Partner, PartnerTipus, 
    Equipment, EquipmentTipus, ContactPerson, Tanev
)


class UserProfileImportWizard:
    """
    Custom wizard to import users and their profiles from a single table.
    This allows importing both User and Profile data from the same CSV/Excel file.
    """
    
    def __init__(self):
        self.user_fields = [
            'username', 'first_name', 'last_name', 'email', 'is_active'
        ]
        self.profile_fields = [
            'telefonszam', 'medias', 'admin_type', 'special_role'
        ]
    
    def process_row(self, row_data):
        """
        Process a single row to create both User and Profile objects.
        
        Expected row format:
        {
            'username': 'john.doe',
            'first_name': 'John',
            'last_name': 'Doe', 
            'email': 'john@example.com',
            'is_active': True,
            'telefonszam': '+36301234567',
            'medias': True,
            'admin_type': 'none',
            'special_role': 'none',
            'stab_name': 'Kamera',  # Optional
            'radio_stab_team': 'A1',  # Optional for 9F students
            'osztaly_start_year': 2023,  # Optional
            'osztaly_szekcio': 'F'  # Optional
        }
        """
        try:
            # Extract user data
            user_data = {k: v for k, v in row_data.items() if k in self.user_fields and v is not None}
            
            # Create or update user
            user, created = User.objects.get_or_create(
                username=user_data.get('username'),
                defaults=user_data
            )
            
            if not created:
                # Update existing user
                for field, value in user_data.items():
                    setattr(user, field, value)
                user.save()
            
            # Extract profile data
            profile_data = {k: v for k, v in row_data.items() if k in self.profile_fields and v is not None}
            
            # Handle related objects
            stab = None
            if row_data.get('stab_name'):
                stab, _ = Stab.objects.get_or_create(name=row_data['stab_name'])
            
            radio_stab = None
            if row_data.get('radio_stab_team'):
                radio_stab, _ = RadioStab.objects.get_or_create(
                    team_code=row_data['radio_stab_team'],
                    defaults={'name': f"{row_data['radio_stab_team']} Rádiós Csapat"}
                )
            
            osztaly = None
            if row_data.get('osztaly_start_year') and row_data.get('osztaly_szekcio'):
                osztaly, _ = Osztaly.objects.get_or_create(
                    startYear=int(row_data['osztaly_start_year']),
                    szekcio=row_data['osztaly_szekcio']
                )
            
            # Create or update profile
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    **profile_data,
                    'stab': stab,
                    'radio_stab': radio_stab,
                    'osztaly': osztaly
                }
            )
            
            if not created:
                # Update existing profile
                for field, value in profile_data.items():
                    setattr(profile, field, value)
                if stab:
                    profile.stab = stab
                if radio_stab:
                    profile.radio_stab = radio_stab
                if osztaly:
                    profile.osztaly = osztaly
                profile.save()
            
            return {'user': user, 'profile': profile, 'created': created}
            
        except Exception as e:
            return {'error': str(e)}


# Register models with data wizard
@registry.register
class UserImport:
    """Simple User import wizard"""
    model = User
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class UserImportSerializer(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
                
        return UserImportSerializer


@registry.register  
class ProfileImport:
    """Profile import wizard"""
    model = Profile
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class ProfileImportSerializer(serializers.ModelSerializer):
            # Add foreign key lookups by name
            user_username = serializers.CharField(source='user.username', write_only=True)
            stab_name = serializers.CharField(source='stab.name', write_only=True, required=False)
            radio_stab_team = serializers.CharField(source='radio_stab.team_code', write_only=True, required=False)
            osztaly_start_year = serializers.IntegerField(source='osztaly.startYear', write_only=True, required=False)
            osztaly_szekcio = serializers.CharField(source='osztaly.szekcio', write_only=True, required=False)
            
            class Meta:
                model = Profile
                fields = [
                    'user_username', 'telefonszam', 'medias', 'admin_type', 'special_role',
                    'stab_name', 'radio_stab_team', 'osztaly_start_year', 'osztaly_szekcio'
                ]
                
            def create(self, validated_data):
                # Handle foreign key lookups
                user = User.objects.get(username=validated_data.pop('user')['username'])
                
                stab = None
                if 'stab' in validated_data and validated_data['stab']['name']:
                    stab, _ = Stab.objects.get_or_create(name=validated_data.pop('stab')['name'])
                
                radio_stab = None 
                if 'radio_stab' in validated_data and validated_data['radio_stab']['team_code']:
                    team_code = validated_data.pop('radio_stab')['team_code']
                    radio_stab, _ = RadioStab.objects.get_or_create(
                        team_code=team_code,
                        defaults={'name': f"{team_code} Rádiós Csapat"}
                    )
                
                osztaly = None
                if 'osztaly' in validated_data and all(k in validated_data['osztaly'] for k in ['startYear', 'szekcio']):
                    osztaly_data = validated_data.pop('osztaly')
                    osztaly, _ = Osztaly.objects.get_or_create(
                        startYear=osztaly_data['startYear'],
                        szekcio=osztaly_data['szekcio']
                    )
                
                return Profile.objects.create(
                    user=user,
                    stab=stab,
                    radio_stab=radio_stab,
                    osztaly=osztaly,
                    **validated_data
                )
                
        return ProfileImportSerializer


@registry.register
class OsztalyImport:
    """Class import wizard"""
    model = Osztaly
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class OsztalyImportSerializer(serializers.ModelSerializer):
            class Meta:
                model = Osztaly
                fields = ['startYear', 'szekcio']
                
        return OsztalyImportSerializer


@registry.register
class StabImport:
    """Stab (Team) import wizard"""
    model = Stab
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class StabImportSerializer(serializers.ModelSerializer):
            class Meta:
                model = Stab
                fields = ['name']
                
        return StabImportSerializer


@registry.register
class RadioStabImport:
    """Radio Stab import wizard"""
    model = RadioStab
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class RadioStabImportSerializer(serializers.ModelSerializer):
            class Meta:
                model = RadioStab
                fields = ['name', 'team_code', 'description']
                
        return RadioStabImportSerializer


@registry.register
class PartnerImport:
    """Partner import wizard"""
    model = Partner
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class PartnerImportSerializer(serializers.ModelSerializer):
            institution_name = serializers.CharField(source='institution.name', write_only=True, required=False)
            
            class Meta:
                model = Partner
                fields = ['name', 'address', 'institution_name', 'imgUrl']
                
            def create(self, validated_data):
                institution = None
                if 'institution' in validated_data and validated_data['institution']['name']:
                    institution, _ = PartnerTipus.objects.get_or_create(
                        name=validated_data.pop('institution')['name']
                    )
                
                return Partner.objects.create(
                    institution=institution,
                    **validated_data
                )
                
        return PartnerImportSerializer


@registry.register
class PartnerTipusImport:
    """Partner Type import wizard"""
    model = PartnerTipus
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class PartnerTipusImportSerializer(serializers.ModelSerializer):
            class Meta:
                model = PartnerTipus
                fields = ['name']
                
        return PartnerTipusImportSerializer


@registry.register
class EquipmentImport:
    """Equipment import wizard"""
    model = Equipment
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class EquipmentImportSerializer(serializers.ModelSerializer):
            equipment_type_name = serializers.CharField(source='equipmentType.name', write_only=True, required=False)
            
            class Meta:
                model = Equipment
                fields = [
                    'nickname', 'brand', 'model', 'serialNumber', 
                    'equipment_type_name', 'functional', 'notes'
                ]
                
            def create(self, validated_data):
                equipment_type = None
                if 'equipmentType' in validated_data and validated_data['equipmentType']['name']:
                    equipment_type, _ = EquipmentTipus.objects.get_or_create(
                        name=validated_data.pop('equipmentType')['name']
                    )
                
                return Equipment.objects.create(
                    equipmentType=equipment_type,
                    **validated_data
                )
                
        return EquipmentImportSerializer


@registry.register
class EquipmentTipusImport:
    """Equipment Type import wizard"""
    model = EquipmentTipus
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class EquipmentTipusImportSerializer(serializers.ModelSerializer):
            class Meta:
                model = EquipmentTipus
                fields = ['name', 'emoji']
                
        return EquipmentTipusImportSerializer


@registry.register
class ContactPersonImport:
    """Contact Person import wizard"""
    model = ContactPerson
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class ContactPersonImportSerializer(serializers.ModelSerializer):
            class Meta:
                model = ContactPerson
                fields = ['name', 'email', 'phone', 'context']
                
        return ContactPersonImportSerializer


@registry.register
class TanevImport:
    """School Year import wizard"""
    model = Tanev
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class TanevImportSerializer(serializers.ModelSerializer):
            class Meta:
                model = Tanev
                fields = ['start_date', 'end_date']
                
        return TanevImportSerializer
