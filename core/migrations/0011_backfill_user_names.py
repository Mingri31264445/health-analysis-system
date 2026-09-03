from django.db import migrations


def backfill_user_names(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Questionnaire = apps.get_model("core", "Questionnaire")

    questionnaires = Questionnaire.objects.exclude(user_id__isnull=True).exclude(name="")
    for questionnaire in questionnaires.iterator():
        normalized_name = " ".join(questionnaire.name.strip().split())
        if not normalized_name:
            continue

        if " " in normalized_name:
            last_name, first_name = normalized_name.split(" ", 1)
        elif len(normalized_name) == 1:
            last_name, first_name = "", normalized_name
        else:
            last_name, first_name = normalized_name[0], normalized_name[1:]

        user = User.objects.filter(pk=questionnaire.user_id).first()
        if user and not user.last_name and (
            not user.first_name or user.first_name == normalized_name
        ):
            user.last_name = last_name
            user.first_name = first_name
            user.save(update_fields=["last_name", "first_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_create_researcher_group"),
    ]

    operations = [
        migrations.RunPython(backfill_user_names, migrations.RunPython.noop),
    ]
