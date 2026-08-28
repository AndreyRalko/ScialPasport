#!/bin/sh
set -e

echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
python - <<'PY'
import os
import time

import psycopg2

host = os.environ.get("POSTGRES_HOST", "db")
port = os.environ.get("POSTGRES_PORT", "5432")
name = os.environ.get("POSTGRES_DB", "social_passport")
user = os.environ.get("POSTGRES_USER", "social_passport")
password = os.environ.get("POSTGRES_PASSWORD", "social_passport")

for attempt in range(1, 31):
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=name,
            user=user,
            password=password,
        )
        conn.close()
        print("PostgreSQL is ready.")
        break
    except Exception as exc:
        print(f"Attempt {attempt}/30: {exc}")
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL is not available.")
PY

echo "Waiting for MinIO at ${MINIO_ENDPOINT_URL}..."
python - <<'PY'
import os
import time
import urllib.request

url = os.environ.get("MINIO_ENDPOINT_URL", "").rstrip("/") + "/minio/health/live"
if url.startswith("http"):
    for attempt in range(1, 31):
        try:
            urllib.request.urlopen(url, timeout=2)
            print("MinIO is ready.")
            break
        except Exception as exc:
            print(f"MinIO attempt {attempt}/30: {exc}")
            time.sleep(2)
    else:
        print("MinIO is not ready, continuing anyway.")
PY

python manage.py compilemessages --ignore .venv --ignore venv || true
python manage.py migrate --noinput
python manage.py ensure_minio
python manage.py seed_data
python manage.py seed_test_data --count 30
python manage.py generate_student_photos
python manage.py ensure_student_accounts

python - <<'PY'
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_passport.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from core.models import UserProfile, UserRole

User = get_user_model()
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@local")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin")

user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email, "is_staff": True, "is_superuser": True},
)
if created:
    user.set_password(password)
else:
    user.email = email
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password)
user.save()

role = (
    UserRole.objects.filter(code="userrole_admin").first()
    or UserRole.objects.filter(name_ru="Администратор системы").first()
    or UserRole.objects.filter(name="Жүйе әкімшісі").first()
)
profile, _ = UserProfile.objects.get_or_create(user=user)
if role and profile.role_id != role.id:
    profile.role = role
    profile.save()

group = (
    Group.objects.filter(name="Жүйе әкімшісі").first()
    or Group.objects.filter(name="Администратор системы").first()
)
if group:
    user.groups.add(group)

print(f"Admin user ready: {username}")
PY

exec "$@"
