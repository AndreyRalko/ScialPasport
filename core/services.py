from collections import defaultdict

from .models import Student, StudentAIAnalysis

CARD_BLOCKS = [
    ("family", "Семья"),
    ("housing", "Жильё"),
    ("psycho", "Характеристика"),
    ("academic", "Учёба"),
    ("medical", "Медицина"),
    ("benefits", "Льготы"),
    ("ai", "ИИ-анализ"),
]


def build_ai_analysis(student: Student) -> StudentAIAnalysis:
    risk_points = 0
    strengths = []
    risks = []
    recommendations = []

    academic = getattr(student, "academic", None)
    family = getattr(student, "family", None)
    psycho = getattr(student, "psycho", None)
    medical = getattr(student, "medical", None)

    if academic:
        if academic.gpa and academic.gpa >= 3.3:
            strengths.append("Стабильная академическая успеваемость")
        if academic.attendance == "problematic":
            risk_points += 2
            risks.append("Проблемная посещаемость")
            recommendations.append("Обратить внимание на частые пропуски")
        if academic.has_unexcused_absences:
            risk_points += 2
            risks.append("Есть пропуски без уважительной причины")
            recommendations.append("Провести индивидуальную беседу куратора")
        if academic.activity:
            strengths.append("Участвует во внеучебной активности")

    if family and family.income_level and "малообеспеч" in family.income_level.name.lower():
        risk_points += 2
        risks.append("Затруднительное материальное положение")
        recommendations.append("Проверить доступные меры социальной поддержки")

    if psycho and psycho.adaptation_level:
        adaptation = psycho.adaptation_level.name.lower()
        if "низ" in adaptation:
            risk_points += 2
            risks.append("Низкая адаптация к университету")
            recommendations.append("Рекомендовать консультацию психолога")
        elif "выс" in adaptation:
            strengths.append("Хороший уровень адаптации")

    if medical and medical.has_disability:
        risk_points += 1
        risks.append("Требуется учитывать медицинские ограничения")
        recommendations.append("Согласовать индивидуальное сопровождение при необходимости")

    if risk_points >= 5:
        risk_level = "high"
        support_level = "specialist"
    elif risk_points >= 3:
        risk_level = "medium"
        support_level = "curator_attention"
    elif risk_points >= 1:
        risk_level = "low"
        support_level = "observe"
    else:
        risk_level = "low"
        support_level = "none"

    short_profile = (
        f"{student.full_name}: курс {student.course}, группа {student.group.name}. "
        f"Оценка выполнена по данным социального паспорта."
    )
    strengths_text = "\n".join(strengths) if strengths else "Явные сильные стороны не выделены автоматически."
    risks_text = "\n".join(risks) if risks else "Значимые факторы риска не обнаружены."
    recommendations_text = (
        "\n".join(dict.fromkeys(recommendations))
        if recommendations
        else "Продолжать плановое сопровождение и периодический мониторинг."
    )

    return StudentAIAnalysis.objects.create(
        student=student,
        short_profile=short_profile,
        strengths=strengths_text,
        risk_factors=risks_text,
        recommendations=recommendations_text,
        risk_level=risk_level,
        support_level=support_level,
    )


def _is_family_filled(student):
    family = getattr(student, "family", None)
    if not family:
        return False
    if family.family_type_id or family.income_level_id:
        return True
    return family.members.exists()


def _is_housing_filled(student):
    housing = getattr(student, "housing", None)
    if not housing:
        return False
    return bool(housing.housing_type_id or housing.comment.strip())


def _is_psycho_filled(student):
    psycho = getattr(student, "psycho", None)
    if not psycho:
        return False
    return any([
        psycho.temperament_id,
        psycho.communication_id,
        psycho.behavior_in_group_id,
        psycho.responsibility_level_id,
        psycho.adaptation_level_id,
        psycho.description.strip(),
    ])


def _is_academic_filled(student):
    academic = getattr(student, "academic", None)
    if not academic:
        return False
    return any([
        academic.gpa is not None,
        academic.attendance,
        academic.activity.strip(),
        academic.has_unexcused_absences,
        academic.unexcused_absences_count > 0,
    ])


def _is_medical_filled(student):
    medical = getattr(student, "medical", None)
    if not medical:
        return False
    return any([
        medical.health_group_id,
        medical.has_disability,
        medical.disability_details.strip(),
        medical.chronic_diseases.strip(),
        medical.recommendations.strip(),
    ])


def _is_benefits_filled(student):
    benefits = getattr(student, "benefits", None)
    if not benefits:
        return False
    return any([
        benefits.state_grant,
        benefits.receives_scholarship,
        benefits.disability_allowance,
        benefits.breadwinner_loss_allowance,
        benefits.preferential_housing,
        benefits.free_meals,
        benefits.additional_benefits.strip(),
    ])


def _is_ai_filled(student):
    if hasattr(student, "_prefetched_objects_cache") and "ai_analyses" in student._prefetched_objects_cache:
        return bool(student.ai_analyses.all())
    return student.ai_analyses.exists()


_BLOCK_CHECKERS = {
    "family": _is_family_filled,
    "housing": _is_housing_filled,
    "psycho": _is_psycho_filled,
    "academic": _is_academic_filled,
    "medical": _is_medical_filled,
    "benefits": _is_benefits_filled,
    "ai": _is_ai_filled,
}


def get_student_completion(student):
    blocks = {key: checker(student) for key, checker in _BLOCK_CHECKERS.items()}
    filled = sum(blocks.values())
    total = len(blocks)
    percent = round(filled / total * 100) if total else 0
    return {"blocks": blocks, "filled": filled, "total": total, "percent": percent}


def get_department_completion_report():
    students = (
        Student.objects.select_related(
            "department",
            "family",
            "housing",
            "psycho",
            "academic",
            "medical",
            "benefits",
        )
        .prefetch_related("family__members", "ai_analyses")
        .order_by("department__name", "last_name")
    )

    dept_stats = defaultdict(
        lambda: {
            "department": "",
            "students_count": 0,
            "total_percent": 0,
            "blocks_filled": {key: 0 for key, _ in CARD_BLOCKS},
        }
    )

    for student in students:
        dept_id = student.department_id
        stats = dept_stats[dept_id]
        stats["department"] = student.department.name
        stats["students_count"] += 1
        completion = get_student_completion(student)
        stats["total_percent"] += completion["percent"]
        for key, is_filled in completion["blocks"].items():
            if is_filled:
                stats["blocks_filled"][key] += 1

    rows = []
    for stats in sorted(dept_stats.values(), key=lambda item: item["department"]):
        count = stats["students_count"]
        row = {
            "department": stats["department"],
            "students_count": count,
            "avg_percent": round(stats["total_percent"] / count) if count else 0,
        }
        for key, _ in CARD_BLOCKS:
            filled = stats["blocks_filled"][key]
            row[f"{key}_percent"] = round(filled / count * 100) if count else 0
        rows.append(row)

    return rows


def get_card_completion_export_rows():
    headers = ["Кафедра", "Студентов", "Средняя заполненность, %"]
    headers.extend(f"{label}, %" for _, label in CARD_BLOCKS)
    rows = get_department_completion_report()
    data = [
        [r["department"], r["students_count"], r["avg_percent"]]
        + [r[f"{key}_percent"] for key, _ in CARD_BLOCKS]
        for r in rows
    ]
    return headers, data
