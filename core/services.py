from .models import Student, StudentAIAnalysis


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
