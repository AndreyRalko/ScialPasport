from django.db.models import Count, Q
from django.urls import reverse
from django.utils.translation import gettext as _

from .models import ActionLog, Student, StudentAIAnalysis
from .services import get_department_completion_report


def _low_adaptation_q():
    return (
        Q(psycho__adaptation_level__code="adaptationlevel_low")
        | Q(psycho__adaptation_level__name__icontains="төмен")
        | Q(psycho__adaptation_level__name_ru__icontains="низ")
    )


def _low_income_q():
    return (
        Q(family__income_level__code="familyincomelevel_low_income")
        | Q(family__income_level__name_ru__icontains="малообеспеч")
        | Q(family__income_level__name__icontains="аз қамтылған")
    )


def _dormitory_q():
    return (
        Q(housing__housing_type__code="housingtype_dormitory")
        | Q(housing__housing_type__name_ru__icontains="общежит")
        | Q(housing__housing_type__name__icontains="жатақхана")
    )


def get_dashboard_stats():
    students = Student.objects.all()
    total = students.count()
    high_risk = students.filter(ai_analyses__risk_level="high").distinct().count()
    medium_risk = students.filter(ai_analyses__risk_level="medium").distinct().count()
    low_risk = students.filter(ai_analyses__risk_level="low").distinct().count()
    no_ai = students.filter(ai_analyses__isnull=True).count()
    low_adaptation = students.filter(_low_adaptation_q()).distinct().count()
    problem_attendance = students.filter(academic__attendance="problematic").count()
    low_income = students.filter(_low_income_q()).distinct().count()
    dormitory = students.filter(_dormitory_q()).distinct().count()
    disability = students.filter(medical__has_disability=True).count()
    grant = students.filter(
        Q(payment_form__code="paymentform_grant") | Q(payment_form__name="грант")
    ).count()

    risk_total = max(total, 1)
    course_counts = list(
        students.values("course").annotate(count=Count("id")).order_by("course")
    )
    max_course = max((row["count"] for row in course_counts), default=1)

    attention = (
        students.filter(
            Q(ai_analyses__risk_level="high")
            | _low_adaptation_q()
            | Q(academic__attendance="problematic")
        )
        .select_related("group", "department", "academic")
        .prefetch_related("ai_analyses")
        .distinct()[:8]
    )
    attention_items = []
    for student in attention:
        latest = student.ai_analyses.first()
        attention_items.append(
            {
                "student": student,
                "risk": latest.risk_level if latest else "",
                "risk_label": latest.get_risk_level_display() if latest else _("Нет анализа"),
            }
        )

    recent_logs = ActionLog.objects.select_related("user")[:8]
    completion = get_department_completion_report()

    return {
        "total_students": total,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "no_ai": no_ai,
        "low_adaptation": low_adaptation,
        "problem_attendance": problem_attendance,
        "low_income": low_income,
        "dormitory": dormitory,
        "disability": disability,
        "grant": grant,
        "risk_bars": [
            {"key": "high", "label": _("Высокий"), "count": high_risk, "pct": round(high_risk * 100 / risk_total)},
            {"key": "medium", "label": _("Средний"), "count": medium_risk, "pct": round(medium_risk * 100 / risk_total)},
            {"key": "low", "label": _("Низкий"), "count": low_risk, "pct": round(low_risk * 100 / risk_total)},
        ],
        "course_bars": [
            {
                "label": _("Курс %(n)s") % {"n": row["course"]},
                "count": row["count"],
                "pct": round(row["count"] * 100 / max_course) if max_course else 0,
            }
            for row in course_counts
        ],
        "completion": completion,
        "attention": attention_items,
        "recent_logs": recent_logs,
        "quick_actions": [
            {"title": _("Добавить студента"), "hint": _("Новая карточка"), "url": reverse("student-create"), "tone": "primary"},
            {"title": _("Студенты"), "hint": _("Список и фильтры"), "url": reverse("student-list"), "tone": "blue"},
            {"title": _("Высокий риск"), "hint": _("ИИ-выборка"), "url": reverse("ai-analytics") + "?risk_level=high", "tone": "red"},
            {"title": _("Проблемная посещаемость"), "hint": _("Отчёт"), "url": reverse("report-export", args=["problem_attendance", "xlsx"]), "tone": "orange"},
            {"title": _("Отчёты"), "hint": _("Выгрузки"), "url": reverse("reports"), "tone": "blue"},
            {"title": _("ИИ-аналитика"), "hint": _("Зона внимания"), "url": reverse("ai-analytics"), "tone": "violet"},
            {"title": _("Журнал действий"), "hint": _("Аудит"), "url": reverse("admin-logs"), "tone": "gray"},
            {"title": _("Справочники"), "hint": _("Настройки"), "url": reverse("settings"), "tone": "gray"},
            {"title": _("Админ-панель"), "hint": _("Пользователи и сессии"), "url": reverse("admin-panel"), "tone": "violet"},
        ],
    }
