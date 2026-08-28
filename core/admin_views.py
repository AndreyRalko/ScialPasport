from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .admin_panel import (
    assign_default_group_permissions,
    ensure_user_profiles,
    get_admin_stats,
    iter_active_sessions,
    session_counts_by_user,
    sync_role_group,
    terminate_session,
    terminate_user_sessions,
)
from .forms import AISettingsForm, GroupManageForm, ReferenceItemForm, UserManageForm
from .llm import LLMError, ping
from .models import AISettings, ActionLog, UserRole
from .views import _staff_required, log_action


def _admin_tabs(section):
    return {
        "section": section,
        "admin_tabs": [
            {"key": "overview", "title": _("Обзор"), "url_name": "admin-panel"},
            {"key": "users", "title": _("Пользователи"), "url_name": "admin-users"},
            {"key": "sessions", "title": _("Сессии"), "url_name": "admin-sessions"},
            {"key": "roles", "title": _("Роли"), "url_name": "admin-roles"},
            {"key": "groups", "title": _("Группы и права"), "url_name": "admin-groups"},
            {"key": "ai", "title": _("ИИ и API"), "url_name": "admin-ai"},
            {"key": "logs", "title": _("Журнал действий"), "url_name": "admin-logs"},
        ],
    }


@login_required
@user_passes_test(_staff_required)
def admin_overview(request):
    assign_default_group_permissions()
    context = _admin_tabs("overview")
    context.update(get_admin_stats())
    return render(request, "core/admin_overview.html", context)


@login_required
@user_passes_test(_staff_required)
def admin_users(request):
    ensure_user_profiles()
    query = request.GET.get("q", "").strip()
    role_id = request.GET.get("role", "")
    status = request.GET.get("status", "")
    users = (
        User.objects.select_related("profile", "profile__role")
        .prefetch_related("profile__departments", "groups")
        .order_by("username")
    )
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )
    if role_id.isdigit():
        users = users.filter(profile__role_id=int(role_id))
    if status == "staff":
        users = users.filter(is_staff=True)
    elif status == "blocked":
        users = users.filter(Q(is_active=False) | Q(profile__is_blocked=True))
    elif status == "active":
        users = users.filter(is_active=True, profile__is_blocked=False)
    counts = session_counts_by_user()
    users = list(users)
    for user in users:
        user.session_count = counts.get(user.pk, 0)
    context = _admin_tabs("users")
    context.update(
        {
            "users": users,
            "roles": UserRole.objects.active(),
            "query": query,
            "role_id": role_id,
            "status": status,
        }
    )
    return render(request, "core/admin_users.html", context)


@login_required
@user_passes_test(_staff_required)
def admin_user_create(request):
    form = UserManageForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_action(request, "create", f"Создан пользователь: {user.username}")
        messages.success(request, _("Пользователь создан."))
        return redirect("admin-users")
    context = _admin_tabs("users")
    context.update({"form": form, "title": _("Новый пользователь"), "back_url": "admin-users"})
    return render(request, "core/settings_user_form.html", context)


@login_required
@user_passes_test(_staff_required)
def admin_user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = UserManageForm(request.POST or None, instance=user_obj, request=request)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "update", f"Обновлён пользователь: {user_obj.username}")
        messages.success(request, _("Пользователь обновлён."))
        return redirect("admin-users")
    context = _admin_tabs("users")
    context.update(
        {
            "form": form,
            "title": _("Редактировать: %(name)s") % {"name": user_obj.username},
            "back_url": "admin-users",
        }
    )
    return render(request, "core/settings_user_form.html", context)


@login_required
@user_passes_test(_staff_required)
@require_POST
def admin_user_toggle_block(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj.pk == request.user.pk:
        messages.error(request, _("Нельзя заблокировать собственную учётную запись."))
        return redirect("admin-users")
    from .models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=user_obj)
    profile.is_blocked = not profile.is_blocked
    profile.save(update_fields=["is_blocked"])
    if profile.is_blocked:
        user_obj.is_active = False
        user_obj.save(update_fields=["is_active"])
        terminate_user_sessions(user_obj.pk)
        log_action(request, "update", f"Заблокирован пользователь: {user_obj.username}")
        messages.success(request, _("Пользователь заблокирован, сессии завершены."))
    else:
        user_obj.is_active = True
        user_obj.save(update_fields=["is_active"])
        log_action(request, "update", f"Разблокирован пользователь: {user_obj.username}")
        messages.success(request, _("Пользователь разблокирован."))
    return redirect("admin-users")


@login_required
@user_passes_test(_staff_required)
@require_POST
def admin_user_logout_all(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    keep = request.session.session_key if user_obj.pk == request.user.pk else None
    deleted = terminate_user_sessions(user_obj.pk, keep_key=keep)
    log_action(request, "update", f"Завершены сессии пользователя: {user_obj.username}")
    messages.success(request, _("Завершено сессий: %(n)s") % {"n": deleted})
    return redirect(request.POST.get("next") or "admin-users")


@login_required
@user_passes_test(_staff_required)
def admin_sessions(request):
    context = _admin_tabs("sessions")
    context.update(
        {
            "sessions": iter_active_sessions(),
            "current_session_key": request.session.session_key,
        }
    )
    return render(request, "core/admin_sessions.html", context)


@login_required
@user_passes_test(_staff_required)
@require_POST
def admin_session_terminate(request, session_key):
    if session_key == request.session.session_key:
        messages.error(request, _("Нельзя завершить текущую сессию."))
        return redirect("admin-sessions")
    terminate_session(session_key)
    log_action(request, "delete", f"Завершена сессия {session_key[:8]}…")
    messages.success(request, _("Сессия завершена."))
    return redirect("admin-sessions")


@login_required
@user_passes_test(_staff_required)
def admin_roles(request):
    assign_default_group_permissions()
    add_form = ReferenceItemForm(request.POST or None)
    if request.method == "POST" and request.POST.get("action") == "add_role" and add_form.is_valid():
        role = UserRole.objects.create(
            name=add_form.cleaned_data["name"],
            name_ru=add_form.cleaned_data.get("name_ru", ""),
            is_active=add_form.cleaned_data.get("is_active", True),
        )
        sync_role_group(role)
        log_action(request, "create", f"Создана роль: {role.name}")
        messages.success(request, _("Роль добавлена."))
        return redirect("admin-roles")
    roles = UserRole.objects.annotate(user_count=Count("userprofile")).order_by("name")
    context = _admin_tabs("roles")
    context.update({"roles": roles, "add_form": add_form})
    return render(request, "core/admin_roles.html", context)


@login_required
@user_passes_test(_staff_required)
def admin_role_edit(request, pk):
    role = get_object_or_404(UserRole, pk=pk)
    form = ReferenceItemForm(
        request.POST or None,
        initial={"name": role.name, "name_ru": role.name_ru, "is_active": role.is_active},
    )
    if request.method == "POST" and form.is_valid():
        role.name = form.cleaned_data["name"]
        role.name_ru = form.cleaned_data.get("name_ru", "")
        role.is_active = form.cleaned_data.get("is_active", False)
        role.save()
        sync_role_group(role)
        log_action(request, "update", f"Обновлена роль: {role.name}")
        messages.success(request, _("Роль обновлена."))
        return redirect("admin-roles")
    return render(
        request,
        "core/form.html",
        {
            "form": form,
            "title": _("Редактировать роль"),
            "back_url": "/administration/roles/",
            "back_label": _("К ролям"),
        },
    )


@login_required
@user_passes_test(_staff_required)
@require_POST
def admin_role_toggle(request, pk):
    role = get_object_or_404(UserRole, pk=pk)
    role.is_active = not role.is_active
    role.save(update_fields=["is_active", "updated_at"])
    status = _("активирована") if role.is_active else _("деактивирована")
    log_action(request, "update", f"Роль {status}: {role.name}")
    messages.success(request, _("Роль %(status)s.") % {"status": status})
    return redirect("admin-roles")


@login_required
@user_passes_test(_staff_required)
def admin_groups(request):
    assign_default_group_permissions()
    groups = Group.objects.annotate(
        user_count=Count("user", distinct=True),
        perm_count=Count("permissions", distinct=True),
    ).order_by("name")
    context = _admin_tabs("groups")
    context.update({"groups": groups})
    return render(request, "core/admin_groups.html", context)


@login_required
@user_passes_test(_staff_required)
def admin_group_edit(request, pk=None):
    group = get_object_or_404(Group, pk=pk) if pk else None
    form = GroupManageForm(request.POST or None, instance=group)
    if request.method == "POST" and form.is_valid():
        group = form.save()
        log_action(request, "update" if pk else "create", f"Группа доступа: {group.name}")
        messages.success(request, _("Группа сохранена."))
        return redirect("admin-groups")
    context = _admin_tabs("groups")
    context.update(
        {
            "form": form,
            "title": _("Редактировать группу") if pk else _("Новая группа"),
        }
    )
    return render(request, "core/admin_group_form.html", context)


@login_required
@user_passes_test(_staff_required)
def admin_ai_settings(request):
    settings_obj = AISettings.load()
    form = AISettingsForm(
        request.POST or None,
        settings=settings_obj,
        initial={
            "provider": settings_obj.provider,
            "model": settings_obj.model,
            "is_enabled": settings_obj.is_enabled,
        },
    )
    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action") or "save"
        settings_obj.provider = form.cleaned_data["provider"]
        settings_obj.model = form.cleaned_data["model"]
        settings_obj.api_key = form.cleaned_data.get("api_key") or ""
        settings_obj.is_enabled = form.cleaned_data.get("is_enabled", False)
        settings_obj.updated_by = request.user
        if action == "test":
            try:
                ping(settings_obj)
            except LLMError as exc:
                messages.error(request, _("Проверка не удалась: %(error)s") % {"error": exc})
                context = _admin_tabs("ai")
                context.update({"form": form, "ai_settings": settings_obj})
                return render(request, "core/admin_ai.html", context)
            settings_obj.save()
            log_action(request, "update", "Проверен доступ к модели ИИ")
            messages.success(
                request,
                _("Подключение успешно: %(provider)s / %(model)s.")
                % {"provider": settings_obj.get_provider_display(), "model": settings_obj.model},
            )
            return redirect("admin-ai")
        settings_obj.save()
        log_action(
            request,
            "update",
            f"Обновлены настройки ИИ: {settings_obj.get_provider_display()} / {settings_obj.model}",
        )
        messages.success(request, _("Настройки ИИ сохранены."))
        return redirect("admin-ai")
    context = _admin_tabs("ai")
    context.update({"form": form, "ai_settings": settings_obj})
    return render(request, "core/admin_ai.html", context)


@login_required
@user_passes_test(_staff_required)
def admin_logs(request):
    query = request.GET.get("q", "").strip()
    action = request.GET.get("action", "").strip()
    logs = ActionLog.objects.select_related("user")
    if query:
        logs = logs.filter(
            Q(description__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
        )
    if action:
        logs = logs.filter(action=action)
    context = _admin_tabs("logs")
    context.update(
        {
            "logs": logs[:300],
            "query": query,
            "action": action,
            "action_choices": ActionLog.ACTIONS,
        }
    )
    return render(request, "core/admin_logs.html", context)
