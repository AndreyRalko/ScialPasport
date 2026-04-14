import random
from datetime import date

from django.core.management.base import BaseCommand

from core.models import (
    AdaptationLevel,
    CommunicationLevel,
    Department,
    FamilyIncomeLevel,
    FamilyType,
    GroupBehaviorType,
    HealthGroup,
    HousingType,
    PaymentForm,
    ResponsibilityLevel,
    Specialty,
    Student,
    StudentAcademic,
    StudentBenefits,
    StudentFamily,
    StudentFamilyMember,
    StudentHousing,
    StudentMedical,
    StudentPsychoProfile,
    StudyGroup,
    TemperamentType,
)
from core.services import build_ai_analysis


class Command(BaseCommand):
    help = "Заполняет систему тестовыми данными студентов и связанных блоков."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=30, help="Количество студентов для генерации")

    def handle(self, *args, **options):
        count = options["count"]

        departments = self._ensure_named(Department, ["Информатика и вычислительная техника", "Экономика и менеджмент", "Юриспруденция"])
        specialties = self._ensure_named(Specialty, ["Программная инженерия", "Информационные системы", "Экономика", "Право"])
        groups = self._ensure_named(StudyGroup, ["ПИ-21", "ПИ-31", "Ф-22", "ИС-11", "ПК-41"])
        payment_forms = self._ensure_named(PaymentForm, ["грант", "платное отделение"])

        family_types = self._ensure_named(FamilyType, ["полная", "неполная", "многодетная", "приемная", "семья в трудной жизненной ситуации"])
        income_levels = self._ensure_named(FamilyIncomeLevel, ["благополучное", "среднее", "затруднительное", "малообеспеченная"])
        housing_types = self._ensure_named(HousingType, ["проживает с родителями", "проживает отдельно", "общежитие", "съемное жилье"])
        temperaments = self._ensure_named(TemperamentType, ["спокойный", "активный", "уравновешенный", "конфликтный"])
        communications = self._ensure_named(CommunicationLevel, ["высокая", "средняя", "сниженная"])
        behaviors = self._ensure_named(GroupBehaviorType, ["сотрудничает", "лидер", "пассивный", "изолированный"])
        responsibilities = self._ensure_named(ResponsibilityLevel, ["высокий", "средний", "низкий"])
        adaptations = self._ensure_named(AdaptationLevel, ["высокая", "средняя", "низкая"])
        health_groups = self._ensure_named(HealthGroup, ["1", "2", "3", "спецгруппа"])

        last_names = ["Иванов", "Петрова", "Сулейменов", "Ким", "Нурланов", "Смирнова", "Ахметов", "Серикова", "Морозов", "Тлеубекова"]
        first_names = ["Алексей", "Мария", "Дамир", "Виктория", "Бекзат", "Анна", "Руслан", "Алина", "Егор", "Айгерим"]
        middle_names = ["Петрович", "Сергеевна", "Ержанович", "Андреевна", "Нурланович", "Дмитриевна", "Олегович", "Маратовна", "Игоревич", "Кайратовна"]
        activities = [
            "волонтерский клуб, спорт",
            "олимпиадный кружок, хакатоны",
            "студсовет, дебатный клуб",
            "секции по футболу",
            "минимальная внеучебная активность",
        ]

        created = 0
        for i in range(count):
            last_name = random.choice(last_names)
            first_name = random.choice(first_names)
            middle_name = random.choice(middle_names)

            iin = self._generate_iin(i)
            if Student.objects.filter(iin=iin).exists():
                continue

            birth_year = random.randint(2000, 2007)
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 27)

            student = Student.objects.create(
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                birth_date=date(birth_year, birth_month, birth_day),
                citizenship="Казахстан",
                nationality=random.choice(["казах", "русский", "уйгур", "татарин"]),
                iin=iin,
                phone=f"+7701{random.randint(1000000, 9999999)}",
                department=random.choice(departments),
                specialty=random.choice(specialties),
                course=random.randint(1, 4),
                group=random.choice(groups),
                payment_form=random.choice(payment_forms),
            )

            family = StudentFamily.objects.create(
                student=student,
                family_type=random.choice(family_types),
                income_level=random.choice(income_levels),
            )

            for n in range(random.randint(1, 4)):
                StudentFamilyMember.objects.create(
                    family=family,
                    full_name=f"{random.choice(last_names)} {random.choice(first_names)}",
                    birth_year=random.randint(1960, 2018),
                    relation=random.choice(["мать", "отец", "брат", "сестра", "опекун"]),
                    workplace=random.choice(["Школа", "Больница", "Частная компания", "ИП", ""]),
                    position=random.choice(["учитель", "врач", "менеджер", "инженер", ""]),
                    phone=f"+7702{random.randint(1000000, 9999999)}",
                    is_guardian=(n == 0 and random.choice([True, False])),
                    is_primary_contact=(n == 0),
                )

            StudentHousing.objects.create(
                student=student,
                housing_type=random.choice(housing_types),
                comment=random.choice(["", "Проживает с родственниками в городе", "Регулярно меняет место проживания"]),
            )

            StudentPsychoProfile.objects.create(
                student=student,
                temperament=random.choice(temperaments),
                communication=random.choice(communications),
                behavior_in_group=random.choice(behaviors),
                responsibility_level=random.choice(responsibilities),
                adaptation_level=random.choice(adaptations),
                description=random.choice(["Положительная динамика", "Требуется внимание к адаптации", "Стабильное поведение в группе"]),
            )

            attendance = random.choice(["good", "satisfactory", "problematic"])
            has_abs = random.choice([True, False, False])
            StudentAcademic.objects.create(
                student=student,
                gpa=round(random.uniform(2.0, 4.0), 2),
                attendance=attendance,
                has_unexcused_absences=has_abs,
                unexcused_absences_count=random.randint(0, 20) if has_abs else 0,
                activity=random.choice(activities),
            )

            has_disability = random.choice([False, False, False, True])
            StudentMedical.objects.create(
                student=student,
                health_group=random.choice(health_groups),
                has_disability=has_disability,
                disability_details="Ограничения по нагрузке" if has_disability else "",
                chronic_diseases=random.choice(["", "нет", "аллергия"]),
                recommendations=random.choice(["Плановое наблюдение", "Без специальных рекомендаций", "Рекомендована консультация специалиста"]),
            )

            StudentBenefits.objects.create(
                student=student,
                state_grant=(student.payment_form.name == "грант"),
                receives_scholarship=random.choice([True, False]),
                disability_allowance=has_disability and random.choice([True, False]),
                breadwinner_loss_allowance=random.choice([False, False, True]),
                preferential_housing=random.choice([False, False, True]),
                free_meals=random.choice([False, True]),
                additional_benefits=random.choice(["", "Единовременная поддержка", "Социальная помощь по заявлению"]),
            )

            build_ai_analysis(student)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Тестовые данные добавлены. Новых студентов: {created}"))

    @staticmethod
    def _ensure_named(model, names):
        result = []
        for name in names:
            obj, _ = model.objects.get_or_create(name=name)
            result.append(obj)
        return result

    @staticmethod
    def _generate_iin(seed):
        base = 950101 + random.randint(100000, 999999)
        suffix = (100000 + seed) % 1000000
        return f"{base:06d}{suffix:06d}"[:12]
