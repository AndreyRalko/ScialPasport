import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
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
from .services import (
    build_ai_analysis,
    get_card_completion_export_rows,
    get_department_completion_report,
)


REFERENCE_GROUPS = [
    {
        "title": "Учебные",
        "items": [
            {"key": "departments", "title": "Кафедры", "model": Department},
            {"key": "specialties", "title": "Специальности", "model": Specialty},
            {"key": "groups", "title": "Учебные группы", "model": StudyGroup},
            {"key": "payment_forms", "title": "Формы оплаты", "model": PaymentForm},
        ],
    },
    {
        "title": "Семья и жильё",
        "items": [
            {"key": "family_types", "title": "Типы семьи", "model": FamilyType},
            {"key": "income_levels", "title": "Материальное положение", "model": FamilyIncomeLevel},
            {"key": "housing_types", "title": "Типы жилья", "model": HousingType},
        ],
    },
    {
        "title": "Социально-психологические",
        "items": [
            {"key": "temperaments", "title": "Темперамент", "model": TemperamentType},
            {"key": "communication", "title": "Уровень общения", "model": CommunicationLevel},
            {"key": "group_behavior", "title": "Поведение в группе", "model": GroupBehaviorType},
            {"key": "responsibility", "title": "Ответственность", "model": ResponsibilityLevel},
            {"key": "adaptation", "title": "Адаптация", "model": AdaptationLevel},
        ],
    },
    {
        "title": "Медицинские",
        "items": [
            {"key": "health_groups", "title": "Группы здоровья", "model": HealthGroup},
        ],
    },
    {
        "title": "Системные",
        "items": [
            {"key": "user_roles", "title": "Роли пользователей", "model": UserRole},
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
    "citizenship", "nationality", "iin", "phone",
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
        "back_label": "Назад к профилю",
    }


@login_required
def student_list(request):
    qs = Student.objects.select_related(
        "department", "group", "specialty", "payment_form"
    ).prefetch_related("ai_analyses")
    student_filter = StudentFilter(request.GET, queryset=qs)
    high_risk = Student.objects.filter(ai_analyses__risk_level="high").distinct().count()
    low_adaptation = Student.objects.filter(psycho__adaptation_level__name__icontains="низ").distinct().count()
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
    form = StudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student = form.save()
        StudentFamily.objects.get_or_create(student=student)
        log_action(request, "create", f"Создан студент: {student.full_name}")
        return redirect("student-detail", pk=student.pk)
    return render(
        request,
        "core/student_form.html",
        _student_form_context(form, "Добавить студента"),
    )


@login_required
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    form = StudentForm(request.POST or None, instance=student)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "update", f"Обновлен студент: {student.full_name}")
        return redirect("student-detail", pk=student.pk)
    return render(
        request,
        "core/student_form.html",
        _student_form_context(form, "Редактировать студента", student),
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
        _block_form_context(form, "Сведения о семье", student, "family"),
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
        _block_form_context(form, "Добавить члена семьи", student, "family"),
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
    return _edit_student_block(request, pk, "housing", StudentHousingForm, "Жилищные условия", "housing")


@login_required
def psycho_edit(request, pk):
    return _edit_student_block(
        request, pk, "psycho", StudentPsychoProfileForm,
        "Социально-психологический профиль", "psycho",
    )


@login_required
def academic_edit(request, pk):
    return _edit_student_block(request, pk, "academic", StudentAcademicForm, "Учебная деятельность", "academic")


@login_required
@permission_required("core.view_studentmedical", raise_exception=True)
def medical_edit(request, pk):
    log_action(request, "view_sensitive", "Доступ к медицинским данным")
    return _edit_student_block(request, pk, "medical", StudentMedicalForm, "Медицинские сведения", "medical")


@login_required
def benefits_edit(request, pk):
    return _edit_student_block(request, pk, "benefits", StudentBenefitsForm, "Льготы и поддержка", "benefits")


@login_required
def ai_generate(request, pk):
    student = get_object_or_404(Student, pk=pk)
    build_ai_analysis(student)
    messages.success(request, "ИИ-анализ сформирован.")
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
        | Q(psycho__adaptation_level__name__icontains="низ")
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
        "low_income": Student.objects.filter(family__income_level__name__icontains="малообеспеч"),
        "disability": Student.objects.filter(medical__has_disability=True),
        "dormitory": Student.objects.filter(housing__housing_type__name__icontains="общежит"),
        "problem_attendance": Student.objects.filter(academic__attendance="problematic"),
        "low_adaptation": Student.objects.filter(psycho__adaptation_level__name__icontains="низ"),
        "high_risk_ai": Student.objects.filter(ai_analyses__risk_level="high"),
    }
    return query_map.get(report_key, Student.objects.none()).distinct()


@login_required
def export_report(request, report_key, fmt):
    if report_key == "card_completion":
        headers, rows = get_card_completion_export_rows()
        filename = "card_completion"
    else:
        headers = ["ФИО", "ИИН", "Группа", "Курс", "Телефон"]
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
@permission_required("core.view_actionlog", raise_exception=True)
def action_logs(request):
    logs = ActionLog.objects.select_related("user")[:200]
    return render(request, "core/action_logs.html", {"logs": logs})


@login_required
@user_passes_test(_staff_required)
def settings_page(request):
    tab = request.GET.get("tab", "references")
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
                    is_active=add_form.cleaned_data.get("is_active", True),
                )
                log_action(request, "create", f"Добавлен справочник: {ref_config['title']} — {add_form.cleaned_data['name']}")
                messages.success(request, "Запись справочника добавлена.")
                return redirect(f"{request.path}?tab=references&ref={ref_key}")

    users = []
    if tab == "users":
        for user in User.objects.all():
            UserProfile.objects.get_or_create(user=user)
        users = (
            User.objects.select_related("profile", "profile__role")
            .prefetch_related("profile__departments")
            .order_by("username")
        )
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
            "users": users,
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
        initial={"name": item.name, "is_active": item.is_active},
    )
    if request.method == "POST" and form.is_valid():
        item.name = form.cleaned_data["name"]
        item.is_active = form.cleaned_data.get("is_active", False)
        item.save()
        log_action(request, "update", f"Обновлён справочник: {ref_config['title']} — {item.name}")
        messages.success(request, "Запись справочника обновлена.")
        return redirect(f"/settings/?tab=references&ref={key}")

    return render(
        request,
        "core/form.html",
        {"form": form, "title": f"Редактировать: {ref_config['title']}"},
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
    status = "активирована" if item.is_active else "деактивирована"
    log_action(request, "update", f"Запись справочника {status}: {item.name}")
    messages.success(request, f"Запись {status}.")
    return redirect(f"/settings/?tab=references&ref={key}")


@login_required
@user_passes_test(_staff_required)
def user_create(request):
    form = UserManageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_action(request, "create", f"Создан пользователь: {user.username}")
        messages.success(request, "Пользователь создан.")
        return redirect("/settings/?tab=users")

    return render(request, "core/settings_user_form.html", {"form": form, "title": "Новый пользователь"})


@login_required
@user_passes_test(_staff_required)
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = UserManageForm(request.POST or None, instance=user_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "update", f"Обновлён пользователь: {user_obj.username}")
        messages.success(request, "Пользователь обновлён.")
        return redirect("/settings/?tab=users")

    return render(
        request,
        "core/settings_user_form.html",
        {"form": form, "title": f"Редактировать: {user_obj.username}"},
    )
