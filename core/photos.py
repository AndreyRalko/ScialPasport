import hashlib
import json
import time
import urllib.error
import urllib.request
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image


FEMALE_NAMES = {
    "мария", "виктория", "анна", "алина", "айгерим", "айгерім", "петрова", "смирнова",
    "серикова", "тлеубекова", "алия", "әлия", "ақерке", "дана", "айша", "камшат",
    "аружан", "мадина", "мәдина", "жанель", "қасымова", "әлімова", "әсел",
    "олга", "екатерина", "дарья", "алсу", "гузель", "лейла", "камиля",
    "мариям", "гүлнара", "дильбар", "замира",
}

USER_AGENT = "Mozilla/5.0 (compatible; SocialPassport/1.0)"


def infer_female_name(first_name: str, last_name: str = "", iin: str = "") -> bool:
    from .identity import is_female_iin

    flagged = is_female_iin(iin)
    if flagged is not None:
        return flagged
    first = (first_name or "").strip().lower()
    last = (last_name or "").strip().lower()
    if first in FEMALE_NAMES or last in FEMALE_NAMES:
        return True
    return first.endswith(("а", "я", "ә")) and first not in {"муса", "мустафа", "илья"}


def _hash_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)


def _download(url: str, timeout=25) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _to_portrait(payload: bytes) -> bytes:
    image = Image.open(BytesIO(payload)).convert("RGB")
    width, height = image.size
    # Cut generator watermarks that sit on the top and bottom edges.
    image = image.crop((
        int(width * 0.02),
        int(height * 0.08),
        int(width * 0.98),
        int(height * 0.93),
    ))
    width, height = image.size
    target_ratio = 4 / 5
    current_ratio = width / height
    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        image = image.crop((left, 0, left + new_width, height))
    elif current_ratio < target_ratio:
        new_height = int(width / target_ratio)
        top = max(0, (height - new_height) // 5)
        image = image.crop((0, top, width, min(height, top + new_height)))
    image = image.resize((480, 600), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _from_this_person(female: bool) -> bytes:
    gender = "female" if female else "male"
    meta_url = (
        "https://this-person-does-not-exist.com/new"
        f"?gender={gender}&age=19-25&etnic=all"
    )
    meta = json.loads(_download(meta_url).decode("utf-8"))
    src = meta.get("src")
    if not src:
        raise RuntimeError("this-person-does-not-exist returned no image")
    return _download("https://this-person-does-not-exist.com" + src)


def _from_pravatar(seed: str) -> bytes:
    return _download(f"https://i.pravatar.cc/512?u={seed}")


def _from_randomuser(seed: str, female: bool) -> bytes:
    folder = "women" if female else "men"
    index = _hash_int(seed) % 99
    return _download(f"https://randomuser.me/api/portraits/{folder}/{index}.jpg")


def generate_portrait_bytes(seed: str, initials: str = "", female=None) -> bytes:
    if female is None:
        female = bool(_hash_int(seed) % 2)
    errors = []
    for loader in (
        lambda: _from_this_person(female),
        lambda: _from_randomuser(seed, female),
        lambda: _from_pravatar(seed),
    ):
        try:
            return _to_portrait(loader())
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            time.sleep(0.4)
    raise RuntimeError("Could not download a real portrait: " + " | ".join(errors))


def save_student_photo(student, force=False):
    if student.photo and not force:
        return False

    payload = generate_portrait_bytes(
        student.iin or str(student.pk),
        female=infer_female_name(student.first_name, student.last_name, student.iin),
    )
    filename = f"{student.iin or student.pk}.jpg"
    if student.photo:
        student.photo.delete(save=False)
    student.photo.save(filename, ContentFile(payload), save=True)
    return True
