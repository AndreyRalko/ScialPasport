import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from openpyxl import Workbook

from .filters import StudentFilter
from .forms import (
    StudentAcademicForm,
    StudentBenefitsForm,
    StudentFamilyForm,
    StudentFamilyMemberForm,
    StudentForm,
    StudentHousingForm,
    StudentMedicalForm,
    StudentPsychoProfileForm,
)
from .models import ActionLog, Student, StudentAIAnalysis, StudentFamily
from .services import build_ai_analysis


def log_action(request, action, description):
    if request.user.is_authenticated:
        ActionLog.objects.create(user=request.user, action=action, description=description)


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
    return render(request, "core/form.html", {"form": form, "title": "Добавить студента"})


@login_required
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    form = StudentForm(request.POST or None, instance=student)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "update", f"Обновлен студент: {student.full_name}")
        return redirect("student-detail", pk=student.pk)
    return render(request, "core/form.html", {"form": form, "title": "Редактировать студента"})


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
        return redirect("student-detail", pk=pk)
    return render(request, "core/form.html", {"form": form, "title": "Сведения о семье"})


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
        return redirect("student-detail", pk=pk)
    return render(request, "core/form.html", {"form": form, "title": "Добавить члена семьи"})


@login_required
def family_member_delete(request, pk, member_id):
    student = get_object_or_404(Student, pk=pk)
    member = get_object_or_404(student.family.members, pk=member_id)
    member.delete()
    log_action(request, "delete", f"Удален член семьи: {student.full_name}")
    return redirect("student-detail", pk=pk)


def _edit_student_block(request, pk, rel_name, form_class, title):
    student = get_object_or_404(Student, pk=pk)
    instance = getattr(student, rel_name, None)
    form = form_class(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.student = student
        obj.save()
        log_action(request, "update", f"Обновлен блок '{title}': {student.full_name}")
        return redirect("student-detail", pk=pk)
    return render(request, "core/form.html", {"form": form, "title": title})


@login_required
def housing_edit(request, pk):
    return _edit_student_block(request, pk, "housing", StudentHousingForm, "Жилищные условия")


@login_required
def psycho_edit(request, pk):
    return _edit_student_block(request, pk, "psycho", StudentPsychoProfileForm, "Социально-психологический профиль")


@login_required
def academic_edit(request, pk):
    return _edit_student_block(request, pk, "academic", StudentAcademicForm, "Учебная деятельность")


@login_required
@permission_required("core.view_studentmedical", raise_exception=True)
def medical_edit(request, pk):
    log_action(request, "view_sensitive", "Доступ к медицинским данным")
    return _edit_student_block(request, pk, "medical", StudentMedicalForm, "Медицинские сведения")


@login_required
def benefits_edit(request, pk):
    return _edit_student_block(request, pk, "benefits", StudentBenefitsForm, "Льготы и поддержка")


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
    return render(request, "core/reports.html")


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
    qs = _report_queryset(report_key)
    if fmt == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{report_key}.csv"'
        writer = csv.writer(response)
        writer.writerow(["ФИО", "ИИН", "Группа", "Курс", "Телефон"])
        for s in qs:
            writer.writerow([s.full_name, s.iin, s.group.name, s.course, s.phone])
        return response

    wb = Workbook()
    ws = wb.active
    ws.title = "report"
    ws.append(["ФИО", "ИИН", "Группа", "Курс", "Телефон"])
    for s in qs:
        ws.append([s.full_name, s.iin, s.group.name, s.course, s.phone])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{report_key}.xlsx"'
    wb.save(response)
    return response


@login_required
@permission_required("core.view_actionlog", raise_exception=True)
def action_logs(request):
    logs = ActionLog.objects.select_related("user")[:200]
    return render(request, "core/action_logs.html", {"logs": logs})
