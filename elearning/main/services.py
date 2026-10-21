"""Domain operations shared by HTML views, the API and the seed command."""
from __future__ import annotations

import secrets
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Course, Enrollment, Lesson, LessonCompletion, Payment, Quiz, QuizAttempt, User


class EnrollmentError(Exception):
    pass


def get_enrollment(user, course: Course) -> Enrollment | None:
    if not user.is_authenticated:
        return None
    return Enrollment.objects.filter(user=user, course=course).first()


@transaction.atomic
def enroll(user: User, course: Course, *, payment_method: str | None = None) -> Enrollment:
    """Enroll ``user`` in ``course``. Paid courses require a ``payment_method``."""
    if course.instructor_id == user.id:
        raise EnrollmentError("You cannot enroll in your own course.")
    if not course.is_published:
        raise EnrollmentError("This course is not published yet.")
    existing = Enrollment.objects.filter(user=user, course=course).first()
    if existing:
        return existing
    if not course.is_free:
        if not payment_method:
            raise EnrollmentError("Payment is required for this course.")
        Payment.objects.create(
            user=user,
            course=course,
            amount=course.price,
            method=payment_method,
            status=Payment.Status.SUCCEEDED,
            reference=f"PAY-{secrets.token_hex(6).upper()}",
        )
    return Enrollment.objects.create(user=user, course=course)


def mark_lesson_complete(enrollment: Enrollment, lesson: Lesson) -> bool:
    """Returns True when newly completed, False if it was already done."""
    if lesson.course_id != enrollment.course_id:
        raise ValueError("Lesson does not belong to the enrolled course.")
    _, created = LessonCompletion.objects.get_or_create(enrollment=enrollment, lesson=lesson)
    enrollment.refresh_completion()
    return created


def grade_quiz(enrollment: Enrollment, quiz: Quiz, answers: dict[str, str]) -> QuizAttempt:
    """Grade ``answers`` (question_id -> 'A'..'D') and persist an attempt."""
    if quiz.course_id != enrollment.course_id:
        raise ValueError("Quiz does not belong to the enrolled course.")
    questions = list(quiz.questions.all())
    total = len(questions)
    correct = sum(1 for q in questions if answers.get(str(q.id)) == q.correct_option)
    score = round(correct * 100 / total, 2) if total else 0.0
    attempt = QuizAttempt.objects.create(
        enrollment=enrollment,
        quiz=quiz,
        score=score,
        correct=correct,
        total=total,
        answers={str(q.id): answers.get(str(q.id), "") for q in questions},
    )
    enrollment.refresh_completion()
    return attempt


def course_outline(course: Course, enrollment: Enrollment | None) -> list[dict]:
    """Ordered lessons + quizzes with per-user completion flags for the learn sidebar."""
    done_lessons = enrollment.completed_lesson_ids() if enrollment else set()
    passed_quizzes = enrollment.passed_quiz_ids() if enrollment else set()
    attempted = set(enrollment.quiz_attempts.values_list("quiz_id", flat=True)) if enrollment else set()
    items: list[dict] = []
    for lesson in course.lessons.all():
        items.append({"kind": "lesson", "obj": lesson, "done": lesson.id in done_lessons, "locked": not (enrollment or lesson.is_preview)})
    for quiz in course.quizzes.all():
        items.append({"kind": "quiz", "obj": quiz, "done": quiz.id in passed_quizzes, "attempted": quiz.id in attempted, "locked": enrollment is None})
    return items


def instructor_stats(instructor: User) -> dict:
    courses = Course.objects.filter(instructor=instructor).with_stats()
    enrollments = Enrollment.objects.filter(course__instructor=instructor)
    revenue = Payment.objects.filter(course__instructor=instructor, status=Payment.Status.SUCCEEDED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    ratings = [c.avg_rating for c in courses if c.avg_rating]
    return {
        "course_count": courses.count(),
        "student_count": enrollments.values("user").distinct().count(),
        "enrollment_count": enrollments.count(),
        "completed_count": enrollments.filter(completed_at__isnull=False).count(),
        "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "revenue": revenue,
        "recent_enrollments": enrollments.select_related("user", "course")[:8],
        "now": timezone.now(),
    }
