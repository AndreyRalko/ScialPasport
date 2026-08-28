from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from .cabinet import is_student_user

STUDENT_ALLOWED_PREFIXES = ("/cabinet/", "/logout/", "/i18n/", "/static/", "/media/")


class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, "profile", None)
            blocked = (profile is not None and profile.is_blocked) or not user.is_active
            if blocked:
                from .models import Student

                to_cabinet = Student.objects.filter(user_id=user.pk).exists()
                logout(request)
                messages.error(request, _("Учётная запись заблокирована или деактивирована."))
                return redirect("cabinet-login" if to_cabinet else "login")
        return self.get_response(request)


class StudentCabinetMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and is_student_user(user):
            path = request.path
            if not any(path.startswith(prefix) for prefix in STUDENT_ALLOWED_PREFIXES):
                return redirect("cabinet-home")
        return self.get_response(request)
