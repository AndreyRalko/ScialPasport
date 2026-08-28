import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from openpyxl import Workbook

from .filters import StudentFilter
from .forms import (
    ReferenceItemForm,
    StudentAcademicForm,
    StudentBenefitsForm,
    StudentFamilyForm,
    StudentFamilyMemberForm,
    StudentForm,
    StudentHousingForm,
    StudentMedicalForm,
    StudentPsychoProfileForm,
    UserManageForm,
)
from .models import (
    ActionLog,
    AdaptationLevel,
    CommunicationLevel,
    Department,
    FamilyIncomeLevel,
    FamilyType,
    GroupBehaviorType,
    HealthGroup,
    HousingType,
    PaymentForm,
    ResponsibilityLevel,
    Specialty,
    Student,
    StudentAIAnalysis,
    StudentFamily,
    StudyGroup,
    TemperamentType,
    UserProfile,
    UserRole,
)
from .dashboard import get_dashboard_stats
from .rag import answer_question
from .services import (
    build_ai_analysis,
    get_card_completion_export_rows,
    get_department_completion_report,
)


REFERENCE_GROUPS = [
    {
        "title": _lazy("Учебные"),
        "items": [
            {"key": "departments", "title": _lazy("Кафедры"), "model": Department},
            {"key": "specialties", "title": _lazy("Специальности"), "model": Specialty},
            {"key": "groups", "title": _lazy("Учебные группы"), "model": StudyGroup},
            {"key": "payment_forms", "title": _lazy("Формы оплаты"), "model": PaymentForm},
        ],
    },
    {
        "title": _lazy("Семья и жильё"),
        "items": [
            {"key": "family_types", "title": _lazy("Типы семьи"), "model": FamilyType},
            {"key": "income_levels", "title": _lazy("Материальное положение"), "model": FamilyIncomeLevel},
            {"key": "housing_types", "title": _lazy("Типы жилья"), "model": HousingType},
        ],
    },
    {
        "title": _lazy("Социально-психологические"),
        "items": [
            {"key": "temperaments", "title": _lazy("Темперамент"), "model": TemperamentType},
            {"key": "communication", "title": _lazy("Уровень общения"), "model": CommunicationLevel},
            {"key": "group_behavior", "title": _lazy("Поведение в группе"), "model": GroupBehaviorType},
            {"key": "responsibility", "title": _lazy("Ответственность"), "model": ResponsibilityLevel},
            {"key": "adaptation", "title": _lazy("Адаптация"), "model": AdaptationLevel},
        ],
    },
    {
        "title": _lazy("Медицинские"),
        "items": [
            {"key": "health_groups", "title": _lazy("Группы здоровья"), "model": HealthGroup},
        ],
    },
    {
        "title": _lazy("Системные"),
        "items": [
            {"key": "user_roles", "title": _lazy("Роли пользователей"), "model": UserRole},
        ],
    },
]

REFERENCE_MAP = {
    item["key"]: item
    for group in REFERENCE_GROUPS
    for item in group["items"]
}


def _staff_required(user):
    return user.is_staff


def _get_reference_config(key):
    return REFERENCE_MAP.get(key)


def log_action(request, action, description):
    if request.user.is_authenticated:
        ActionLog.objects.create(user=request.user, action=action, description=description)


STUDENT_PERSONAL_FIELDS = [
    "last_name", "first_name", "middle_name", "birth_date",
    "citizenship", "nationality", "iin", "phone", "photo",
]
STUDENT_ACADEMIC_FIELDS = ["department", "specialty", "course", "group", "payment_form"]


def _student_form_context(form, title, student=None):
    return {
        "form": form,
        "title": title,
        "student": student,
        "personal_fields": [form[name] for name in STUDENT_PERSONAL_FIELDS],
        "academic_fields": [form[name] for name in STUDENT_ACADEMIC_FIELDS],
    }


def _block_form_context(form, title, student, tab=None):
    back_url = f"/students/{student.pk}/"
    if tab:
        back_url += f"#{tab}"
    return {
        "form": form,
        "title": title,
        "subtitle": student.full_name,
        "back_url": back_url,
        "back_label": _("Назад к профилю"),
    }


class StaffLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        from .cabinet import is_student_user

        if is_student_user(self.request.user):
            return reverse("cabinet-home")
        return super().get_success_url()


@login_required
def home(request):
    from .cabinet import is_student_user

    if is_student_user(request.user):
        return redirect("cabinet-home")
    return render(request, "core/home.html", get_dashboard_stats())


@login_required
@require_POST
def assistant_ask(request):
    message = (request.POST.get("message") or "").strip()
    result = answer_question(message)
    log_action(request, "view_sensitive", _("Вопрос ИИ-ассистенту: %(q)s") % {"q": message[:180]})
    return JsonResponse(result)


@login_required
def student_list(request):
    qs = Student.objects.select_related(
        "department", "group", "specialty", "payment_form", "academic"
    ).prefetch_related("ai_analyses")
    student_filter = StudentFilter(request.GET, queryset=qs)
    high_risk = Student.objects.filter(ai_analyses__risk_level="high").distinct().count()
    low_adaptation = Student.objects.filter(
        Q(psycho__adaptation_level__code="adaptationlevel_low")
        | Q(psycho__adaptation_level__name__icontains="төмен")
        | Q(psycho__adaptation_level__name_ru__icontains="низ")
    ).distinct().count()
    problem_attendance = Student.objects.filter(academic__attendance="problematic").distinct().count()
    return render(
        request,
        "core/student_list.html",
        {
            "filter": student_filter,
            "students": student_filter.qs.distinct(),
            "high_risk_count": high_risk,
            "low_adaptation_count": low_adaptation,
            "problem_attendance_count": problem_attendance,
        },
    )


@login_required
def student_create(request):
    form = StudentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        student = form.save()
        StudentFamily.objects.get_or_create(student=student)
        log_action(request, "create", _("Создан студент: %(name)s") % {"name": student.full_name})
        return redirect("student-detail", pk=student.pk)
    return render(
        request,
        "core/student_form.html",
        _student_form_context(form, _("Добавить студента")),
    )


@login_required
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    form = StudentForm(request.POST or None, request.FILES or None, instance=student)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "update", _("Обновлен студент: %(name)s") % {"name": student.full_name})
        return redirect("student-detail", pk=student.pk)
    return render(
        request,
        "core/student_form.html",
        _student_form_context(form, _("Редактировать студента"), student),
    )


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    family, _ = StudentFamily.objects.get_or_create(student=student)
    context = {
        "student": student,
        "family": family,
        "members": family.members.all(),
        "housing": getattr(student, "housing", None),
        "psycho": getattr(student, "psycho", None),
        "academic": getattr(student, "academic", None),
        "medical": getattr(student, "medical", None),
        "benefits": getattr(student, "benefits", None),
        "latest_ai": student.ai_analyses.first(),
        "ai_history": student.ai_analyses.all()[:10],
        "cabinet_requests": student.cabinet_requests.all()[:10],
    }
    return render(request, "core/student_detail.html", context)


@login_required
def family_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    family, _ = StudentFamily.objects.get_or_create(student=student)
    form = StudentFamilyForm(request.POST or None, instance=family)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "update", f"Обновлен семейный блок: {student.full_name}")
        return redirect(f"/students/{pk}/#family")
    return render(
        request,
        "core/form.html",
        _block_form_context(form, _("Сведения о семье"), student, "family"),
    )


@login_required
def family_member_create(request, pk):
    student = get_object_or_404(Student, pk=pk)
    family, _ = StudentFamily.objects.get_or_create(student=student)
    form = StudentFamilyMemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        member = form.save(commit=False)
        member.family = family
        member.save()
        log_action(request, "create", f"Добавлен член семьи: {student.full_name}")
        return redirect(f"/students/{pk}/#family")
    return render(
        request,
        "core/form.html",
        _block_form_context(form, _("Добавить члена семьи"), student, "family"),
    )


@login_required
def family_member_delete(request, pk, member_id):
    student = get_object_or_404(Student, pk=pk)
    member = get_object_or_404(student.family.members, pk=member_id)
    member.delete()
    log_action(request, "delete", f"Удален член семьи: {student.full_name}")
    return redirect("student-detail", pk=pk)


def _edit_student_block(request, pk, rel_name, form_class, title, tab):
    student = get_object_or_404(Student, pk=pk)
    instance = getattr(student, rel_name, None)
    form = form_class(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.student = student
        obj.save()
        log_action(request, "update", f"Обновлен блок '{title}': {student.full_name}")
        return redirect(f"/students/{pk}/#{tab}")
    return render(
        request,
        "core/form.html",
        _block_form_context(form, title, student, tab),
    )


@login_required
def housing_edit(request, pk):
    return _edit_student_block(request, pk, "housing", StudentHousingForm, _("Жилищные условия"), "housing")


@login_required
def psycho_edit(request, pk):
    return _edit_student_block(
        request, pk, "psycho", StudentPsychoProfileForm,
        _("Социально-психологический профиль"), "psycho",
    )


@login_required
def academic_edit(request, pk):
    return _edit_student_block(request, pk, "academic", StudentAcademicForm, _("Учебная деятельность"), "academic")


@login_required
@permission_required("core.view_studentmedical", raise_exception=True)
def medical_edit(request, pk):
    log_action(request, "view_sensitive", "Доступ к медицинским данным")
    return _edit_student_block(request, pk, "medical", StudentMedicalForm, _("Медицинские сведения"), "medical")


@login_required
def benefits_edit(request, pk):
    return _edit_student_block(request, pk, "benefits", StudentBenefitsForm, _("Льготы и поддержка"), "benefits")


@login_required
def ai_generate(request, pk):
    student = get_object_or_404(Student, pk=pk)
    build_ai_analysis(student)
    messages.success(request, _("ИИ-анализ сформирован."))
    log_action(request, "create", f"Сформирован ИИ-анализ: {student.full_name}")
    return redirect("student-detail", pk=pk)


@login_required
def ai_analytics_page(request):
    qs = StudentAIAnalysis.objects.select_related("student")
    risk = request.GET.get("risk_level")
    if risk:
        qs = qs.filter(risk_level=risk)

    spotlight = Student.objects.filter(
        Q(ai_analyses__risk_level="high")
        | Q(psycho__adaptation_level__code="adaptationlevel_low")
        | Q(psycho__adaptation_level__name_ru__icontains="низ")
        | Q(academic__attendance="problematic")
    ).distinct()
    return render(request, "core/ai_analytics.html", {"analyses": qs[:100], "students": spotlight})


@login_required
def reports_page(request):
    return render(
        request,
        "core/reports.html",
        {"completion_report": get_department_completion_report()},
    )


def _report_queryset(report_key):
    query_map = {
        "low_income": Student.objects.filter(
            Q(family__income_level__code="familyincomelevel_low_income")
            | Q(family__income_level__name_ru__icontains="малообеспеч")
        ),
        "disability": Student.objects.filter(medical__has_disability=True),
        "dormitory": Student.objects.filter(
            Q(housing__housing_type__code="housingtype_dormitory")
            | Q(housing__housing_type__name_ru__icontains="общежит")
        ),
        "problem_attendance": Student.objects.filter(academic__attendance="problematic"),
        "low_adaptation": Student.objects.filter(
            Q(psycho__adaptation_level__code="adaptationlevel_low")
            | Q(psycho__adaptation_level__name_ru__icontains="низ")
        ),
        "high_risk_ai": Student.objects.filter(ai_analyses__risk_level="high"),
    }
    return query_map.get(report_key, Student.objects.none()).distinct()


@login_required
def export_report(request, report_key, fmt):
    if report_key == "card_completion":
        headers, rows = get_card_completion_export_rows()
        filename = "card_completion"
    else:
        headers = [_("ФИО"), _("ИИН"), _("Группа"), _("Курс"), _("Телефон")]
        rows = [
            [s.full_name, s.iin, s.group.name, s.course, s.phone]
            for s in _report_queryset(report_key)
        ]
        filename = report_key

    if fmt == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        writer.writerow(headers)
        writer.writerows(rows)
        return response

    wb = Workbook()
    ws = wb.active
    ws.title = "report"
    ws.append(headers)
    for row in rows:
        ws.append(row)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    wb.save(response)
    return response


@login_required
def action_logs(request):
    return redirect("admin-logs")


@login_required
@user_passes_test(_staff_required)
def settings_page(request):
    tab = request.GET.get("tab", "references")
    if tab == "users":
        return redirect("admin-users")
    ref_key = request.GET.get("ref", "departments")
    ref_config = _get_reference_config(ref_key)
    if not ref_config:
        ref_key = "departments"
        ref_config = REFERENCE_MAP["departments"]

    reference_items = []
    add_form = ReferenceItemForm()
    if tab == "references":
        model = ref_config["model"]
        reference_items = model._default_manager.order_by("name")
        if request.method == "POST" and request.POST.get("action") == "add_reference":
            add_form = ReferenceItemForm(request.POST)
            if add_form.is_valid():
                model.objects.create(
                    name=add_form.cleaned_data["name"],
                    name_ru=add_form.cleaned_data.get("name_ru", ""),
                    is_active=add_form.cleaned_data.get("is_active", True),
                )
                log_action(request, "create", f"Добавлен справочник: {ref_config['title']} — {add_form.cleaned_data['name']}")
                messages.success(request, _("Запись справочника добавлена."))
                return redirect(f"{request.path}?tab=references&ref={ref_key}")

    return render(
        request,
        "core/settings.html",
        {
            "tab": tab,
            "ref_key": ref_key,
            "ref_config": ref_config,
            "reference_groups": REFERENCE_GROUPS,
            "reference_items": reference_items,
            "add_form": add_form,
        },
    )


@login_required
@user_passes_test(_staff_required)
def reference_edit(request, key, pk):
    ref_config = _get_reference_config(key)
    if not ref_config:
        return redirect("settings")

    model = ref_config["model"]
    item = get_object_or_404(model, pk=pk)
    form = ReferenceItemForm(
        request.POST or None,
        initial={"name": item.name, "name_ru": item.name_ru, "is_active": item.is_active},
    )
    if request.method == "POST" and form.is_valid():
        item.name = form.cleaned_data["name"]
        item.name_ru = form.cleaned_data.get("name_ru", "")
        item.is_active = form.cleaned_data.get("is_active", False)
        item.save()
        log_action(request, "update", f"Обновлён справочник: {ref_config['title']} — {item.name}")
        messages.success(request, _("Запись справочника обновлена."))
        return redirect(f"/settings/?tab=references&ref={key}")

    return render(
        request,
        "core/form.html",
        {"form": form, "title": _("Редактировать: %(title)s") % {"title": ref_config["title"]}},
    )


@login_required
@user_passes_test(_staff_required)
def reference_toggle(request, key, pk):
    if request.method != "POST":
        return redirect("settings")

    ref_config = _get_reference_config(key)
    if not ref_config:
        return redirect("settings")

    item = get_object_or_404(ref_config["model"], pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active", "updated_at"])
    status = _("активирована") if item.is_active else _("деактивирована")
    log_action(request, "update", f"Запись справочника {status}: {item.name}")
    messages.success(request, _("Запись %(status)s.") % {"status": status})
    return redirect(f"/settings/?tab=references&ref={key}")


@login_required
@user_passes_test(_staff_required)
def user_create(request):
    return redirect("admin-user-create")


@login_required
@user_passes_test(_staff_required)
def user_edit(request, pk):
    return redirect("admin-user-edit", pk=pk)
