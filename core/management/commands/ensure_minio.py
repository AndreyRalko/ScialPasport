from django.core.management.base import BaseCommand

from core.minio_utils import ensure_minio_bucket


class Command(BaseCommand):
    help = "Creates the MinIO bucket and public-read policy."

    def handle(self, *args, **options):
        if ensure_minio_bucket():
            self.stdout.write(self.style.SUCCESS("MinIO bucket is ready."))
        else:
            self.stdout.write("MinIO is not configured, skipped.")
