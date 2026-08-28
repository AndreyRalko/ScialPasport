from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .cabinet import get_cabinet_student, is_student_user
from .forms import (
    CabinetLoginForm,
    CabinetPasswordForm,
    CabinetProfileForm,
    CabinetRequestForm,
    StudentFamilyForm,
    StudentFamilyMemberForm,
    StudentHousingForm,
)
from .models import StudentFamily, StudentFamilyMember, StudentHousing, StudentRequest
from .views import log_action


def student_login_required(view):
    @wraps(view)
    @login_required(login_url="cabinet-login")
    def wrapped(request, *args, **kwargs):
        student = get_cabinet_student(request.user)
        if not student:
            if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
                return redirect("home")
            return redirect("cabinet-login")
        request.cabinet_student = student
        return view(request, *args, **kwargs)

    return wrapped


def _cabinet_context(request, **extra):
    student = request.cabinet_student
    context = {
        "student": student,
        "family": getattr(student, "family", None),
        "housing": getattr(student, "housing", None),
        "academic": getattr(student, "academic", None),
        "benefits": getattr(student, "benefits", None),
        "members": [],
    }
    if context["family"]:
        context["members"] = context["family"].members.all()
    context.update(extra)
    return context


def cabinet_login(request):
    if request.user.is_authenticated:
        if is_student_user(request.user):
            return redirect("cabinet-home")
        return redirect("home")

    form = CabinetLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        iin = form.cleaned_data["iin"]
        user = authenticate(request, username=iin, password=form.cleaned_data["password"])
        if user and is_student_user(user):
            login(request, user)
            return redirect("cabinet-home")
        form.add_error(None, _("Неверный ИИН или пароль, либо кабинет ещё не подключен."))
    return render(request, "cabinet/login.html", {"form": form})


def cabinet_logout(request):
    logout(request)
    return redirect("cabinet-login")


@student_login_required
def cabinet_home(request):
    student = request.cabinet_student
    requests = student.cabinet_requests.all()[:8]
    return render(
        request,
        "cabinet/home.html",
        _cabinet_context(request, requests=requests),
    )


@student_login_required
def cabinet_profile(request):
    student = request.cabinet_student
    form = CabinetProfileForm(request.POST or None, request.FILES or None, instance=student)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "update", _("Студент обновил контакты в кабинете"))
        messages.success(request, _("Контактные данные сохранены."))
        return redirect("cabinet-profile")
    return render(request, "cabinet/profile.html", _cabinet_context(request, form=form))


@student_login_required
def cabinet_family(request):
    student = request.cabinet_student
    family, _ = StudentFamily.objects.get_or_create(student=student)
    form = StudentFamilyForm(request.POST or None, instance=family)
    if request.method == "POST" and request.POST.get("action") == "save_family" and form.is_valid():
        form.save()
        log_action(request, "update", _("Студент обновил сведения о семье"))
        messages.success(request, _("Сведения о семье сохранены."))
        return redirect("cabinet-family")
    return render(
        request,
        "cabinet/family.html",
        _cabinet_context(request, form=form, member_form=StudentFamilyMemberForm(), family=family, members=family.members.all()),
    )


@student_login_required
@require_POST
def cabinet_family_member_add(request):
    student = request.cabinet_student
    family, _ = StudentFamily.objects.get_or_create(student=student)
    form = StudentFamilyMemberForm(request.POST)
    if form.is_valid():
        member = form.save(commit=False)
        member.family = family
        member.save()
        log_action(request, "create", _("Студент добавил члена семьи"))
        messages.success(request, _("Член семьи добавлен."))
    else:
        messages.error(request, _("Проверьте данные члена семьи."))
    return redirect("cabinet-family")


@student_login_required
@require_POST
def cabinet_family_member_delete(request, member_id):
    student = request.cabinet_student
    member = get_object_or_404(StudentFamilyMember, pk=member_id, family__student=student)
    member.delete()
    log_action(request, "delete", _("Студент удалил члена семьи"))
    messages.success(request, _("Член семьи удалён."))
    return redirect("cabinet-family")


@student_login_required
def cabinet_housing(request):
    student = request.cabinet_student
    housing, _ = StudentHousing.objects.get_or_create(student=student)
    form = StudentHousingForm(request.POST or None, instance=housing)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "update", _("Студент обновил жилищные условия"))
        messages.success(request, _("Жилищные условия сохранены."))
        return redirect("cabinet-housing")
    return render(request, "cabinet/housing.html", _cabinet_context(request, form=form, housing=housing))


@student_login_required
def cabinet_requests(request):
    student = request.cabinet_student
    form = CabinetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.student = student
        item.status = "new"
        item.save()
        log_action(request, "create", _("Студент отправил обращение: %(t)s") % {"t": item.get_request_type_display()})
        messages.success(request, _("Обращение отправлено куратору."))
        return redirect("cabinet-requests")
    return render(
        request,
        "cabinet/requests.html",
        _cabinet_context(request, form=form, requests=student.cabinet_requests.all()),
    )


@student_login_required
def cabinet_password(request):
    form = CabinetPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not request.user.check_password(form.cleaned_data["old_password"]):
            form.add_error("old_password", _("Неверный текущий пароль."))
        else:
            request.user.set_password(form.cleaned_data["new_password"])
            request.user.save(update_fields=["password"])
            update_session_auth_hash(request, request.user)
            log_action(request, "update", _("Студент сменил пароль кабинета"))
            messages.success(request, _("Пароль обновлён."))
            return redirect("cabinet-password")
    return render(request, "cabinet/password.html", _cabinet_context(request, form=form))
