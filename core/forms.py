from django import forms
from django.contrib.auth.models import User

from .models import (
    Department,
    Student,
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
                field.empty_label = "— не выбрано —"
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
        label="Название",
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Введите название"}),
    )
    is_active = forms.BooleanField(label="Активен", required=False, initial=True)


class UserManageForm(forms.ModelForm):
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"placeholder": "Минимум 8 символов"}),
        required=False,
        help_text="Оставьте пустым, чтобы не менять пароль при редактировании.",
    )
    role = forms.ModelChoiceField(
        label="Роль",
        queryset=UserRole.objects.active(),
        required=False,
    )
    departments = forms.ModelMultipleChoiceField(
        label="Кафедры",
        queryset=Department.objects.active(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    is_blocked = forms.BooleanField(label="Заблокирован", required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_staff"]
        labels = {
            "username": "Логин",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Электронная почта",
            "is_staff": "Права администратора",
        }
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Логин"}),
            "first_name": forms.TextInput(attrs={"placeholder": "Имя"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Фамилия"}),
            "email": forms.EmailInput(attrs={"placeholder": "pochta@universitet.kz"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self.fields.get("role"), forms.ModelChoiceField):
            self.fields["role"].empty_label = "— не выбрано —"
        if self.instance.pk:
            self.fields["password"].required = False
            profile = getattr(self.instance, "profile", None)
            if profile:
                self.fields["role"].initial = profile.role
                self.fields["departments"].initial = profile.departments.all()
                self.fields["is_blocked"].initial = profile.is_blocked
        else:
            self.fields["password"].required = True
            del self.fields["password"].help_text

    def save(self, commit=True):
        is_new = not self.instance.pk
        user = super().save(commit=False)
        if is_new:
            user.set_password(self.cleaned_data["password"])
        elif self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data.get("role")
            profile.is_blocked = self.cleaned_data.get("is_blocked", False)
            profile.save()
            profile.departments.set(self.cleaned_data.get("departments", []))
        return user

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("password"):
            self.add_error("password", "Укажите пароль для нового пользователя.")
        return cleaned
