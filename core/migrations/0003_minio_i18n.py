from django.db import migrations, models


def add_reference_fields(model_name):
    return [
        migrations.AddField(
            model_name=model_name,
            name="name_ru",
            field=models.CharField(blank=True, max_length=255, verbose_name="Название (рус)"),
        ),
        migrations.AddField(
            model_name=model_name,
            name="code",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True, verbose_name="Код"),
        ),
    ]


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_alter_actionlog_options_and_more"),
    ]

    operations = [
        *add_reference_fields("adaptationlevel"),
        *add_reference_fields("communicationlevel"),
        *add_reference_fields("department"),
        *add_reference_fields("familyincomelevel"),
        *add_reference_fields("familytype"),
        *add_reference_fields("groupbehaviortype"),
        *add_reference_fields("healthgroup"),
        *add_reference_fields("housingtype"),
        *add_reference_fields("paymentform"),
        *add_reference_fields("responsibilitylevel"),
        *add_reference_fields("specialty"),
        *add_reference_fields("studygroup"),
        *add_reference_fields("temperamenttype"),
        *add_reference_fields("userrole"),
        migrations.AddField(
            model_name="student",
            name="photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="students/photos/",
                verbose_name="Фотография",
            ),
        ),
    ]
