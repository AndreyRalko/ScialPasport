from datetime import date

NAME_PACKS = [
    {
        "weight": 70,
        "nationality": "kazakh",
        "male": {
            "last": [
                "Ахметов", "Жұмабеков", "Нұрланов", "Сүлейменов", "Серіков",
                "Болатов", "Қасымов", "Ержанов", "Тлеубеков", "Әлімов",
            ],
            "first": [
                "Алихан", "Арман", "Бекзат", "Дамир", "Дәулет",
                "Ерлан", "Нұрлан", "Руслан", "Серік", "Темірлан",
            ],
            "patronyms": [
                "Ержанұлы", "Нұрланұлы", "Серікұлы", "Қайратұлы", "Болатұлы",
                "Ермекұлы", "Маратұлы", "Асанұлы", "Бекзатұлы", "Дәулетұлы",
            ],
        },
        "female": {
            "last": [
                "Ахметова", "Жұмабекова", "Нұрланова", "Сүлейменова", "Серикова",
                "Болатова", "Қасымова", "Ержанова", "Тлеубекова", "Әлімова",
            ],
            "first": [
                "Айгерім", "Аружан", "Әлия", "Ақерке", "Дана",
                "Жанель", "Камшат", "Мәдина", "Айша", "Әсел",
            ],
            "patronyms": [
                "Ержанқызы", "Нұрланқызы", "Серікқызы", "Қайратқызы", "Болатқызы",
                "Ермекқызы", "Маратқызы", "Асанқызы", "Бекзатқызы", "Дәулетқызы",
            ],
        },
    },
    {
        "weight": 15,
        "nationality": "russian",
        "male": {
            "last": ["Иванов", "Петров", "Смирнов", "Кузнецов", "Соколов"],
            "first": ["Алексей", "Дмитрий", "Иван", "Сергей", "Андрей", "Павел"],
            "patronyms": [
                "Александрович", "Сергеевич", "Олегович", "Иванович",
                "Дмитриевич", "Андреевич", "Петрович", "Николаевич",
            ],
        },
        "female": {
            "last": ["Иванова", "Петрова", "Смирнова", "Кузнецова", "Соколова"],
            "first": ["Анна", "Мария", "Екатерина", "Ольга", "Виктория", "Дарья"],
            "patronyms": [
                "Александровна", "Сергеевна", "Олеговна", "Ивановна",
                "Дмитриевна", "Андреевна", "Петровна", "Николаевна",
            ],
        },
    },
    {
        "weight": 10,
        "nationality": "tatar",
        "male": {
            "last": ["Хакимов", "Гатиатуллин", "Сафин", "Валиев", "Юсупов"],
            "first": ["Марат", "Рустам", "Ильдар", "Айрат", "Тимур"],
            "patronyms": ["Маратович", "Рустамович", "Ильдарович", "Айратович", "Рашидович"],
        },
        "female": {
            "last": ["Хакимова", "Гатиатуллина", "Сафина", "Валиева", "Юсупова"],
            "first": ["Алсу", "Гузель", "Лейла", "Алина", "Камиля"],
            "patronyms": ["Маратовна", "Рустамовна", "Ильдаровна", "Айратовна", "Рашидовна"],
        },
    },
    {
        "weight": 5,
        "nationality": "uyghur",
        "male": {
            "last": ["Тохтахунов", "Розиев", "Абдуллаев", "Исмаилов"],
            "first": ["Әркин", "Мурат", "Алишер", "Бахтияр"],
            "patronyms": ["Әркинулы", "Муратулы", "Алишерулы", "Бахтиярулы"],
        },
        "female": {
            "last": ["Тохтахунова", "Розиева", "Абдуллаева", "Исмаилова"],
            "first": ["Мариям", "Гүлнара", "Дильбар", "Замира"],
            "patronyms": ["Әркинқызы", "Муратқызы", "Алишерқызы", "Бахтиярқызы"],
        },
    },
]


def is_female_iin(iin: str) -> bool | None:
    if not iin or len(iin) < 7 or not iin[6].isdigit():
        return None
    digit = int(iin[6])
    if digit in (1, 3, 5):
        return False
    if digit in (2, 4, 6):
        return True
    return None


def century_gender_digit(birth: date, female: bool) -> int:
    if birth.year >= 2000:
        return 6 if female else 5
    if birth.year >= 1900:
        return 4 if female else 3
    return 2 if female else 1


def iin_checksum(digits11: str) -> str:
    numbers = [int(char) for char in digits11]
    first = sum(number * weight for number, weight in zip(numbers, range(1, 12))) % 11
    if first < 10:
        return str(first)
    second = sum(number * weight for number, weight in zip(numbers, [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2])) % 11
    return str(second if second < 10 else 0)


def build_iin(birth: date, female: bool, serial: int) -> str:
    body = f"{birth:%y%m%d}{century_gender_digit(birth, female)}{serial % 10000:04d}"
    return body + iin_checksum(body)


def pick_pack(rng) -> dict:
    roll = rng.randint(1, sum(pack["weight"] for pack in NAME_PACKS))
    cursor = 0
    for pack in NAME_PACKS:
        cursor += pack["weight"]
        if roll <= cursor:
            return pack
    return NAME_PACKS[0]


def generate_identity(rng, index: int = 0) -> dict:
    female = bool(rng.randrange(2))
    pack = pick_pack(rng)
    names = pack["female"] if female else pack["male"]
    birth = date(rng.randint(2000, 2007), rng.randint(1, 12), rng.randint(1, 27))
    return {
        "female": female,
        "last_name": rng.choice(names["last"]),
        "first_name": rng.choice(names["first"]),
        "middle_name": rng.choice(names["patronyms"]),
        "nationality": pack["nationality"],
        "birth_date": birth,
        "iin": build_iin(birth, female, 1000 + index * 17 + rng.randint(0, 16)),
        "pack": pack,
    }


CITIZENSHIP_ALIASES = {
    "kz": "kz",
    "қазақстан": "kz",
    "казахстан": "kz",
}
NATIONALITY_ALIASES = {
    "kazakh": "kazakh",
    "қазақ": "kazakh",
    "казах": "kazakh",
    "russian": "russian",
    "орыс": "russian",
    "русский": "russian",
    "русская": "russian",
    "tatar": "tatar",
    "татар": "tatar",
    "татарин": "tatar",
    "uyghur": "uyghur",
    "ұйғыр": "uyghur",
    "уйгур": "uyghur",
}
RELATION_ALIASES = {
    "mother": "mother",
    "анасы": "mother",
    "мать": "mother",
    "father": "father",
    "әкесі": "father",
    "отец": "father",
    "brother": "brother",
    "ағасы": "brother",
    "брат": "brother",
    "sister": "sister",
    "әпкесі": "sister",
    "сіңлісі": "sister",
    "сестра": "sister",
    "guardian": "guardian",
    "қамқоршысы": "guardian",
    "опекун": "guardian",
}

WORKPLACES = ["Школа", "Больница", "Частная компания", "ИП"]
POSITIONS = ["учитель", "врач", "менеджер", "инженер"]
HOUSING_COMMENTS = [
    "",
    "Проживает у родственников в городе",
    "Часто меняет место жительства",
]
PSYCHO_NOTES = [
    "Положительная динамика",
    "Требует внимания к адаптации",
    "Поведение в группе устойчивое",
]
ACTIVITIES = [
    "волонтёрский клуб, спорт",
    "олимпиадный кружок, хакатоны",
    "студенческий совет, дискуссионный клуб",
    "секция футбола",
    "внеучебная активность низкая",
]
MEDICAL_CHRONIC = ["", "нет", "аллергия"]
MEDICAL_RECS = [
    "Плановое наблюдение",
    "Специальных рекомендаций нет",
    "Рекомендована консультация специалиста",
]
EXTRA_BENEFITS = ["", "Разовая поддержка", "Социальная помощь по заявлению"]


def normalize_code(value: str, aliases: dict) -> str:
    key = (value or "").strip().lower()
    return aliases.get(key, value)


def pack_by_identity(last_name: str = "", nationality: str = "") -> dict:
    code = normalize_code(nationality, NATIONALITY_ALIASES)
    for pack in NAME_PACKS:
        if pack["nationality"] == code:
            return pack
        if last_name in pack["male"]["last"] or last_name in pack["female"]["last"]:
            return pack
    return NAME_PACKS[0]


def paired_last_name(pack: dict, last_name: str, female: bool) -> str:
    males = pack["male"]["last"]
    females = pack["female"]["last"]
    if last_name in males:
        index = males.index(last_name)
        return females[index] if female else last_name
    if last_name in females:
        index = females.index(last_name)
        return last_name if female else males[index]
    names = pack["female"]["last"] if female else pack["male"]["last"]
    return names[0]


def _birth_year_for(relation: str, student_year: int, rng) -> int:
    if relation in {"mother", "guardian"}:
        return student_year - rng.randint(22, 36)
    if relation == "father":
        return student_year - rng.randint(24, 40)
    year = student_year + rng.randint(-7, 6)
    if year == student_year:
        year -= 1
    return min(max(year, student_year - 10), student_year + 8)


def generate_family_members(rng, student, family_type=None) -> list[dict]:
    pack = pack_by_identity(student.last_name, student.nationality)
    student_year = student.birth_date.year
    type_code = (getattr(family_type, "code", "") or "").lower()
    if "single" in type_code:
        roles = [rng.choice(["mother", "father"])]
        if rng.random() < 0.45:
            roles.append(rng.choice(["brother", "sister"]))
    elif "large" in type_code:
        roles = ["mother", "father", rng.choice(["brother", "sister"]), rng.choice(["brother", "sister"])]
    elif "foster" in type_code or "special" in type_code:
        roles = ["guardian"]
        if rng.random() < 0.5:
            roles.append(rng.choice(["brother", "sister"]))
    else:
        roles = ["mother", "father"]
        if rng.random() < 0.4:
            roles.append(rng.choice(["brother", "sister"]))

    members = []
    for index, relation in enumerate(roles):
        female = relation in {"mother", "sister"} or (relation == "guardian" and rng.randrange(2))
        names = pack["female"] if female else pack["male"]
        if relation in {"mother", "father", "brother", "sister"}:
            last_name = paired_last_name(pack, student.last_name, female)
        else:
            last_name = rng.choice(names["last"])
        members.append(
            {
                "full_name": f"{last_name} {rng.choice(names['first'])} {rng.choice(names['patronyms'])}",
                "birth_year": _birth_year_for(relation, student_year, rng),
                "relation": relation,
                "workplace": rng.choice(WORKPLACES),
                "position": rng.choice(POSITIONS),
                "phone": f"+7702{rng.randint(1000000, 9999999)}",
                "is_guardian": relation in {"mother", "father", "guardian"} and index == 0,
                "is_primary_contact": index == 0,
            }
        )
    return members
