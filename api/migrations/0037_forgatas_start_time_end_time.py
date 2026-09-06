from datetime import datetime

from django.db import migrations, models


def populate_start_end_time(apps, schema_editor):
    """Combine legacy date + timeFrom/timeTo into the new start_time/end_time datetimes."""
    Forgatas = apps.get_model('api', 'Forgatas')

    batch_size = 1000
    queryset = Forgatas.objects.all()
    total = queryset.count()
    print(f"Migrating {total} Forgatas records to start_time/end_time...")

    for i in range(0, total, batch_size):
        batch = list(queryset[i:i + batch_size])
        for forgatas in batch:
            forgatas.start_time = datetime.combine(forgatas.date, forgatas.timeFrom)
            forgatas.end_time = datetime.combine(forgatas.date, forgatas.timeTo)
            forgatas.save(update_fields=['start_time', 'end_time'])
        print(f"Processed {min(i + batch_size, total)}/{total} records...")

    print(f"Successfully migrated {total} Forgatas records.")


def reverse_populate_start_end_time(apps, schema_editor):
    """Reverse migration is a no-op: legacy date/timeFrom/timeTo fields were never modified."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0036_merge_20260906_1705'),
    ]

    operations = [
        migrations.AddField(
            model_name='forgatas',
            name='start_time',
            field=models.DateTimeField(null=True, blank=True, verbose_name='Kezdés időpontja',
                                        help_text='A forgatás kezdésének dátuma és időpontja'),
        ),
        migrations.AddField(
            model_name='forgatas',
            name='end_time',
            field=models.DateTimeField(null=True, blank=True, verbose_name='Befejezés időpontja',
                                        help_text='A forgatás befejezésének dátuma és időpontja'),
        ),
        migrations.RunPython(populate_start_end_time, reverse_populate_start_end_time),
        migrations.AlterField(
            model_name='forgatas',
            name='start_time',
            field=models.DateTimeField(blank=False, null=False, verbose_name='Kezdés időpontja',
                                        help_text='A forgatás kezdésének dátuma és időpontja'),
        ),
        migrations.AlterField(
            model_name='forgatas',
            name='end_time',
            field=models.DateTimeField(blank=False, null=False, verbose_name='Befejezés időpontja',
                                        help_text='A forgatás befejezésének dátuma és időpontja'),
        ),
        migrations.AlterField(
            model_name='forgatas',
            name='date',
            field=models.DateField(blank=True, null=True, verbose_name='Dátum (elavult)',
                                    help_text='Elavult mező, lásd: start_time/end_time'),
        ),
        migrations.AlterField(
            model_name='forgatas',
            name='timeFrom',
            field=models.TimeField(blank=True, null=True, verbose_name='Kezdés ideje (elavult)',
                                    help_text='Elavult mező, lásd: start_time'),
        ),
        migrations.AlterField(
            model_name='forgatas',
            name='timeTo',
            field=models.TimeField(blank=True, null=True, verbose_name='Befejezés ideje (elavult)',
                                    help_text='Elavult mező, lásd: end_time'),
        ),
        migrations.AlterModelOptions(
            name='forgatas',
            options={'ordering': ['start_time'], 'verbose_name': 'Forgatás', 'verbose_name_plural': 'Forgatások'},
        ),
    ]
