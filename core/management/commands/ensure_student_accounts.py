from django.core.management.base import BaseCommand

from core.cabinet import DEMO_CABINET_PASSWORD, ensure_student_account
from core.models import Student


class Command(BaseCommand):
    help = "Создаёт учётные записи кабинета для студентов без входа."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help=f"Сбросить пароли кабинета на {DEMO_CABINET_PASSWORD}",
        )

    def handle(self, *args, **options):
        created = 0
        linked = 0
        reset = options["reset_passwords"]
        for student in Student.objects.all():
            before = student.user_id
            user, was_created = ensure_student_account(student, reset_password=reset)
            if was_created:
                created += 1
            elif before != user.pk:
                linked += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Кабинет: создано {created}, привязано {linked}. "
                f"Демо-пароль: {DEMO_CABINET_PASSWORD}"
            )
        )
