from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..decorators import student_required
from ..models import Course, Lesson, Quiz, QuizAttempt
from ..services import course_outline, get_enrollment, grade_quiz, mark_lesson_complete


def _course_access(request, slug):
    course = get_object_or_404(Course.objects.select_related("instructor"), slug=slug)
    enrollment = get_enrollment(request.user, course)
    is_owner = course.instructor_id == request.user.id
    if not enrollment and not is_owner and not request.user.is_staff:
        raise PermissionDenied("Enroll in this course to access its content.")
    return course, enrollment, is_owner


def _learn_context(request, course, enrollment, is_owner, outline=None, **extra):
    outline = outline if outline is not None else course_outline(course, enrollment)
    ctx = {
        "course": course,
        "enrollment": enrollment,
        "is_owner": is_owner,
        "outline": outline,
        "progress": enrollment.progress_percent() if enrollment else 0,
        "done_count": sum(1 for i in outline if i["done"]),
        "total_count": len(outline),
    }
    ctx.update(extra)
    return ctx


def _next_item(outline, current_kind, current_id):
    seen = False
    for item in outline:
        if seen:
            return item
        if item["kind"] == current_kind and item["obj"].id == current_id:
            seen = True
    return None


def learn(request, slug):
    if not request.user.is_authenticated:
        return redirect(f"/accounts/login/?next={request.path}")
    course, enrollment, is_owner = _course_access(request, slug)
    outline = course_outline(course, enrollment)
    # Resume at the first unfinished item.
    for item in outline:
        if not item["done"]:
            if item["kind"] == "lesson":
                return redirect("lesson", slug=slug, lesson_id=item["obj"].id)
            return redirect("quiz", slug=slug, quiz_id=item["obj"].id)
    first = outline[0] if outline else None
    if first and first["kind"] == "lesson":
        return redirect("lesson", slug=slug, lesson_id=first["obj"].id)
    if first:
        return redirect("quiz", slug=slug, quiz_id=first["obj"].id)
    messages.info(request, "This course has no content yet.")
    return redirect(course)


def lesson(request, slug, lesson_id):
    if not request.user.is_authenticated:
        return redirect(f"/accounts/login/?next={request.path}")
    course = get_object_or_404(Course, slug=slug)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    enrollment = get_enrollment(request.user, course)
    is_owner = course.instructor_id == request.user.id
    if not enrollment and not is_owner and not lesson.is_preview and not request.user.is_staff:
        raise PermissionDenied("Enroll in this course to watch this lesson.")
    outline = course_outline(course, enrollment)
    return render(request, "learning/lesson.html", _learn_context(
        request, course, enrollment, is_owner, outline=outline,
        lesson=lesson, current_kind="lesson", current_id=lesson.id,
        is_done=bool(enrollment) and lesson.id in enrollment.completed_lesson_ids(),
        next_item=_next_item(outline, "lesson", lesson.id),
    ))


@student_required
@require_POST
def complete_lesson(request, slug, lesson_id):
    course, enrollment, _ = _course_access(request, slug)
    if not enrollment:
        raise PermissionDenied
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    mark_lesson_complete(enrollment, lesson)
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"ok": True, "progress": enrollment.progress_percent(), "completed": enrollment.is_completed})
    messages.success(request, f"Marked “{lesson.title}” as complete.")
    nxt = _next_item(course_outline(course, enrollment), "lesson", lesson.id)
    if nxt and nxt["kind"] == "lesson":
        return redirect("lesson", slug=slug, lesson_id=nxt["obj"].id)
    if nxt:
        return redirect("quiz", slug=slug, quiz_id=nxt["obj"].id)
    return redirect("lesson", slug=slug, lesson_id=lesson.id)


def quiz(request, slug, quiz_id):
    if not request.user.is_authenticated:
        return redirect(f"/accounts/login/?next={request.path}")
    course, enrollment, is_owner = _course_access(request, slug)
    quiz = get_object_or_404(Quiz.objects.prefetch_related("questions"), pk=quiz_id, course=course)
    questions = list(quiz.questions.all())
    attempts = QuizAttempt.objects.filter(enrollment=enrollment, quiz=quiz) if enrollment else QuizAttempt.objects.none()
    best = max((a.score for a in attempts), default=None)

    if request.method == "POST":
        if not enrollment:
            raise PermissionDenied("Only enrolled students can submit quizzes.")
        answers = {str(q.id): request.POST.get(f"q{q.id}", "") for q in questions}
        missing = [q for q in questions if not answers[str(q.id)]]
        if missing:
            messages.error(request, f"Please answer all questions ({len(missing)} left).")
            return render(request, "learning/quiz.html", _learn_context(
                request, course, enrollment, is_owner, quiz=quiz, questions=questions, answers=answers, attempts=attempts, best=best, current_kind="quiz", current_id=quiz.id,
            ))
        attempt = grade_quiz(enrollment, quiz, answers)
        return redirect("quiz_result", slug=slug, quiz_id=quiz.id, attempt_id=attempt.id)

    return render(request, "learning/quiz.html", _learn_context(
        request, course, enrollment, is_owner, quiz=quiz, questions=questions, answers={}, attempts=attempts[:5], best=best, current_kind="quiz", current_id=quiz.id,
    ))


def quiz_result(request, slug, quiz_id, attempt_id):
    if not request.user.is_authenticated:
        return redirect(f"/accounts/login/?next={request.path}")
    course, enrollment, is_owner = _course_access(request, slug)
    quiz = get_object_or_404(Quiz, pk=quiz_id, course=course)
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, quiz=quiz)
    if attempt.enrollment_id != (enrollment.id if enrollment else None) and not is_owner and not request.user.is_staff:
        raise PermissionDenied
    review_rows = []
    for q in quiz.questions.all():
        chosen = attempt.answers.get(str(q.id), "")
        review_rows.append({"q": q, "chosen": chosen, "chosen_text": dict(q.options).get(chosen, "—"), "correct": chosen == q.correct_option})
    outline = course_outline(course, enrollment)
    return render(request, "learning/quiz_result.html", _learn_context(
        request, course, enrollment, is_owner, outline=outline,
        quiz=quiz, attempt=attempt, rows=review_rows, next_item=_next_item(outline, "quiz", quiz.id), current_kind="quiz", current_id=quiz.id,
    ))
