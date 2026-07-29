import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assert_no_unowned_skill_entries(apps, schema_editor):
    SkillEntry = apps.get_model("skill_ledger", "SkillEntry")
    database_alias = schema_editor.connection.alias
    unowned_count = (
        SkillEntry.objects.using(database_alias).filter(user__isnull=True).count()
    )
    if unowned_count > 0:
        raise RuntimeError(
            f"Cannot enforce SkillEntry ownership: unowned_count={unowned_count}."
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("skill_ledger", "0002_skillentry_user"),
    ]

    operations = [
        migrations.RunPython(
            assert_no_unowned_skill_entries,
            reverse_code=noop_reverse,
        ),
        migrations.AlterField(
            model_name="skillentry",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="skill_entries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
