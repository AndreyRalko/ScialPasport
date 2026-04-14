from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import ActionLog


@receiver(user_logged_in)
def on_user_login(sender, request, user, **kwargs):
    ActionLog.objects.create(user=user, action="login", description="Вход в систему")


@receiver(user_logged_out)
def on_user_logout(sender, request, user, **kwargs):
    if user:
        ActionLog.objects.create(user=user, action="logout", description="Выход из системы")
