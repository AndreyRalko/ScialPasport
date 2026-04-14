import django_filters
from django.db.models import Q

from .models import Student


class StudentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search", label="Поиск")
    has_disability = django_filters.BooleanFilter(field_name="medical__has_disability")
    has_benefits = django_filters.BooleanFilter(method="filter_benefits")
    attendance = django_filters.CharFilter(field_name="academic__attendance")
    has_unexcused_absences = django_filters.BooleanFilter(field_name="academic__has_unexcused_absences")
    activity = django_filters.CharFilter(method="filter_activity")

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
