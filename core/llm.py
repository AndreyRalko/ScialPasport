import json
import re
import urllib.error
import urllib.request

from django.utils.translation import gettext as _

from .models import AISettings

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
IIN_RE = re.compile(r"\b\d{12}\b")

PROVIDER_MODELS = {
    AISettings.PROVIDER_OPENAI: {
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4.1-mini",
        "gpt-4.1",
    },
    AISettings.PROVIDER_CLAUDE: {
        "claude-sonnet-4-20250514",
        "claude-3-7-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-opus-4-20250514",
    },
}


class LLMError(Exception):
    pass


def sanitize_text(text: str) -> str:
    return IIN_RE.sub("************", text or "")


def student_brief(student) -> dict:
    academic = getattr(student, "academic", None)
    family = getattr(student, "family", None)
    housing = getattr(student, "housing", None)
    psycho = getattr(student, "psycho", None)
    benefits = getattr(student, "benefits", None)
    return {
        "full_name": student.full_name,
        "course": student.course,
        "group": str(getattr(student, "group", "") or ""),
        "department": str(getattr(student, "department", "") or ""),
        "specialty": str(getattr(student, "specialty", "") or ""),
        "gpa": getattr(academic, "gpa", None),
        "attendance": getattr(academic, "attendance", ""),
        "has_unexcused_absences": bool(getattr(academic, "has_unexcused_absences", False)),
        "activity": getattr(academic, "activity", ""),
        "family_type": str(getattr(family, "family_type", "") or ""),
        "housing_type": str(getattr(housing, "housing_type", "") or ""),
        "adaptation": str(getattr(psycho, "adaptation_level", "") or ""),
        "state_grant": bool(getattr(benefits, "state_grant", False)),
        "scholarship": bool(getattr(benefits, "receives_scholarship", False)),
    }


def complete(system: str, user: str, *, max_tokens: int = 800, timeout: int = 30, settings: AISettings | None = None) -> str:
    settings = settings or AISettings.load()
    if not settings.api_key:
        raise LLMError(_("API-ключ не задан."))
    if settings.provider == AISettings.PROVIDER_CLAUDE:
        return _complete_claude(settings, system, user, max_tokens, timeout)
    return _complete_openai(settings, system, user, max_tokens, timeout)


def complete_json(system: str, user: str, **kwargs) -> dict:
    raw = complete(system, user, **kwargs).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(_("Модель вернула ответ не в формате JSON.")) from exc
    if not isinstance(data, dict):
        raise LLMError(_("Модель вернула неожиданный JSON."))
    return data


def ping(settings: AISettings) -> str:
    text = complete(
        "Reply with the single word OK.",
        "Health check.",
        max_tokens=16,
        timeout=20,
        settings=settings,
    )
    return (text or "").strip()


def _request_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            raw = json.loads(exc.read().decode("utf-8"))
            detail = (
                raw.get("error", {}).get("message")
                or raw.get("error", {}).get("type")
                or raw.get("message")
                or ""
            )
        except Exception:
            detail = ""
        if exc.code in (401, 403):
            raise LLMError(_("API-ключ отклонён провайдером.")) from exc
        if exc.code == 429:
            raise LLMError(_("Превышен лимит запросов к модели.")) from exc
        raise LLMError(_("Ошибка API (%(code)s)%(detail)s") % {
            "code": exc.code,
            "detail": f": {detail}" if detail else "",
        }) from exc
    except urllib.error.URLError as exc:
        raise LLMError(_("Не удалось связаться с API провайдера.")) from exc


def _complete_openai(settings: AISettings, system: str, user: str, max_tokens: int, timeout: int) -> str:
    data = _request_json(
        OPENAI_URL,
        {
            "model": settings.model,
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        timeout,
    )
    choices = data.get("choices") or []
    if not choices:
        raise LLMError(_("Пустой ответ модели OpenAI."))
    return (choices[0].get("message") or {}).get("content") or ""


def _complete_claude(settings: AISettings, system: str, user: str, max_tokens: int, timeout: int) -> str:
    data = _request_json(
        CLAUDE_URL,
        {
            "model": settings.model,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        {
            "x-api-key": settings.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        timeout,
    )
    chunks = data.get("content") or []
    text = "".join(part.get("text", "") for part in chunks if part.get("type") == "text")
    if not text:
        raise LLMError(_("Пустой ответ модели Claude."))
    return text
