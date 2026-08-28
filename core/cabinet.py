from django.contrib.auth.models import User

from .models import Student, UserProfile, UserRole

DEMO_CABINET_PASSWORD = "Student12345"


def is_student_user(user):
    if not user or not getattr(user, "is_authenticated", False) or user.is_staff or user.is_superuser:
        return False
    return Student.objects.filter(user_id=user.pk).exists()


def get_cabinet_student(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return Student.objects.filter(user_id=user.pk).select_related(
        "group", "department", "specialty", "payment_form"
    ).first()


def ensure_student_account(student, password=DEMO_CABINET_PASSWORD, reset_password=False):
    role = UserRole.objects.filter(code="userrole_student").first()
    user = student.user
    created = False
    if user is None:
        user = User.objects.filter(username=student.iin).first()
        if user is None:
            user = User(username=student.iin, first_name=student.first_name, last_name=student.last_name)
            user.set_password(password)
            user.is_staff = False
            user.is_superuser = False
            user.save()
            created = True
        student.user = user
        student.save(update_fields=["user"])
    elif reset_password:
        user.set_password(password)
        user.save(update_fields=["password"])

    user.first_name = student.first_name
    user.last_name = student.last_name
    user.is_staff = False
    user.is_superuser = False
    updates = ["first_name", "last_name", "is_staff", "is_superuser"]
    if student.iin and user.username != student.iin:
        taken = User.objects.filter(username=student.iin).exclude(pk=user.pk).exists()
        if not taken:
            user.username = student.iin
            updates.append("username")
    user.save(update_fields=updates)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if role and profile.role_id != role.id:
        profile.role = role
        profile.save(update_fields=["role"])
    return user, created
