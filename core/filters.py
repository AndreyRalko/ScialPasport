import django_filters
from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Student, StudentAcademic


BOOLEAN_CHOICES = (("", _("Все")), ("true", _("Да")), ("false", _("Нет")))


class StudentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method="filter_search",
        label=_("Поиск"),
        widget=forms.TextInput(attrs={"placeholder": _("ФИО, ИИН или телефон")}),
    )
    has_disability = django_filters.BooleanFilter(
        field_name="medical__has_disability",
        label=_("Инвалидность"),
        widget=forms.Select(choices=BOOLEAN_CHOICES),
    )
    has_benefits = django_filters.BooleanFilter(
        method="filter_benefits",
        label=_("Есть льготы"),
        widget=forms.Select(choices=BOOLEAN_CHOICES),
    )
    attendance = django_filters.ChoiceFilter(
        field_name="academic__attendance",
        label=_("Посещаемость"),
        choices=[("", _("Все"))] + StudentAcademic.ATTENDANCE_CHOICES,
    )
    has_unexcused_absences = django_filters.BooleanFilter(
        field_name="academic__has_unexcused_absences",
        label=_("Пропуски без уважительной причины"),
        widget=forms.Select(choices=BOOLEAN_CHOICES),
    )
    activity = django_filters.CharFilter(
        method="filter_activity",
        label=_("Внеучебная активность"),
        widget=forms.TextInput(attrs={"placeholder": _("Ключевые слова")}),
    )

    class Meta:
        model = Student
        fields = [
            "department",
            "specialty",
            "course",
            "group",
            "payment_form",
            "family__family_type",
            "family__income_level",
            "housing__housing_type",
            "medical__health_group",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.filters.values():
            if hasattr(field.field, "empty_label"):
                field.field.empty_label = _("Все")

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(last_name__icontains=value)
            | Q(first_name__icontains=value)
            | Q(middle_name__icontains=value)
            | Q(iin__icontains=value)
            | Q(phone__icontains=value)
        )

    def filter_benefits(self, queryset, name, value):
        if value is None:
            return queryset
        benefits_q = (
            Q(benefits__state_grant=True)
            | Q(benefits__receives_scholarship=True)
            | Q(benefits__disability_allowance=True)
            | Q(benefits__breadwinner_loss_allowance=True)
            | Q(benefits__preferential_housing=True)
            | Q(benefits__free_meals=True)
        )
        return queryset.filter(benefits_q) if value else queryset.exclude(benefits_q)

    def filter_activity(self, queryset, name, value):
        return queryset.filter(academic__activity__icontains=value)
