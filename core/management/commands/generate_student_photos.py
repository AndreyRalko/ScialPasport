from django.core.management.base import BaseCommand

from core.minio_utils import ensure_minio_bucket
from core.models import Student
from core.photos import save_student_photo


class Command(BaseCommand):
    help = "Generates student portraits and uploads them to MinIO."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Replace existing photos")

    def handle(self, *args, **options):
        ensure_minio_bucket()
        created = 0
        students = list(Student.objects.all())
        for index, student in enumerate(students, start=1):
            if save_student_photo(student, force=options["force"]):
                created += 1
                self.stdout.write(f"[{index}/{len(students)}] {student.full_name}")
        self.stdout.write(self.style.SUCCESS(f"Student photos ready. Generated: {created}"))
