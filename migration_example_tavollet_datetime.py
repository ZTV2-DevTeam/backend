"""
Data migration script for converting Tavollet DateField to DateTimeField.

This script handles the conversion of existing date-only records to datetime
with appropriate default times to maintain logical absence periods.
"""

from django.db import migrations
from django.utils import timezone
from datetime import datetime, time


def convert_dates_to_datetimes(apps, schema_editor):
    """
    Convert existing date fields to datetime fields with appropriate times.
    
    Strategy:
    - start_date -> start_date 00:00:00 (beginning of day)
    - end_date -> end_date 23:59:59 (end of day)
    
    This ensures that existing absence periods maintain their logical coverage.
    """
    Tavollet = apps.get_model('api', 'Tavollet')
    
    # Process in batches to avoid memory issues with large datasets
    batch_size = 1000
    total_updated = 0
    
    # Get all records that need conversion
    queryset = Tavollet.objects.all()
    total_records = queryset.count()
    
    print(f"Converting {total_records} Tavollet records...")
    
    for i in range(0, total_records, batch_size):
        batch = queryset[i:i + batch_size]
        
        for tavollet in batch:
            # Convert start_date to beginning of day
            if hasattr(tavollet.start_date, 'date'):
                # Already datetime, skip
                continue
                
            start_datetime = datetime.combine(
                tavollet.start_date,
                time.min  # 00:00:00
            )
            
            # Convert end_date to end of day
            end_datetime = datetime.combine(
                tavollet.end_date,
                time(23, 59, 59)  # 23:59:59
            )
            
            # Make timezone aware if settings.USE_TZ is True
            if timezone.is_naive(start_datetime):
                start_datetime = timezone.make_aware(start_datetime)
            if timezone.is_naive(end_datetime):
                end_datetime = timezone.make_aware(end_datetime)
            
            # Update the record
            tavollet.start_date = start_datetime
            tavollet.end_date = end_datetime
            tavollet.save(update_fields=['start_date', 'end_date'])
            
            total_updated += 1
        
        print(f"Processed {min(i + batch_size, total_records)}/{total_records} records...")
    
    print(f"Successfully converted {total_updated} Tavollet records to datetime format.")


def reverse_conversion(apps, schema_editor):
    """
    Reverse the conversion by extracting date from datetime fields.
    
    This is used if the migration needs to be rolled back.
    """
    Tavollet = apps.get_model('api', 'Tavollet')
    
    batch_size = 1000
    total_updated = 0
    
    queryset = Tavollet.objects.all()
    total_records = queryset.count()
    
    print(f"Reverting {total_records} Tavollet records to date format...")
    
    for i in range(0, total_records, batch_size):
        batch = queryset[i:i + batch_size]
        
        for tavollet in batch:
            # Extract date from datetime
            if hasattr(tavollet.start_date, 'date'):
                start_date = tavollet.start_date.date()
                end_date = tavollet.end_date.date()
                
                tavollet.start_date = start_date
                tavollet.end_date = end_date
                tavollet.save(update_fields=['start_date', 'end_date'])
                
                total_updated += 1
        
        print(f"Reverted {min(i + batch_size, total_records)}/{total_records} records...")
    
    print(f"Successfully reverted {total_updated} Tavollet records to date format.")


class Migration(migrations.Migration):
    """
    Django migration for converting Tavollet date fields to datetime fields.
    """
    
    dependencies = [
        ('api', '0004_config_contactperson_equipmenttipus_osztaly_and_more'),  # Update this to your latest migration
    ]

    operations = [
        # First, run the data conversion before schema change
        migrations.RunPython(
            convert_dates_to_datetimes,
            reverse_conversion,
            hints={'target_db': 'default'}
        ),
        
        # Then alter the field types
        migrations.AlterField(
            model_name='tavollet',
            name='start_date',
            field=models.DateTimeField(
                help_text='A távollét kezdő időpontja (dátum és idő)',
                verbose_name='Kezdő időpont'
            ),
        ),
        migrations.AlterField(
            model_name='tavollet',
            name='end_date',
            field=models.DateTimeField(
                help_text='A távollét záró időpontja (dátum és idő)',
                verbose_name='Záró időpont'
            ),
        ),
    ]
