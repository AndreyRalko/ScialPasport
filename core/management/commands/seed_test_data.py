import random

from django.core.management.base import BaseCommand

from core.cabinet import ensure_student_account
from core.identity import (
    ACTIVITIES,
    CITIZENSHIP_ALIASES,
    EXTRA_BENEFITS,
    HOUSING_COMMENTS,
    MEDICAL_CHRONIC,
    MEDICAL_RECS,
    NATIONALITY_ALIASES,
    PSYCHO_NOTES,
    build_iin,
    generate_family_members,
    generate_identity,
    normalize_code,
)
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
from core.photos import save_student_photo
from core.services import build_ai_analysis


class Command(BaseCommand):
    help = "Заполняет систему тестовыми данными студентов и связанных блоков."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=30, help="Количество студентов для генерации")
        parser.add_argument("--force", action="store_true", help="Добавлять студентов, даже если они уже есть")
        parser.add_argument("--replace", action="store_true", help="Удалить существующих студентов и создать заново")
        parser.add_argument(
            "--fix-identity",
            action="store_true",
            help="Исправить пол, отчество, язык ФИО и ИИН у существующих студентов",
        )
        parser.add_argument(
            "--fix-mocks",
            action="store_true",
            help="Исправить язык полей, семью, возраста и фото у существующих студентов",
        )

    def handle(self, *args, **options):
        count = options["count"]
        if options.get("fix_mocks"):
            self._fix_mocks()
            return
        if options.get("fix_identity"):
            self._fix_identities()
            return
        if options.get("replace"):
            Student.objects.all().delete()
        elif Student.objects.exists() and not options.get("force"):
            self.stdout.write("Студенты уже есть, генерация пропущена.")
            return

        departments = list(Department.objects.all()) or self._ensure_named(
            Department, ["Информатика және есептеу техникасы"]
        )
        specialties = list(Specialty.objects.all()) or self._ensure_named(Specialty, ["Бағдарламалық инженерия"])
        groups = list(StudyGroup.objects.all()) or self._ensure_named(StudyGroup, ["ПИ-21"])
        payment_forms = list(PaymentForm.objects.all()) or self._ensure_named(PaymentForm, ["грант"])
        family_types = list(FamilyType.objects.all())
        income_levels = list(FamilyIncomeLevel.objects.all())
        housing_types = list(HousingType.objects.all())
        temperaments = list(TemperamentType.objects.all())
        communications = list(CommunicationLevel.objects.all())
        behaviors = list(GroupBehaviorType.objects.all())
        responsibilities = list(ResponsibilityLevel.objects.all())
        adaptations = list(AdaptationLevel.objects.all())
        health_groups = list(HealthGroup.objects.all())

        created = 0
        for i in range(count):
            identity = generate_identity(random, i)
            iin = self._unique_iin(identity["iin"], identity["birth_date"], identity["female"])

            student = Student.objects.create(
                last_name=identity["last_name"],
                first_name=identity["first_name"],
                middle_name=identity["middle_name"],
                birth_date=identity["birth_date"],
                citizenship="kz",
                nationality=identity["nationality"],
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
                family_type=random.choice(family_types) if family_types else None,
                income_level=random.choice(income_levels) if income_levels else None,
            )

            for member in generate_family_members(random, student, family.family_type):
                StudentFamilyMember.objects.create(family=family, **member)

            StudentHousing.objects.create(
                student=student,
                housing_type=random.choice(housing_types) if housing_types else None,
                comment=random.choice(HOUSING_COMMENTS),
            )

            StudentPsychoProfile.objects.create(
                student=student,
                temperament=random.choice(temperaments) if temperaments else None,
                communication=random.choice(communications) if communications else None,
                behavior_in_group=random.choice(behaviors) if behaviors else None,
                responsibility_level=random.choice(responsibilities) if responsibilities else None,
                adaptation_level=random.choice(adaptations) if adaptations else None,
                description=random.choice(PSYCHO_NOTES),
            )

            attendance = random.choice(["good", "satisfactory", "problematic"])
            has_abs = random.choice([True, False, False])
            StudentAcademic.objects.create(
                student=student,
                gpa=round(random.uniform(2.0, 4.0), 2),
                attendance=attendance,
                has_unexcused_absences=has_abs,
                unexcused_absences_count=random.randint(0, 20) if has_abs else 0,
                activity=random.choice(ACTIVITIES),
            )

            has_disability = random.choice([False, False, False, True])
            StudentMedical.objects.create(
                student=student,
                health_group=random.choice(health_groups) if health_groups else None,
                has_disability=has_disability,
                disability_details="Ограничения по нагрузке" if has_disability else "",
                chronic_diseases=random.choice(MEDICAL_CHRONIC),
                recommendations=random.choice(MEDICAL_RECS),
            )

            grant = bool(student.payment_form and student.payment_form.code == "paymentform_grant")
            StudentBenefits.objects.create(
                student=student,
                state_grant=grant or student.payment_form.name == "грант",
                receives_scholarship=random.choice([True, False]),
                disability_allowance=has_disability and random.choice([True, False]),
                breadwinner_loss_allowance=random.choice([False, False, True]),
                preferential_housing=random.choice([False, False, True]),
                free_meals=random.choice([False, True]),
                additional_benefits=random.choice(EXTRA_BENEFITS),
            )

            build_ai_analysis(student)
            save_student_photo(student)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Тестовые данные добавлены. Новых студентов: {created}"))

    @staticmethod
    def _ensure_named(model, names):
        result = []
        for name in names:
            obj, _ = model.objects.get_or_create(name=name)
            result.append(obj)
        return result

    def _fix_identities(self):
        updated = 0
        for index, student in enumerate(Student.objects.select_related("user").all(), start=1):
            identity = generate_identity(random, index)
            student.last_name = identity["last_name"]
            student.first_name = identity["first_name"]
            student.middle_name = identity["middle_name"]
            student.birth_date = identity["birth_date"]
            student.nationality = identity["nationality"]
            student.citizenship = "kz"
            student.iin = self._unique_iin(
                identity["iin"],
                identity["birth_date"],
                identity["female"],
                exclude_pk=student.pk,
            )
            student.save(
                update_fields=[
                    "last_name",
                    "first_name",
                    "middle_name",
                    "birth_date",
                    "nationality",
                    "citizenship",
                    "iin",
                    "updated_at",
                ]
            )
            ensure_student_account(student)
            try:
                save_student_photo(student, force=True)
            except Exception as exc:
                self.stderr.write(f"Фото не обновлено для {student.iin}: {exc}")
            updated += 1
            self.stdout.write(f"{student.iin}  {student.full_name}")
        self.stdout.write(self.style.SUCCESS(f"Идентичность обновлена у {updated} студентов."))

    def _fix_mocks(self):
        updated = 0
        for student in Student.objects.all():
            student.citizenship = normalize_code(student.citizenship, CITIZENSHIP_ALIASES) or "kz"
            student.nationality = normalize_code(student.nationality, NATIONALITY_ALIASES) or "kazakh"
            student.save(update_fields=["citizenship", "nationality", "updated_at"])

            family = StudentFamily.objects.filter(student=student).first()
            if family:
                family.members.all().delete()
                for member in generate_family_members(random, student, family.family_type):
                    StudentFamilyMember.objects.create(family=family, **member)

            housing = StudentHousing.objects.filter(student=student).first()
            if housing:
                housing.comment = random.choice(HOUSING_COMMENTS)
                housing.save(update_fields=["comment"])
            psycho = StudentPsychoProfile.objects.filter(student=student).first()
            if psycho:
                psycho.description = random.choice(PSYCHO_NOTES)
                psycho.save(update_fields=["description"])
            academic = StudentAcademic.objects.filter(student=student).first()
            if academic:
                academic.activity = random.choice(ACTIVITIES)
                academic.save(update_fields=["activity"])
            medical = StudentMedical.objects.filter(student=student).first()
            if medical:
                medical.disability_details = "Ограничения по нагрузке" if medical.has_disability else ""
                medical.chronic_diseases = random.choice(MEDICAL_CHRONIC)
                medical.recommendations = random.choice(MEDICAL_RECS)
                medical.save(update_fields=["disability_details", "chronic_diseases", "recommendations"])
            benefits = StudentBenefits.objects.filter(student=student).first()
            if benefits:
                benefits.additional_benefits = random.choice(EXTRA_BENEFITS)
                benefits.save(update_fields=["additional_benefits"])

            try:
                save_student_photo(student, force=True)
            except Exception as exc:
                self.stderr.write(f"Фото не обновлено для {student.iin}: {exc}")
            updated += 1
            self.stdout.write(f"{student.iin}  {student.full_name}")
        self.stdout.write(self.style.SUCCESS(f"Мок-данные обновлены у {updated} студентов."))

    @staticmethod
    def _unique_iin(candidate, birth, female, exclude_pk=None):
        serial = int(candidate[7:11]) if len(candidate) >= 11 else 1000
        for step in range(10000):
            iin = build_iin(birth, female, serial + step)
            qs = Student.objects.filter(iin=iin)
            if exclude_pk:
                qs = qs.exclude(pk=exclude_pk)
            if not qs.exists():
                return iin
        raise RuntimeError("Не удалось подобрать уникальный ИИН.")
