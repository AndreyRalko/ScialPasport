from django.contrib.auth.models import Group, Permission, User
from django.contrib.sessions.models import Session
from django.db.models import Count, Q
from django.utils import timezone

from .models import ActionLog, UserProfile, UserRole


CURATOR_PERMISSIONS = {
    "view_student",
    "add_student",
    "change_student",
    "view_studentfamily",
    "add_studentfamily",
    "change_studentfamily",
    "view_studentfamilymember",
    "add_studentfamilymember",
    "change_studentfamilymember",
    "delete_studentfamilymember",
    "view_studenthousing",
    "add_studenthousing",
    "change_studenthousing",
    "view_studentpsychoprofile",
    "add_studentpsychoprofile",
    "change_studentpsychoprofile",
    "view_studentacademic",
    "add_studentacademic",
    "change_studentacademic",
    "view_studentmedical",
    "view_studentbenefits",
    "add_studentbenefits",
    "change_studentbenefits",
    "view_studentaianalysis",
    "add_studentaianalysis",
}


def ensure_user_profiles():
    existing = set(UserProfile.objects.values_list("user_id", flat=True))
    missing = [UserProfile(user_id=user_id) for user_id in User.objects.values_list("id", flat=True) if user_id not in existing]
    if missing:
        UserProfile.objects.bulk_create(missing, ignore_conflicts=True)


def sync_role_group(role):
    if not role:
        return None
    group, _ = Group.objects.get_or_create(name=role.name)
    return group


def assign_default_group_permissions():
    core_perms = Permission.objects.filter(content_type__app_label="core")
    curator_perms = core_perms.filter(codename__in=CURATOR_PERMISSIONS)
    for role in UserRole.objects.all():
        group = sync_role_group(role)
        if not group:
            continue
        code = role.code or ""
        if code == "userrole_admin" or code.endswith("_admin"):
            group.permissions.set(core_perms)
        elif code == "userrole_student" or code.endswith("_student"):
            group.permissions.clear()
        elif not group.permissions.exists():
            group.permissions.set(curator_perms)


def sync_user_role_group(user, role):
    role_names = set(UserRole.objects.values_list("name", flat=True))
    current = user.groups.filter(name__in=role_names)
    if current:
        user.groups.remove(*current)
    group = sync_role_group(role)
    if group:
        user.groups.add(group)


def iter_active_sessions():
    ensure_user_profiles()
    users = {
        str(user.pk): user
        for user in User.objects.select_related("profile", "profile__role").order_by("username")
    }
    rows = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()).order_by("-expire_date"):
        data = session.get_decoded()
        user = users.get(str(data.get("_auth_user_id") or ""))
        rows.append(
            {
                "session_key": session.session_key,
                "expire_date": session.expire_date,
                "user": user,
            }
        )
    return rows


def session_counts_by_user():
    counts = {}
    for row in iter_active_sessions():
        if row["user"]:
            counts[row["user"].pk] = counts.get(row["user"].pk, 0) + 1
    return counts


def terminate_session(session_key):
    Session.objects.filter(session_key=session_key).delete()


def terminate_user_sessions(user_id, keep_key=None):
    deleted = 0
    for row in iter_active_sessions():
        if not row["user"] or row["user"].pk != user_id:
            continue
        if keep_key and row["session_key"] == keep_key:
            continue
        terminate_session(row["session_key"])
        deleted += 1
    return deleted


def get_admin_stats():
    ensure_user_profiles()
    users = User.objects.all()
    sessions = iter_active_sessions()
    return {
        "total_users": users.count(),
        "staff_users": users.filter(is_staff=True).count(),
        "superusers": users.filter(is_superuser=True).count(),
        "active_users": users.filter(is_active=True, profile__is_blocked=False).count(),
        "blocked_users": users.filter(Q(is_active=False) | Q(profile__is_blocked=True)).distinct().count(),
        "active_sessions": len(sessions),
        "roles_count": UserRole.objects.count(),
        "groups_count": Group.objects.count(),
        "recent_logins": users.filter(last_login__isnull=False).select_related("profile", "profile__role").order_by("-last_login")[:8],
        "recent_admin_logs": ActionLog.objects.select_related("user").filter(
            action__in=["login", "logout", "create", "update", "delete"]
        )[:8],
        "role_bars": [
            {
                "role": role,
                "count": role.user_count,
                "pct": round(role.user_count * 100 / max(users.count(), 1)),
            }
            for role in UserRole.objects.annotate(user_count=Count("userprofile")).order_by("name")
        ],
    }
