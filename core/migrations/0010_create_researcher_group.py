from django.db import migrations


def create_researcher_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="研究人員")


def delete_researcher_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="研究人員").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0009_add_record_owners"),
    ]

    operations = [
        migrations.RunPython(create_researcher_group, delete_researcher_group),
    ]
