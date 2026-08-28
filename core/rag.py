import re
from dataclasses import dataclass, field

from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _

from .dashboard import get_dashboard_stats
from .models import Student


TOKEN_RE = re.compile(r"[0-9a-zа-яёәғқңөұүһіі\-]+", re.IGNORECASE)

SYNONYMS = {
    "high_risk": [
        "высокий", "риск", "жоғары", "тәуекел", "attention", "вниман", "назар",
        "опасн", "critical", "high",
    ],
    "medium_risk": ["средний", "орташа", "medium"],
    "low_adaptation": [
        "адаптац", "бейімдел", "низк", "төмен", "психолог",
    ],
    "attendance": [
        "посещаем", "пропуск", "қатысу", "сабақ", "attendance", "problematic",
        "проблемн",
    ],
    "dormitory": ["общежит", "жатақхана", "dorm", "жиль", "тұрғын"],
    "low_income": [
        "малообеспеч", "аз", "қамтылған", "доход", "материал", "киын", "қиын",
    ],
    "disability": ["инвалид", "мүгедек", "disability"],
    "grant": ["грант", "стипенд"],
    "stats": [
        "сколько", "қанша", "статистик", "сводк", "итог", "барлық", "всего",
        "дашборд", "dashboard",
    ],
}


@dataclass
class KnowledgeDoc:
    doc_id: str
    title: str
    text: str
    url: str = ""
    student_id: int | None = None
    tokens: set[str] = field(default_factory=set)
    photo_url: str = ""

    def __post_init__(self):
        self.tokens = set(tokenize(self.title + " " + self.text))


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


def _ref_text(obj) -> str:
    if not obj:
        return ""
    return " ".join(part for part in [getattr(obj, "name", ""), getattr(obj, "name_ru", "")] if part)


def build_student_document(student: Student) -> KnowledgeDoc:
    academic = getattr(student, "academic", None)
    family = getattr(student, "family", None)
    housing = getattr(student, "housing", None)
    psycho = getattr(student, "psycho", None)
    medical = getattr(student, "medical", None)
    benefits = getattr(student, "benefits", None)
    latest = student.ai_analyses.first() if hasattr(student, "ai_analyses") else None

    parts = [
        student.full_name,
        student.iin,
        student.phone,
        student.citizenship,
        student.nationality,
        _ref_text(student.department),
        _ref_text(student.specialty),
        _ref_text(student.group),
        _ref_text(student.payment_form),
        f"{_('Курс')} {student.course}",
    ]
    if family:
        parts.append(_ref_text(family.family_type))
        parts.append(_ref_text(family.income_level))
    if housing:
        parts.append(_ref_text(housing.housing_type))
        parts.append(housing.comment)
    if psycho:
        parts.extend([
            _ref_text(psycho.temperament),
            _ref_text(psycho.communication),
            _ref_text(psycho.adaptation_level),
            psycho.description,
        ])
    if academic:
        parts.extend([
            str(academic.gpa or ""),
            academic.get_attendance_display(),
            academic.activity,
        ])
        if academic.has_unexcused_absences:
            parts.append(_("Пропуски без уважительной причины"))
    if medical:
        parts.append(_ref_text(medical.health_group))
        if medical.has_disability:
            parts.append(_("Инвалидность"))
            parts.append(medical.disability_details)
        parts.append(medical.chronic_diseases)
    if benefits:
        if benefits.state_grant:
            parts.append(_("Государственный грант"))
        if benefits.receives_scholarship:
            parts.append(_("Стипендия"))
        if benefits.free_meals:
            parts.append(_("Бесплатное питание"))
        parts.append(benefits.additional_benefits)
    if latest:
        parts.extend([
            latest.get_risk_level_display(),
            latest.get_support_level_display(),
            latest.short_profile,
            latest.strengths,
            latest.risk_factors,
            latest.recommendations,
        ])

    photo_url = ""
    if student.photo:
        try:
            photo_url = student.photo.url
        except ValueError:
            photo_url = ""

    return KnowledgeDoc(
        doc_id=f"student:{student.pk}",
        title=student.full_name,
        text=" ".join(str(part) for part in parts if part),
        url=reverse("student-detail", args=[student.pk]),
        student_id=student.pk,
        photo_url=photo_url,
    )


def build_corpus() -> list[KnowledgeDoc]:
    students = (
        Student.objects.select_related(
            "department", "specialty", "group", "payment_form",
            "family", "family__family_type", "family__income_level",
            "housing", "housing__housing_type",
            "psycho", "psycho__adaptation_level", "psycho__temperament", "psycho__communication",
            "academic", "medical", "medical__health_group", "benefits",
        )
        .prefetch_related("ai_analyses")
    )
    docs = [build_student_document(student) for student in students]
    stats = get_dashboard_stats()
    summary = (
        f"{_('Студенты')}: {stats['total_students']}. "
        f"{_('Высокий риск')}: {stats['high_risk']}. "
        f"{_('Средний риск')}: {stats['medium_risk']}. "
        f"{_('Низкая адаптация')}: {stats['low_adaptation']}. "
        f"{_('Проблемная посещаемость')}: {stats['problem_attendance']}. "
        f"{_('Студенты из малообеспеченных семей')}: {stats['low_income']}. "
        f"{_('Студенты, проживающие в общежитии')}: {stats['dormitory']}. "
        f"{_('Студенты с инвалидностью')}: {stats['disability']}."
    )
    docs.append(
        KnowledgeDoc(
            doc_id="system:stats",
            title=_("Сводка системы"),
            text=summary,
            url=reverse("home"),
        )
    )
    return docs


def detect_intents(query: str) -> set[str]:
    tokens = tokenize(query)
    blob = " ".join(tokens)
    found = set()
    for intent, words in SYNONYMS.items():
        if any(word in blob for word in words):
            found.add(intent)
    return found


def retrieve(query: str, limit=6) -> list[tuple[float, KnowledgeDoc]]:
    docs = build_corpus()
    query_tokens = set(tokenize(query))
    intents = detect_intents(query)
    scored = []
    for doc in docs:
        score = 0.0
        if query_tokens:
            overlap = query_tokens & doc.tokens
            score += len(overlap) * 3
            for token in query_tokens:
                if token in doc.title.lower():
                    score += 8
                if token.isdigit() and token in doc.text:
                    score += 10
        if "high_risk" in intents and "высок" in doc.text.lower() or "жоғары" in doc.text.lower() and "тәуекел" in tokenize(query):
            score += 1
        if score > 0 or doc.doc_id == "system:stats" and "stats" in intents:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored and docs:
        return [(1.0, docs[-1])]
    return scored[:limit]


def _student_payload(doc: KnowledgeDoc) -> dict | None:
    if not doc.student_id:
        return None
    return {
        "id": doc.student_id,
        "name": doc.title,
        "url": doc.url,
        "photo": doc.photo_url,
    }


def _list_students(queryset, title: str, empty: str) -> dict:
    students = list(queryset.select_related("group")[:12])
    lines = [title]
    sources = []
    payload = []
    if not students:
        return {"answer": empty, "sources": [], "students": []}
    for student in students:
        latest = student.ai_analyses.first() if hasattr(student, "ai_analyses") else None
        risk = latest.get_risk_level_display() if latest else "—"
        lines.append(f"• {student.full_name} — {student.group}, {_('Курс')} {student.course}, {risk}")
        url = reverse("student-detail", args=[student.pk])
        sources.append({"title": student.full_name, "url": url, "snippet": risk})
        photo = ""
        if student.photo:
            try:
                photo = student.photo.url
            except ValueError:
                photo = ""
        payload.append({"id": student.pk, "name": student.full_name, "url": url, "photo": photo})
    return {"answer": "\n".join(lines), "sources": sources, "students": payload}


def answer_question(query: str) -> dict:
    query = (query or "").strip()
    if not query:
        return {
            "answer": _("Введите вопрос по студентам, рискам или отчётам."),
            "sources": [],
            "students": [],
        }

    local = _answer_locally(query)
    from .llm import LLMError, complete, sanitize_text
    from .models import AISettings

    settings = AISettings.load()
    if not settings.is_ready():
        return local
    context_bits = [local.get("answer") or ""]
    for source in local.get("sources") or []:
        context_bits.append(f"{source.get('title')}: {source.get('snippet')}")
    try:
        answer = complete(
            (
                "You are an assistant for a university social-passport system. "
                "Answer only from the provided data. Do not invent students or numbers. "
                "Reply in the same language as the user question. Keep the answer concise."
            ),
            f"Question:\n{query}\n\nData:\n{sanitize_text(chr(10).join(context_bits))}",
            max_tokens=500,
            timeout=25,
            settings=settings,
        )
        answer = sanitize_text(answer).strip()
        if answer:
            local["answer"] = answer
    except LLMError:
        return local
    return local


def _answer_locally(query: str) -> dict:
    intents = detect_intents(query)
    stats = get_dashboard_stats()
    qs = Student.objects.select_related("group", "department").prefetch_related("ai_analyses")

    if "stats" in intents and not (intents - {"stats"}):
        answer = _(
            "В системе %(total)s студентов. Высокий риск: %(high)s, средняя адаптация/риск: %(mid)s, "
            "низкая адаптация: %(adapt)s, проблемная посещаемость: %(att)s, "
            "малообеспеченные: %(poor)s, общежитие: %(dorm)s."
        ) % {
            "total": stats["total_students"],
            "high": stats["high_risk"],
            "mid": stats["medium_risk"],
            "adapt": stats["low_adaptation"],
            "att": stats["problem_attendance"],
            "poor": stats["low_income"],
            "dorm": stats["dormitory"],
        }
        return {
            "answer": answer,
            "sources": [{"title": _("Сводка системы"), "url": reverse("home"), "snippet": answer}],
            "students": [],
        }

    if "high_risk" in intents:
        return _list_students(
            qs.filter(ai_analyses__risk_level="high").distinct(),
            _("Студенты с высоким риском по данным ИИ-анализа:"),
            _("Студенты с высоким риском не найдены."),
        )
    if "low_adaptation" in intents:
        return _list_students(
            qs.filter(
                Q(psycho__adaptation_level__code="adaptationlevel_low")
                | Q(psycho__adaptation_level__name_ru__icontains="низ")
            ).distinct(),
            _("Студенты с низкой адаптацией:"),
            _("Студенты с низкой адаптацией не найдены."),
        )
    if "attendance" in intents:
        return _list_students(
            qs.filter(academic__attendance="problematic"),
            _("Студенты с проблемной посещаемостью:"),
            _("Студенты с проблемной посещаемостью не найдены."),
        )
    if "dormitory" in intents:
        return _list_students(
            qs.filter(
                Q(housing__housing_type__code="housingtype_dormitory")
                | Q(housing__housing_type__name_ru__icontains="общежит")
            ).distinct(),
            _("Студенты, проживающие в общежитии:"),
            _("Студенты в общежитии не найдены."),
        )
    if "low_income" in intents:
        return _list_students(
            qs.filter(
                Q(family__income_level__code="familyincomelevel_low_income")
                | Q(family__income_level__name_ru__icontains="малообеспеч")
            ).distinct(),
            _("Студенты из малообеспеченных семей:"),
            _("Малообеспеченные студенты не найдены."),
        )
    if "disability" in intents:
        return _list_students(
            qs.filter(medical__has_disability=True),
            _("Студенты с инвалидностью:"),
            _("Студенты с инвалидностью не найдены."),
        )

    ranked = retrieve(query)
    if not ranked:
        return {
            "answer": _("По запросу ничего не найдено в базе социального паспорта."),
            "sources": [],
            "students": [],
        }

    lines = [_("Ответ по данным социального паспорта (RAG):")]
    sources = []
    students = []
    for score, doc in ranked:
        if doc.student_id:
            snippet = " ".join(doc.text.split()[:28])
            lines.append(f"• {doc.title}: {snippet}…")
            sources.append({"title": doc.title, "url": doc.url, "snippet": snippet})
            payload = _student_payload(doc)
            if payload:
                students.append(payload)
        elif doc.doc_id == "system:stats":
            lines.append(doc.text)
            sources.append({"title": doc.title, "url": doc.url, "snippet": doc.text})

    return {"answer": "\n".join(lines), "sources": sources[:6], "students": students[:6]}
