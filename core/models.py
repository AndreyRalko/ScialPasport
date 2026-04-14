from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class ReferenceModel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(ReferenceModel):
    pass


class Specialty(ReferenceModel):
    pass


class StudyGroup(ReferenceModel):
    pass


class PaymentForm(ReferenceModel):
    pass


class FamilyType(ReferenceModel):
    pass


class FamilyIncomeLevel(ReferenceModel):
    pass


class HousingType(ReferenceModel):
    pass


class TemperamentType(ReferenceModel):
    pass


class CommunicationLevel(ReferenceModel):
    pass


class GroupBehaviorType(ReferenceModel):
    pass


class ResponsibilityLevel(ReferenceModel):
    pass


class AdaptationLevel(ReferenceModel):
    pass


class HealthGroup(ReferenceModel):
    pass


class UserRole(ReferenceModel):
    pass


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True, blank=True)
    departments = models.ManyToManyField(Department, blank=True)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class Student(models.Model):
    iin_validator = RegexValidator(r"^\d{12}$", "ИИН должен содержать ровно 12 цифр.")

    last_name = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, blank=True)
    birth_date = models.DateField()
    citizenship = models.CharField(max_length=120)
    nationality = models.CharField(max_length=120)
    iin = models.CharField(max_length=12, unique=True, validators=[iin_validator], db_index=True)
    phone = models.CharField(max_length=20, db_index=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT)
    course = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)])
    group = models.ForeignKey(StudyGroup, on_delete=models.PROTECT)
    payment_form = models.ForeignKey(PaymentForm, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name", "middle_name"]),
            models.Index(fields=["iin"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()

    @property
    def age(self):
        today = timezone.localdate()
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years


class StudentFamily(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="family")
    family_type = models.ForeignKey(FamilyType, on_delete=models.SET_NULL, null=True, blank=True)
    income_level = models.ForeignKey(FamilyIncomeLevel, on_delete=models.SET_NULL, null=True, blank=True)


class StudentFamilyMember(models.Model):
    family = models.ForeignKey(StudentFamily, on_delete=models.CASCADE, related_name="members")
    full_name = models.CharField(max_length=255)
    birth_year = models.PositiveSmallIntegerField()
    relation = models.CharField(max_length=120)
    workplace = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_guardian = models.BooleanField(default=False)
    is_primary_contact = models.BooleanField(default=False)


class StudentHousing(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="housing")
    housing_type = models.ForeignKey(HousingType, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.TextField(blank=True)


class StudentPsychoProfile(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="psycho")
    temperament = models.ForeignKey(TemperamentType, on_delete=models.SET_NULL, null=True, blank=True)
    communication = models.ForeignKey(CommunicationLevel, on_delete=models.SET_NULL, null=True, blank=True)
    behavior_in_group = models.ForeignKey(GroupBehaviorType, on_delete=models.SET_NULL, null=True, blank=True)
    responsibility_level = models.ForeignKey(ResponsibilityLevel, on_delete=models.SET_NULL, null=True, blank=True)
    adaptation_level = models.ForeignKey(AdaptationLevel, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)


class StudentAcademic(models.Model):
    ATTENDANCE_CHOICES = [
        ("good", "Хорошая"),
        ("satisfactory", "Удовлетворительная"),
        ("problematic", "Проблемная"),
    ]
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="academic")
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    attendance = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES, blank=True)
    has_unexcused_absences = models.BooleanField(default=False)
    unexcused_absences_count = models.PositiveIntegerField(default=0)
    activity = models.TextField(blank=True)


class StudentMedical(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="medical")
    health_group = models.ForeignKey(HealthGroup, on_delete=models.SET_NULL, null=True, blank=True)
    has_disability = models.BooleanField(default=False)
    disability_details = models.TextField(blank=True)
    chronic_diseases = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)


class StudentBenefits(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="benefits")
    state_grant = models.BooleanField(default=False)
    receives_scholarship = models.BooleanField(default=False)
    disability_allowance = models.BooleanField(default=False)
    breadwinner_loss_allowance = models.BooleanField(default=False)
    preferential_housing = models.BooleanField(default=False)
    free_meals = models.BooleanField(default=False)
    additional_benefits = models.TextField(blank=True)


class StudentAIAnalysis(models.Model):
    RISK_LEVELS = [("low", "Низкий"), ("medium", "Средний"), ("high", "Высокий")]
    SUPPORT_LEVELS = [
        ("none", "Не требуется"),
        ("observe", "Желательно наблюдение"),
        ("curator_attention", "Рекомендуется внимание куратора"),
        ("specialist", "Рекомендуется подключение профильного специалиста"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="ai_analyses")
    short_profile = models.TextField()
    strengths = models.TextField()
    risk_factors = models.TextField()
    recommendations = models.TextField()
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS)
    support_level = models.CharField(max_length=30, choices=SUPPORT_LEVELS)
    created_at = models.DateTimeField(auto_now_add=True)
    disclaimer = models.CharField(
        max_length=255,
        default="Вывод сформирован автоматически и требует проверки ответственным сотрудником",
    )

    class Meta:
        ordering = ["-created_at"]


class ActionLog(models.Model):
    ACTIONS = [
        ("login", "Вход"),
        ("logout", "Выход"),
        ("create", "Создание"),
        ("update", "Редактирование"),
        ("delete", "Удаление"),
        ("view_sensitive", "Просмотр чувствительных данных"),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTIONS)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
