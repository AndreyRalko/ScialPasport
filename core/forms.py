from django import forms
from django.contrib.auth.models import Group, Permission, User
from django.utils.translation import gettext_lazy as _

from .models import (
    AISettings,
    Department,
    Student,
    StudentRequest,
    UserProfile,
    UserRole,
    StudentAcademic,
    StudentBenefits,
    StudentFamily,
    StudentFamilyMember,
    StudentHousing,
    StudentMedical,
    StudentPsychoProfile,
)


class DateInput(forms.DateInput):
    input_type = "date"


class RussianModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = _("— не выбрано —")
            widget = field.widget
            if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, forms.DateInput)):
                widget.attrs.setdefault("class", "styled-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "styled-input")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "styled-input")
                widget.attrs.setdefault("rows", 4)


class StudentForm(RussianModelForm):
    class Meta:
        model = Student
        fields = [
            "last_name",
            "first_name",
            "middle_name",
            "birth_date",
            "citizenship",
            "nationality",
            "iin",
            "phone",
            "photo",
            "department",
            "specialty",
            "course",
            "group",
            "payment_form",
        ]
        widgets = {"birth_date": DateInput()}


class StudentFamilyForm(RussianModelForm):
    class Meta:
        model = StudentFamily
        fields = ["family_type", "income_level"]


class StudentFamilyMemberForm(RussianModelForm):
    class Meta:
        model = StudentFamilyMember
        exclude = ["family"]


class StudentHousingForm(forms.ModelForm):
    class Meta:
        model = StudentHousing
        exclude = ["student"]


class StudentPsychoProfileForm(RussianModelForm):
    class Meta:
        model = StudentPsychoProfile
        exclude = ["student"]


class StudentAcademicForm(RussianModelForm):
    class Meta:
        model = StudentAcademic
        exclude = ["student"]


class StudentMedicalForm(RussianModelForm):
    class Meta:
        model = StudentMedical
        exclude = ["student"]


class StudentBenefitsForm(RussianModelForm):
    class Meta:
        model = StudentBenefits
        exclude = ["student"]


class ReferenceItemForm(forms.Form):
    name = forms.CharField(
        label=_("Название (қаз)"),
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": _("Қазақша атауы")}),
    )
    name_ru = forms.CharField(
        label=_("Название (рус)"),
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": _("Русское название")}),
    )
    is_active = forms.BooleanField(label=_("Активен"), required=False, initial=True)


class UserManageForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Пароль"),
        widget=forms.PasswordInput(attrs={"placeholder": _("Минимум 8 символов")}),
        required=False,
        help_text=_("Оставьте пустым, чтобы не менять пароль при редактировании."),
    )
    role = forms.ModelChoiceField(
        label=_("Роль"),
        queryset=UserRole.objects.active(),
        required=False,
    )
    departments = forms.ModelMultipleChoiceField(
        label=_("Кафедры"),
        queryset=Department.objects.active(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    is_blocked = forms.BooleanField(label=_("Заблокирован"), required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active", "is_staff", "is_superuser"]
        labels = {
            "username": _("Логин"),
            "first_name": _("Имя"),
            "last_name": _("Фамилия"),
            "email": _("Электронная почта"),
            "is_active": _("Активен"),
            "is_staff": _("Доступ к админ-панели"),
            "is_superuser": _("Суперпользователь"),
        }
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": _("Логин")}),
            "first_name": forms.TextInput(attrs={"placeholder": _("Имя")}),
            "last_name": forms.TextInput(attrs={"placeholder": _("Фамилия")}),
            "email": forms.EmailInput(attrs={"placeholder": "pochta@universitet.kz"}),
        }

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        if isinstance(self.fields.get("role"), forms.ModelChoiceField):
            self.fields["role"].empty_label = _("— не выбрано —")
        if not (request and request.user.is_superuser):
            self.fields.pop("is_superuser", None)
        if self.instance.pk:
            self.fields["password"].required = False
            profile = getattr(self.instance, "profile", None)
            if profile:
                self.fields["role"].initial = profile.role
                self.fields["departments"].initial = profile.departments.all()
                self.fields["is_blocked"].initial = profile.is_blocked
        else:
            self.fields["password"].required = True
            self.fields["is_active"].initial = True
            self.fields["password"].help_text = ""

    def save(self, commit=True):
        from .admin_panel import sync_user_role_group, terminate_user_sessions

        is_new = not self.instance.pk
        user = super().save(commit=False)
        if is_new:
            user.set_password(self.cleaned_data["password"])
        elif self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if self.cleaned_data.get("is_blocked"):
            user.is_active = False
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data.get("role")
            profile.is_blocked = self.cleaned_data.get("is_blocked", False)
            profile.save()
            profile.departments.set(self.cleaned_data.get("departments", []))
            sync_user_role_group(user, profile.role)
            if profile.is_blocked or not user.is_active:
                keep = None
                if self.request and self.request.user.pk == user.pk:
                    keep = self.request.session.session_key
                terminate_user_sessions(user.pk, keep_key=keep)
        return user

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("password"):
            self.add_error("password", _("Укажите пароль для нового пользователя."))
        current = self.request.user if self.request else None
        if current and self.instance.pk == current.pk:
            if cleaned.get("is_blocked"):
                self.add_error("is_blocked", _("Нельзя заблокировать собственную учётную запись."))
            if cleaned.get("is_active") is False:
                self.add_error("is_active", _("Нельзя деактивировать собственную учётную запись."))
            if self.instance.is_staff and not cleaned.get("is_staff"):
                self.add_error("is_staff", _("Нельзя снять свои права администратора."))
            if self.instance.is_superuser and "is_superuser" in self.fields and not cleaned.get("is_superuser"):
                self.add_error("is_superuser", _("Нельзя снять у себя права суперпользователя."))
        return cleaned


class GroupManageForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        label=_("Права"),
        queryset=Permission.objects.filter(content_type__app_label__in=["core", "auth"]).select_related("content_type").order_by("content_type__model", "codename"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]
        labels = {"name": _("Название группы")}
        widgets = {"name": forms.TextInput(attrs={"placeholder": _("Например: Кураторы")})}


class CabinetLoginForm(forms.Form):
    iin = forms.CharField(
        label=_("ИИН"),
        max_length=12,
        min_length=12,
        widget=forms.TextInput(attrs={"placeholder": "000000000000", "inputmode": "numeric", "autocomplete": "username"}),
    )
    password = forms.CharField(
        label=_("Пароль"),
        widget=forms.PasswordInput(attrs={"placeholder": _("Пароль кабинета"), "autocomplete": "current-password"}),
    )


class CabinetProfileForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["phone", "photo"]
        labels = {"phone": _("Телефон"), "photo": _("Фотография")}


class CabinetRequestForm(forms.ModelForm):
    class Meta:
        model = StudentRequest
        fields = ["request_type", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": _("Опишите вопрос куратору")}),
        }


class AISettingsForm(forms.Form):
    provider = forms.ChoiceField(label=_("Провайдер"), choices=AISettings.PROVIDERS)
    model = forms.ChoiceField(label=_("Модель"), choices=AISettings.MODELS)
    api_key = forms.CharField(
        label=_("API-ключ"),
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "styled-input",
                "autocomplete": "new-password",
                "placeholder": _("Вставьте ключ OpenAI или Anthropic"),
            },
            render_value=False,
        ),
    )
    is_enabled = forms.BooleanField(label=_("Использовать внешнюю модель"), required=False)

    def __init__(self, *args, settings: AISettings | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = settings
        for name in ("provider", "model"):
            self.fields[name].widget.attrs.setdefault("class", "styled-input")
        if settings and settings.api_key:
            self.fields["api_key"].help_text = _("Сохранён ключ %(mask)s. Оставьте поле пустым, чтобы не менять.") % {
                "mask": settings.masked_key()
            }
            self.fields["api_key"].widget.attrs["placeholder"] = _("Новый ключ — или пусто, чтобы оставить текущий")

    def clean(self):
        from .llm import PROVIDER_MODELS

        cleaned = super().clean()
        provider = cleaned.get("provider")
        model = cleaned.get("model")
        allowed = PROVIDER_MODELS.get(provider, set())
        if provider and model and model not in allowed:
            self.add_error("model", _("Эта модель не относится к выбранному провайдеру."))
        api_key = (cleaned.get("api_key") or "").strip()
        if not api_key and self.settings and self.settings.api_key:
            cleaned["api_key"] = self.settings.api_key
        elif api_key:
            cleaned["api_key"] = api_key
        if cleaned.get("is_enabled") and not cleaned.get("api_key"):
            self.add_error("api_key", _("Чтобы включить модель, укажите API-ключ."))
        return cleaned


class CabinetPasswordForm(forms.Form):
    old_password = forms.CharField(label=_("Текущий пароль"), widget=forms.PasswordInput)
    new_password = forms.CharField(label=_("Новый пароль"), widget=forms.PasswordInput, min_length=8)
    new_password2 = forms.CharField(label=_("Повторите пароль"), widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password") and cleaned.get("new_password") != cleaned.get("new_password2"):
            self.add_error("new_password2", _("Пароли не совпадают."))
        return cleaned
