# Generated for basic user permission scoping.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_meridiantest_age_meridiantest_birth_date_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='bfstest',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bfs_tests', to=settings.AUTH_USER_MODEL, verbose_name='使用者'),
        ),
        migrations.AddField(
            model_name='facediagnosis',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='face_diagnoses', to=settings.AUTH_USER_MODEL, verbose_name='使用者'),
        ),
        migrations.AddField(
            model_name='meridiantest',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='meridian_tests', to=settings.AUTH_USER_MODEL, verbose_name='使用者'),
        ),
    ]
