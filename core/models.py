from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class ReferenceModel(models.Model):
    name = models.CharField("Название", max_length=255, unique=True)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(ReferenceModel):
    class Meta:
        verbose_name = "Кафедра"
        verbose_name_plural = "Кафедры"
        ordering = ["name"]


class Specialty(ReferenceModel):
    class Meta:
        verbose_name = "Специальность"
        verbose_name_plural = "Специальности"
        ordering = ["name"]


class StudyGroup(ReferenceModel):
    class Meta:
        verbose_name = "Учебная группа"
        verbose_name_plural = "Учебные группы"
        ordering = ["name"]


class PaymentForm(ReferenceModel):
    class Meta:
        verbose_name = "Форма оплаты"
        verbose_name_plural = "Формы оплаты"
        ordering = ["name"]


class FamilyType(ReferenceModel):
    class Meta:
        verbose_name = "Тип семьи"
        verbose_name_plural = "Типы семьи"
        ordering = ["name"]


class FamilyIncomeLevel(ReferenceModel):
    class Meta:
        verbose_name = "Материальное положение"
        verbose_name_plural = "Уровни материального положения"
        ordering = ["name"]


class HousingType(ReferenceModel):
    class Meta:
        verbose_name = "Тип жилья"
        verbose_name_plural = "Типы жилья"
        ordering = ["name"]


class TemperamentType(ReferenceModel):
    class Meta:
        verbose_name = "Темперамент"
        verbose_name_plural = "Типы темперамента"
        ordering = ["name"]


class CommunicationLevel(ReferenceModel):
    class Meta:
        verbose_name = "Уровень общения"
        verbose_name_plural = "Уровни общения"
        ordering = ["name"]


class GroupBehaviorType(ReferenceModel):
    class Meta:
        verbose_name = "Поведение в группе"
        verbose_name_plural = "Типы поведения в группе"
        ordering = ["name"]


class ResponsibilityLevel(ReferenceModel):
    class Meta:
        verbose_name = "Уровень ответственности"
        verbose_name_plural = "Уровни ответственности"
        ordering = ["name"]


class AdaptationLevel(ReferenceModel):
    class Meta:
        verbose_name = "Уровень адаптации"
        verbose_name_plural = "Уровни адаптации"
        ordering = ["name"]


class HealthGroup(ReferenceModel):
    class Meta:
        verbose_name = "Группа здоровья"
        verbose_name_plural = "Группы здоровья"
        ordering = ["name"]


class UserRole(ReferenceModel):
    class Meta:
        verbose_name = "Роль пользователя"
        verbose_name_plural = "Роли пользователей"
        ordering = ["name"]


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile", verbose_name="Пользователь"
    )
    role = models.ForeignKey(
        UserRole, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Роль"
    )
    departments = models.ManyToManyField(Department, blank=True, verbose_name="Кафедры")
    is_blocked = models.BooleanField("Заблокирован", default=False)

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class Student(models.Model):
    iin_validator = RegexValidator(r"^\d{12}$", "ИИН должен содержать ровно 12 цифр.")

    last_name = models.CharField("Фамилия", max_length=150)
    first_name = models.CharField("Имя", max_length=150)
    middle_name = models.CharField("Отчество", max_length=150, blank=True)
    birth_date = models.DateField("Дата рождения")
    citizenship = models.CharField("Гражданство", max_length=120)
    nationality = models.CharField("Национальность", max_length=120)
    iin = models.CharField(
        "ИИН", max_length=12, unique=True, validators=[iin_validator], db_index=True
    )
    phone = models.CharField("Телефон", max_length=20, db_index=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name="Кафедра")
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, verbose_name="Специальность")
    course = models.PositiveSmallIntegerField(
        "Курс", validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    group = models.ForeignKey(StudyGroup, on_delete=models.PROTECT, verbose_name="Учебная группа")
    payment_form = models.ForeignKey(
        PaymentForm, on_delete=models.PROTECT, verbose_name="Форма оплаты"
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"
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
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="family", verbose_name="Студент"
    )
    family_type = models.ForeignKey(
        FamilyType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Тип семьи"
    )
    income_level = models.ForeignKey(
        FamilyIncomeLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Материальное положение",
    )

    class Meta:
        verbose_name = "Семья студента"
        verbose_name_plural = "Семьи студентов"


class StudentFamilyMember(models.Model):
    family = models.ForeignKey(
        StudentFamily, on_delete=models.CASCADE, related_name="members", verbose_name="Семья"
    )
    full_name = models.CharField("ФИО", max_length=255)
    birth_year = models.PositiveSmallIntegerField("Год рождения")
    relation = models.CharField("Степень родства", max_length=120)
    workplace = models.CharField("Место работы", max_length=255, blank=True)
    position = models.CharField("Должность", max_length=120, blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    is_guardian = models.BooleanField("Опекун", default=False)
    is_primary_contact = models.BooleanField("Основной контакт", default=False)

    class Meta:
        verbose_name = "Член семьи"
        verbose_name_plural = "Члены семьи"


class StudentHousing(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="housing", verbose_name="Студент"
    )
    housing_type = models.ForeignKey(
        HousingType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Тип жилья"
    )
    comment = models.TextField("Комментарий", blank=True)

    class Meta:
        verbose_name = "Жилищные условия"
        verbose_name_plural = "Жилищные условия"


class StudentPsychoProfile(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="psycho", verbose_name="Студент"
    )
    temperament = models.ForeignKey(
        TemperamentType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Темперамент"
    )
    communication = models.ForeignKey(
        CommunicationLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Уровень общения",
    )
    behavior_in_group = models.ForeignKey(
        GroupBehaviorType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Поведение в группе",
    )
    responsibility_level = models.ForeignKey(
        ResponsibilityLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Уровень ответственности",
    )
    adaptation_level = models.ForeignKey(
        AdaptationLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Уровень адаптации",
    )
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Социально-психологический профиль"
        verbose_name_plural = "Социально-психологические профили"


class StudentAcademic(models.Model):
    ATTENDANCE_CHOICES = [
        ("good", "Хорошая"),
        ("satisfactory", "Удовлетворительная"),
        ("problematic", "Проблемная"),
    ]
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="academic", verbose_name="Студент"
    )
    gpa = models.DecimalField(
        "Средний балл", max_digits=4, decimal_places=2, null=True, blank=True
    )
    attendance = models.CharField(
        "Посещаемость", max_length=20, choices=ATTENDANCE_CHOICES, blank=True
    )
    has_unexcused_absences = models.BooleanField(
        "Пропуски без уважительной причины", default=False
    )
    unexcused_absences_count = models.PositiveIntegerField(
        "Количество пропусков", default=0
    )
    activity = models.TextField("Внеучебная активность", blank=True)

    class Meta:
        verbose_name = "Учебная деятельность"
        verbose_name_plural = "Учебная деятельность"


class StudentMedical(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="medical", verbose_name="Студент"
    )
    health_group = models.ForeignKey(
        HealthGroup, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Группа здоровья"
    )
    has_disability = models.BooleanField("Инвалидность", default=False)
    disability_details = models.TextField("Сведения об инвалидности", blank=True)
    chronic_diseases = models.TextField("Хронические заболевания", blank=True)
    recommendations = models.TextField("Рекомендации", blank=True)

    class Meta:
        verbose_name = "Медицинские сведения"
        verbose_name_plural = "Медицинские сведения"


class StudentBenefits(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="benefits", verbose_name="Студент"
    )
    state_grant = models.BooleanField("Государственный грант", default=False)
    receives_scholarship = models.BooleanField("Стипендия", default=False)
    disability_allowance = models.BooleanField("Пособие по инвалидности", default=False)
    breadwinner_loss_allowance = models.BooleanField(
        "Пособие по потере кормильца", default=False
    )
    preferential_housing = models.BooleanField("Льготное жильё", default=False)
    free_meals = models.BooleanField("Бесплатное питание", default=False)
    additional_benefits = models.TextField("Дополнительные льготы", blank=True)

    class Meta:
        verbose_name = "Льготы и поддержка"
        verbose_name_plural = "Льготы и поддержка"


class StudentAIAnalysis(models.Model):
    RISK_LEVELS = [("low", "Низкий"), ("medium", "Средний"), ("high", "Высокий")]
    SUPPORT_LEVELS = [
        ("none", "Не требуется"),
        ("observe", "Желательно наблюдение"),
        ("curator_attention", "Рекомендуется внимание куратора"),
        ("specialist", "Рекомендуется подключение профильного специалиста"),
    ]
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="ai_analyses", verbose_name="Студент"
    )
    short_profile = models.TextField("Краткий профиль")
    strengths = models.TextField("Сильные стороны")
    risk_factors = models.TextField("Факторы риска")
    recommendations = models.TextField("Рекомендации")
    risk_level = models.CharField("Уровень риска", max_length=20, choices=RISK_LEVELS)
    support_level = models.CharField(
        "Уровень сопровождения", max_length=30, choices=SUPPORT_LEVELS
    )
    created_at = models.DateTimeField("Дата анализа", auto_now_add=True)
    disclaimer = models.CharField(
        "Дисклеймер",
        max_length=255,
        default="Вывод сформирован автоматически и требует проверки ответственным сотрудником",
    )

    class Meta:
        verbose_name = "ИИ-анализ"
        verbose_name_plural = "ИИ-анализы"
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
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Пользователь"
    )
    action = models.CharField("Действие", max_length=30, choices=ACTIONS)
    description = models.CharField("Описание", max_length=255)
    created_at = models.DateTimeField("Дата и время", auto_now_add=True)

    class Meta:
        verbose_name = "Запись журнала"
        verbose_name_plural = "Журнал действий"
        ordering = ["-created_at"]
