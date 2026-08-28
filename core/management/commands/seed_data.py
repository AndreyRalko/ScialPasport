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
    StudyGroup,
    TemperamentType,
    UserRole,
)


REFERENCES = {
    Department: [
        {"code": "cs", "name": "Информатика және есептеу техникасы", "name_ru": "Информатика и вычислительная техника"},
        {"code": "econ", "name": "Экономика және менеджмент", "name_ru": "Экономика и менеджмент"},
        {"code": "law", "name": "Құқықтану", "name_ru": "Юриспруденция"},
    ],
    Specialty: [
        {"code": "se", "name": "Бағдарламалық инженерия", "name_ru": "Программная инженерия"},
        {"code": "is", "name": "Ақпараттық жүйелер", "name_ru": "Информационные системы"},
        {"code": "eco", "name": "Экономика", "name_ru": "Экономика"},
        {"code": "law", "name": "Құқық", "name_ru": "Право"},
    ],
    StudyGroup: [
        {"code": "pi21", "name": "ПИ-21", "name_ru": "ПИ-21"},
        {"code": "pi31", "name": "ПИ-31", "name_ru": "ПИ-31"},
        {"code": "f22", "name": "Ф-22", "name_ru": "Ф-22"},
        {"code": "is11", "name": "ИС-11", "name_ru": "ИС-11"},
        {"code": "pk41", "name": "ПК-41", "name_ru": "ПК-41"},
    ],
    PaymentForm: [
        {"code": "grant", "name": "грант", "name_ru": "грант"},
        {"code": "paid", "name": "ақылы бөлім", "name_ru": "платное отделение"},
    ],
    FamilyType: [
        {"code": "full", "name": "толық", "name_ru": "полная"},
        {"code": "single", "name": "толық емес", "name_ru": "неполная"},
        {"code": "large", "name": "көпбалалы", "name_ru": "многодетная"},
        {"code": "foster", "name": "асырап алушы", "name_ru": "приемная"},
        {"code": "special", "name": "ерекше мәртебелі отбасы", "name_ru": "семья с особым статусом"},
        {"code": "hard", "name": "қиын өмірлік жағдайдағы отбасы", "name_ru": "семья в трудной жизненной ситуации"},
    ],
    FamilyIncomeLevel: [
        {"code": "well", "name": "жақсы", "name_ru": "благополучное"},
        {"code": "mid", "name": "орташа", "name_ru": "среднее"},
        {"code": "hard", "name": "қиын", "name_ru": "затруднительное"},
        {"code": "low_income", "name": "аз қамтылған", "name_ru": "малообеспеченная"},
    ],
    HousingType: [
        {"code": "parents", "name": "ата-анасымен тұрады", "name_ru": "проживает с родителями"},
        {"code": "independent", "name": "жеке тұрады", "name_ru": "проживает отдельно"},
        {"code": "dormitory", "name": "жатақхана", "name_ru": "общежитие"},
        {"code": "rent", "name": "жалға алынған тұрғын үй", "name_ru": "съемное жилье"},
        {"code": "relatives", "name": "туыстарында тұрады", "name_ru": "проживает у родственников"},
    ],
    TemperamentType: [
        {"code": "calm", "name": "байсалды", "name_ru": "спокойный"},
        {"code": "active", "name": "белсенді", "name_ru": "активный"},
        {"code": "balanced", "name": "теңгерімді", "name_ru": "уравновешенный"},
        {"code": "conflict", "name": "қақтығысты", "name_ru": "конфликтный"},
        {"code": "reserved", "name": "тұйық", "name_ru": "замкнутый"},
    ],
    CommunicationLevel: [
        {"code": "high", "name": "жоғары", "name_ru": "высокая"},
        {"code": "mid", "name": "орташа", "name_ru": "средняя"},
        {"code": "low", "name": "төмендеген", "name_ru": "сниженная"},
    ],
    GroupBehaviorType: [
        {"code": "coop", "name": "ынтымақтасады", "name_ru": "сотрудничает"},
        {"code": "leader", "name": "көшбасшы", "name_ru": "лидер"},
        {"code": "passive", "name": "енжар", "name_ru": "пассивный"},
        {"code": "isolated", "name": "оқшауланған", "name_ru": "изолированный"},
    ],
    ResponsibilityLevel: [
        {"code": "high", "name": "жоғары", "name_ru": "высокий"},
        {"code": "mid", "name": "орташа", "name_ru": "средний"},
        {"code": "low", "name": "төмен", "name_ru": "низкий"},
    ],
    AdaptationLevel: [
        {"code": "high", "name": "жоғары", "name_ru": "высокая"},
        {"code": "mid", "name": "орташа", "name_ru": "средняя"},
        {"code": "low", "name": "төмен", "name_ru": "низкая"},
    ],
    HealthGroup: [
        {"code": "g1", "name": "1", "name_ru": "1"},
        {"code": "g2", "name": "2", "name_ru": "2"},
        {"code": "g3", "name": "3", "name_ru": "3"},
        {"code": "special", "name": "арнайы топ", "name_ru": "спецгруппа"},
    ],
    UserRole: [
        {"code": "admin", "name": "Жүйе әкімшісі", "name_ru": "Администратор системы"},
        {"code": "curator", "name": "Куратор / тәлімгер", "name_ru": "Куратор / наставник"},
        {"code": "social", "name": "Әлеуметтік педагог", "name_ru": "Социальный педагог"},
        {"code": "psychologist", "name": "Психолог", "name_ru": "Психолог"},
        {"code": "head", "name": "Кафедра меңгерушісі", "name_ru": "Заведующий кафедрой"},
        {"code": "student", "name": "Студент", "name_ru": "Студент"},
    ],
}


class Command(BaseCommand):
    help = "Заполняет базовые справочники и роли."

    def handle(self, *args, **options):
        for model, values in REFERENCES.items():
            used_codes = set()
            for index, item in enumerate(values):
                code = f"{model._meta.model_name}_{item['code']}"
                if code in used_codes:
                    code = f"{code}_{index}"
                used_codes.add(code)
                obj = (
                    model.objects.filter(code=code).first()
                    or model.objects.filter(name=item["name"]).first()
                    or model.objects.filter(name=item["name_ru"]).first()
                )
                if obj:
                    obj.name = item["name"]
                    obj.name_ru = item["name_ru"]
                    obj.code = code
                    obj.save(update_fields=["name", "name_ru", "code", "updated_at"])
                else:
                    model.objects.create(name=item["name"], name_ru=item["name_ru"], code=code)

        from core.admin_panel import assign_default_group_permissions, sync_role_group

        for role in UserRole.objects.all():
            sync_role_group(role)
        assign_default_group_permissions()

        self.stdout.write(self.style.SUCCESS("Базовые справочники заполнены."))
