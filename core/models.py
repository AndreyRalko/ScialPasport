from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class ReferenceModel(models.Model):
    name = models.CharField(_("Название"), max_length=255, unique=True)
    name_ru = models.CharField(_("Название (рус)"), max_length=255, blank=True)
    code = models.CharField(_("Код"), max_length=64, blank=True, null=True, unique=True)
    is_active = models.BooleanField(_("Активен"), default=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.localized_name

    @property
    def localized_name(self):
        language = (get_language() or "kk").split("-")[0]
        if language == "ru" and self.name_ru:
            return self.name_ru
        return self.name


class Department(ReferenceModel):
    class Meta:
        verbose_name = _("Кафедра")
        verbose_name_plural = _("Кафедры")
        ordering = ["name"]


class Specialty(ReferenceModel):
    class Meta:
        verbose_name = _("Специальность")
        verbose_name_plural = _("Специальности")
        ordering = ["name"]


class StudyGroup(ReferenceModel):
    class Meta:
        verbose_name = _("Учебная группа")
        verbose_name_plural = _("Учебные группы")
        ordering = ["name"]


class PaymentForm(ReferenceModel):
    class Meta:
        verbose_name = _("Форма оплаты")
        verbose_name_plural = _("Формы оплаты")
        ordering = ["name"]


class FamilyType(ReferenceModel):
    class Meta:
        verbose_name = _("Тип семьи")
        verbose_name_plural = _("Типы семьи")
        ordering = ["name"]


class FamilyIncomeLevel(ReferenceModel):
    class Meta:
        verbose_name = _("Материальное положение")
        verbose_name_plural = _("Уровни материального положения")
        ordering = ["name"]


class HousingType(ReferenceModel):
    class Meta:
        verbose_name = _("Тип жилья")
        verbose_name_plural = _("Типы жилья")
        ordering = ["name"]


class TemperamentType(ReferenceModel):
    class Meta:
        verbose_name = _("Темперамент")
        verbose_name_plural = _("Типы темперамента")
        ordering = ["name"]


class CommunicationLevel(ReferenceModel):
    class Meta:
        verbose_name = _("Уровень общения")
        verbose_name_plural = _("Уровни общения")
        ordering = ["name"]


class GroupBehaviorType(ReferenceModel):
    class Meta:
        verbose_name = _("Поведение в группе")
        verbose_name_plural = _("Типы поведения в группе")
        ordering = ["name"]


class ResponsibilityLevel(ReferenceModel):
    class Meta:
        verbose_name = _("Уровень ответственности")
        verbose_name_plural = _("Уровни ответственности")
        ordering = ["name"]


class AdaptationLevel(ReferenceModel):
    class Meta:
        verbose_name = _("Уровень адаптации")
        verbose_name_plural = _("Уровни адаптации")
        ordering = ["name"]


class HealthGroup(ReferenceModel):
    class Meta:
        verbose_name = _("Группа здоровья")
        verbose_name_plural = _("Группы здоровья")
        ordering = ["name"]


class UserRole(ReferenceModel):
    class Meta:
        verbose_name = _("Роль пользователя")
        verbose_name_plural = _("Роли пользователей")
        ordering = ["name"]


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile", verbose_name=_("Пользователь")
    )
    role = models.ForeignKey(
        UserRole, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Роль")
    )
    departments = models.ManyToManyField(Department, blank=True, verbose_name=_("Кафедры"))
    is_blocked = models.BooleanField(_("Заблокирован"), default=False)

    class Meta:
        verbose_name = _("Профиль пользователя")
        verbose_name_plural = _("Профили пользователей")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class Student(models.Model):
    iin_validator = RegexValidator(r"^\d{12}$", _("ИИН должен содержать ровно 12 цифр."))

    CITIZENSHIP_CHOICES = [
        ("kz", _("Казахстан")),
    ]
    NATIONALITY_CHOICES = [
        ("kazakh", _("Казах")),
        ("russian", _("Русский")),
        ("tatar", _("Татарин")),
        ("uyghur", _("Уйгур")),
    ]

    last_name = models.CharField(_("Фамилия"), max_length=150)
    first_name = models.CharField(_("Имя"), max_length=150)
    middle_name = models.CharField(_("Отчество"), max_length=150, blank=True)
    birth_date = models.DateField(_("Дата рождения"))
    citizenship = models.CharField(_("Гражданство"), max_length=120, choices=CITIZENSHIP_CHOICES, default="kz")
    nationality = models.CharField(_("Национальность"), max_length=120, choices=NATIONALITY_CHOICES)
    iin = models.CharField(
        _("ИИН"), max_length=12, unique=True, validators=[iin_validator], db_index=True
    )
    phone = models.CharField(_("Телефон"), max_length=20, db_index=True)
    photo = models.ImageField(_("Фотография"), upload_to="students/photos/", blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name=_("Кафедра"))
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, verbose_name=_("Специальность"))
    course = models.PositiveSmallIntegerField(
        _("Курс"), validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    group = models.ForeignKey(StudyGroup, on_delete=models.PROTECT, verbose_name=_("Учебная группа"))
    payment_form = models.ForeignKey(
        PaymentForm, on_delete=models.PROTECT, verbose_name=_("Форма оплаты")
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_record",
        verbose_name=_("Учётная запись кабинета"),
    )
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Студент")
        verbose_name_plural = _("Студенты")
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
        FamilyType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Тип семьи")
    )
    income_level = models.ForeignKey(
        FamilyIncomeLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Материальное положение"),
    )

    class Meta:
        verbose_name = "Семья студента"
        verbose_name_plural = "Семьи студентов"


class StudentFamilyMember(models.Model):
    RELATION_CHOICES = [
        ("mother", _("мать")),
        ("father", _("отец")),
        ("brother", _("брат")),
        ("sister", _("сестра")),
        ("guardian", _("опекун")),
    ]
    family = models.ForeignKey(
        StudentFamily, on_delete=models.CASCADE, related_name="members", verbose_name="Семья"
    )
    full_name = models.CharField(_("ФИО"), max_length=255)
    birth_year = models.PositiveSmallIntegerField(_("Год рождения"))
    relation = models.CharField(_("Степень родства"), max_length=120, choices=RELATION_CHOICES)
    workplace = models.CharField(_("Место работы"), max_length=255, blank=True)
    position = models.CharField(_("Должность"), max_length=120, blank=True)
    phone = models.CharField(_("Телефон"), max_length=20, blank=True)
    is_guardian = models.BooleanField(_("Опекун"), default=False)
    is_primary_contact = models.BooleanField(_("Основной контакт"), default=False)

    class Meta:
        verbose_name = "Член семьи"
        verbose_name_plural = "Члены семьи"


class StudentHousing(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="housing", verbose_name="Студент"
    )
    housing_type = models.ForeignKey(
        HousingType, on_delete=models.SET_NULL, null=True, blank=True,         verbose_name=_("Тип жилья")
    )
    comment = models.TextField(_("Комментарий"), blank=True)

    class Meta:
        verbose_name = "Жилищные условия"
        verbose_name_plural = "Жилищные условия"


class StudentPsychoProfile(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="psycho", verbose_name="Студент"
    )
    temperament = models.ForeignKey(
        TemperamentType, on_delete=models.SET_NULL, null=True, blank=True,         verbose_name=_("Темперамент")
    )
    communication = models.ForeignKey(
        CommunicationLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Уровень общения"),
    )
    behavior_in_group = models.ForeignKey(
        GroupBehaviorType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Поведение в группе"),
    )
    responsibility_level = models.ForeignKey(
        ResponsibilityLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Уровень ответственности"),
    )
    adaptation_level = models.ForeignKey(
        AdaptationLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Уровень адаптации"),
    )
    description = models.TextField(_("Описание"), blank=True)

    class Meta:
        verbose_name = "Социально-психологический профиль"
        verbose_name_plural = "Социально-психологические профили"


class StudentAcademic(models.Model):
    ATTENDANCE_CHOICES = [
        ("good", _("Хорошая")),
        ("satisfactory", _("Удовлетворительная")),
        ("problematic", _("Проблемная")),
    ]
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="academic", verbose_name="Студент"
    )
    gpa = models.DecimalField(
        _("Средний балл"), max_digits=4, decimal_places=2, null=True, blank=True
    )
    attendance = models.CharField(
        _("Посещаемость"), max_length=20, choices=ATTENDANCE_CHOICES, blank=True
    )
    has_unexcused_absences = models.BooleanField(
        _("Пропуски без уважительной причины"), default=False
    )
    unexcused_absences_count = models.PositiveIntegerField(
        _("Количество пропусков"), default=0
    )
    activity = models.TextField(_("Внеучебная активность"), blank=True)

    class Meta:
        verbose_name = "Учебная деятельность"
        verbose_name_plural = "Учебная деятельность"


class StudentMedical(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="medical", verbose_name="Студент"
    )
    health_group = models.ForeignKey(
        HealthGroup, on_delete=models.SET_NULL, null=True, blank=True,         verbose_name=_("Группа здоровья")
    )
    has_disability = models.BooleanField(_("Инвалидность"), default=False)
    disability_details = models.TextField(_("Сведения об инвалидности"), blank=True)
    chronic_diseases = models.TextField(_("Хронические заболевания"), blank=True)
    recommendations = models.TextField(_("Рекомендации"), blank=True)

    class Meta:
        verbose_name = "Медицинские сведения"
        verbose_name_plural = "Медицинские сведения"


class StudentBenefits(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="benefits", verbose_name="Студент"
    )
    state_grant = models.BooleanField(_("Государственный грант"), default=False)
    receives_scholarship = models.BooleanField(_("Стипендия"), default=False)
    disability_allowance = models.BooleanField(_("Пособие по инвалидности"), default=False)
    breadwinner_loss_allowance = models.BooleanField(
        _("Пособие по потере кормильца"), default=False
    )
    preferential_housing = models.BooleanField(_("Льготное жильё"), default=False)
    free_meals = models.BooleanField(_("Бесплатное питание"), default=False)
    additional_benefits = models.TextField(_("Дополнительные льготы"), blank=True)

    class Meta:
        verbose_name = "Льготы и поддержка"
        verbose_name_plural = "Льготы и поддержка"


class StudentAIAnalysis(models.Model):
    RISK_LEVELS = [("low", _("Низкий")), ("medium", _("Средний")), ("high", _("Высокий"))]
    SUPPORT_LEVELS = [
        ("none", _("Не требуется")),
        ("observe", _("Желательно наблюдение")),
        ("curator_attention", _("Рекомендуется внимание куратора")),
        ("specialist", _("Рекомендуется подключение профильного специалиста")),
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
        default=_("Вывод сформирован автоматически и требует проверки ответственным сотрудником"),
    )

    class Meta:
        verbose_name = "ИИ-анализ"
        verbose_name_plural = "ИИ-анализы"
        ordering = ["-created_at"]


class StudentRequest(models.Model):
    TYPES = [
        ("data", _("Уточнение данных")),
        ("housing", _("Жильё / общежитие")),
        ("benefit", _("Льгота / поддержка")),
        ("consult", _("Консультация")),
        ("other", _("Другое")),
    ]
    STATUSES = [
        ("new", _("Новая")),
        ("in_progress", _("В работе")),
        ("done", _("Закрыта")),
    ]
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="cabinet_requests", verbose_name=_("Студент")
    )
    request_type = models.CharField(_("Тип обращения"), max_length=20, choices=TYPES)
    message = models.TextField(_("Сообщение"))
    status = models.CharField(_("Статус"), max_length=20, choices=STATUSES, default="new")
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Обращение студента")
        verbose_name_plural = _("Обращения студентов")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} — {self.get_request_type_display()}"


class ActionLog(models.Model):
    ACTIONS = [
        ("login", _("Вход")),
        ("logout", _("Выход")),
        ("create", _("Создание")),
        ("update", _("Редактирование")),
        ("delete", _("Удаление")),
        ("view_sensitive", _("Просмотр чувствительных данных")),
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


class AISettings(models.Model):
    PROVIDER_OPENAI = "openai"
    PROVIDER_CLAUDE = "claude"
    PROVIDERS = [
        (PROVIDER_OPENAI, "OpenAI"),
        (PROVIDER_CLAUDE, "Claude (Anthropic)"),
    ]
    MODELS = [
        ("gpt-4o-mini", "OpenAI — GPT-4o mini"),
        ("gpt-4o", "OpenAI — GPT-4o"),
        ("gpt-4.1-mini", "OpenAI — GPT-4.1 mini"),
        ("gpt-4.1", "OpenAI — GPT-4.1"),
        ("claude-sonnet-4-20250514", "Claude — Sonnet 4"),
        ("claude-3-7-sonnet-latest", "Claude — 3.7 Sonnet"),
        ("claude-3-5-haiku-latest", "Claude — 3.5 Haiku"),
        ("claude-opus-4-20250514", "Claude — Opus 4"),
    ]
    DEFAULT_MODELS = {
        PROVIDER_OPENAI: "gpt-4o-mini",
        PROVIDER_CLAUDE: "claude-sonnet-4-20250514",
    }

    provider = models.CharField(_("Провайдер"), max_length=20, choices=PROVIDERS, default=PROVIDER_OPENAI)
    model = models.CharField(_("Модель"), max_length=80, default="gpt-4o-mini")
    api_key = models.CharField(_("API-ключ"), max_length=512, blank=True)
    is_enabled = models.BooleanField(_("Использовать внешнюю модель"), default=False)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_settings_updates",
        verbose_name=_("Кто обновил"),
    )

    class Meta:
        verbose_name = _("Настройки ИИ")
        verbose_name_plural = _("Настройки ИИ")

    def __str__(self):
        return f"{self.get_provider_display()} / {self.model}"

    @property
    def model_label(self):
        return dict(self.MODELS).get(self.model, self.model)

    def masked_key(self):
        if not self.api_key:
            return ""
        tail = self.api_key[-4:] if len(self.api_key) >= 4 else ""
        return f"••••{tail}"

    def is_ready(self):
        return bool(self.is_enabled and self.api_key and self.model)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
