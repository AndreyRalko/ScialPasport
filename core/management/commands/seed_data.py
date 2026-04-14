from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.models import (
    AdaptationLevel,
    CommunicationLevel,
    FamilyIncomeLevel,
    FamilyType,
    GroupBehaviorType,
    HealthGroup,
    HousingType,
    PaymentForm,
    ResponsibilityLevel,
    TemperamentType,
    UserRole,
)


class Command(BaseCommand):
    help = "Заполняет базовые справочники и роли."

    def handle(self, *args, **options):
        references = {
            PaymentForm: ["грант", "платное отделение"],
            FamilyType: [
                "полная",
                "неполная",
                "многодетная",
                "приемная",
                "семья с особым статусом",
                "семья в трудной жизненной ситуации",
            ],
            FamilyIncomeLevel: ["благополучное", "среднее", "затруднительное", "малообеспеченная"],
            HousingType: [
                "проживает с родителями",
                "проживает отдельно",
                "общежитие",
                "съемное жилье",
                "проживает у родственников",
            ],
            TemperamentType: ["спокойный", "активный", "уравновешенный", "конфликтный", "замкнутый"],
            CommunicationLevel: ["высокая", "средняя", "сниженная"],
            GroupBehaviorType: ["сотрудничает", "лидер", "пассивный", "изолированный"],
            ResponsibilityLevel: ["высокий", "средний", "низкий"],
            AdaptationLevel: ["высокая", "средняя", "низкая"],
            HealthGroup: ["1", "2", "3", "спецгруппа"],
            UserRole: ["Администратор системы", "Куратор / наставник"],
        }

        for model, values in references.items():
            for value in values:
                model.objects.get_or_create(name=value)

        for group_name in ("Администратор системы", "Куратор / наставник"):
            Group.objects.get_or_create(name=group_name)

        self.stdout.write(self.style.SUCCESS("Базовые справочники заполнены."))
