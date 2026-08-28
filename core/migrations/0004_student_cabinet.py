from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0003_minio_i18n"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="student_record",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Учётная запись кабинета",
            ),
        ),
        migrations.CreateModel(
            name="StudentRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "request_type",
                    models.CharField(
                        choices=[
                            ("data", "Уточнение данных"),
                            ("housing", "Жильё / общежитие"),
                            ("benefit", "Льгота / поддержка"),
                            ("consult", "Консультация"),
                            ("other", "Другое"),
                        ],
                        max_length=20,
                        verbose_name="Тип обращения",
                    ),
                ),
                ("message", models.TextField(verbose_name="Сообщение")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "Новая"),
                            ("in_progress", "В работе"),
                            ("done", "Закрыта"),
                        ],
                        default="new",
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cabinet_requests",
                        to="core.student",
                        verbose_name="Студент",
                    ),
                ),
            ],
            options={
                "verbose_name": "Обращение студента",
                "verbose_name_plural": "Обращения студентов",
                "ordering": ["-created_at"],
            },
        ),
    ]
