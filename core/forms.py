from django import forms

from .models import (
    Student,
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


class StudentForm(forms.ModelForm):
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


class StudentFamilyForm(forms.ModelForm):
    class Meta:
        model = StudentFamily
        fields = ["family_type", "income_level"]


class StudentFamilyMemberForm(forms.ModelForm):
    class Meta:
        model = StudentFamilyMember
        exclude = ["family"]


class StudentHousingForm(forms.ModelForm):
    class Meta:
        model = StudentHousing
        exclude = ["student"]


class StudentPsychoProfileForm(forms.ModelForm):
    class Meta:
        model = StudentPsychoProfile
        exclude = ["student"]


class StudentAcademicForm(forms.ModelForm):
    class Meta:
        model = StudentAcademic
        exclude = ["student"]


class StudentMedicalForm(forms.ModelForm):
    class Meta:
        model = StudentMedical
        exclude = ["student"]


class StudentBenefitsForm(forms.ModelForm):
    class Meta:
        model = StudentBenefits
        exclude = ["student"]
