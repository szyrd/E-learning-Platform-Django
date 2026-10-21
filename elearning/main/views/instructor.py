from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..decorators import instructor_required
from ..forms import CourseForm, LessonForm, QuestionForm, QuizForm
from ..models import Course, Enrollment, Lesson, Question, Quiz
from ..services import instructor_stats


def _own_course(request, slug) -> Course:
    course = get_object_or_404(Course, slug=slug)
    if course.instructor_id != request.user.id and not request.user.is_staff:
        raise PermissionDenied("You can only manage your own courses.")
    return course


def _own_lesson(request, lesson_id) -> Lesson:
    lesson = get_object_or_404(Lesson.objects.select_related("course"), pk=lesson_id)
    if lesson.course.instructor_id != request.user.id and not request.user.is_staff:
        raise PermissionDenied
    return lesson


def _own_quiz(request, quiz_id) -> Quiz:
    quiz = get_object_or_404(Quiz.objects.select_related("course"), pk=quiz_id)
    if quiz.course.instructor_id != request.user.id and not request.user.is_staff:
        raise PermissionDenied
    return quiz


# --------------------------------------------------------------------------- dashboard
@instructor_required
def dashboard(request):
    courses = Course.objects.filter(instructor=request.user).with_stats().select_related("category")
    return render(request, "instructor/dashboard.html", {"courses": courses, "stats": instructor_stats(request.user)})


@instructor_required
def students(request):
    enrollments = (
        Enrollment.objects.filter(course__instructor=request.user)
        .select_related("user", "course")
        .order_by("-enrolled_at")
    )
    course_slug = request.GET.get("course")
    if course_slug:
        enrollments = enrollments.filter(course__slug=course_slug)
    rows = [{"e": e, "progress": e.progress_percent()} for e in enrollments[:200]]
    return render(request, "instructor/students.html", {
        "rows": rows,
        "courses": Course.objects.filter(instructor=request.user),
        "course_slug": course_slug,
    })


# --------------------------------------------------------------------------- courses
@instructor_required
def course_create(request):
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.instructor = request.user
        course.save()
        messages.success(request, "Course created. Now add some lessons!")
        return redirect("manage_course", slug=course.slug)
    return render(request, "instructor/course_form.html", {"form": form, "course": None})


@instructor_required
def course_edit(request, slug):
    course = _own_course(request, slug)
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Course updated.")
        return redirect("manage_course", slug=course.slug)
    return render(request, "instructor/course_form.html", {"form": form, "course": course})


@instructor_required
def manage_course(request, slug):
    course = _own_course(request, slug)
    stats = Enrollment.objects.filter(course=course).aggregate(
        students=Count("id"), completed=Count("id", filter=Q(completed_at__isnull=False))
    )
    rating = course.reviews.aggregate(v=Avg("rating"))["v"]
    return render(request, "instructor/manage_course.html", {
        "course": course,
        "lessons": course.lessons.all(),
        "quizzes": course.quizzes.prefetch_related("questions"),
        "stats": stats,
        "rating": round(rating, 1) if rating else None,
        "reviews": course.reviews.select_related("user")[:5],
    })


@instructor_required
@require_POST
def course_delete(request, slug):
    course = _own_course(request, slug)
    title = course.title
    course.delete()
    messages.success(request, f"“{title}” was deleted.")
    return redirect("instructor_dashboard")


@instructor_required
@require_POST
def course_toggle_publish(request, slug):
    course = _own_course(request, slug)
    course.is_published = not course.is_published
    course.save(update_fields=["is_published"])
    messages.success(request, "Course published." if course.is_published else "Course unpublished.")
    return redirect("manage_course", slug=slug)


# --------------------------------------------------------------------------- lessons
@instructor_required
def lesson_create(request, slug):
    course = _own_course(request, slug)
    form = LessonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lesson = form.save(commit=False)
        lesson.course = course
        lesson.save()
        messages.success(request, f"Lesson “{lesson.title}” added.")
        if "save_add_another" in request.POST:
            return redirect("lesson_create", slug=slug)
        return redirect("manage_course", slug=slug)
    return render(request, "instructor/lesson_form.html", {"form": form, "course": course, "lesson": None})


@instructor_required
def lesson_edit(request, lesson_id):
    lesson = _own_lesson(request, lesson_id)
    form = LessonForm(request.POST or None, instance=lesson)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Lesson updated.")
        return redirect("manage_course", slug=lesson.course.slug)
    return render(request, "instructor/lesson_form.html", {"form": form, "course": lesson.course, "lesson": lesson})


@instructor_required
@require_POST
def lesson_delete(request, lesson_id):
    lesson = _own_lesson(request, lesson_id)
    slug = lesson.course.slug
    title = lesson.title
    lesson.delete()
    messages.success(request, f"Lesson “{title}” deleted.")
    return redirect("manage_course", slug=slug)


@instructor_required
@require_POST
def lesson_move(request, lesson_id, direction):
    lesson = _own_lesson(request, lesson_id)
    siblings = list(lesson.course.lessons.all())
    idx = siblings.index(lesson)
    swap = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap < len(siblings):
        other = siblings[swap]
        lesson.order, other.order = other.order, lesson.order
        if lesson.order == other.order:  # legacy rows with equal order
            lesson.order, other.order = swap + 1, idx + 1
        Lesson.objects.bulk_update([lesson, other], ["order"])
    return redirect("manage_course", slug=lesson.course.slug)


# --------------------------------------------------------------------------- quizzes
@instructor_required
def quiz_create(request, slug):
    course = _own_course(request, slug)
    form = QuizForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        quiz = form.save(commit=False)
        quiz.course = course
        quiz.save()
        messages.success(request, "Quiz created. Add your first question below.")
        return redirect("manage_quiz", quiz_id=quiz.id)
    return render(request, "instructor/quiz_form.html", {"form": form, "course": course, "quiz": None})


@instructor_required
def quiz_edit(request, quiz_id):
    quiz = _own_quiz(request, quiz_id)
    form = QuizForm(request.POST or None, instance=quiz)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Quiz updated.")
        return redirect("manage_quiz", quiz_id=quiz.id)
    return render(request, "instructor/quiz_form.html", {"form": form, "course": quiz.course, "quiz": quiz})


@instructor_required
@require_POST
def quiz_delete(request, quiz_id):
    quiz = _own_quiz(request, quiz_id)
    slug = quiz.course.slug
    quiz.delete()
    messages.success(request, "Quiz deleted.")
    return redirect("manage_course", slug=slug)


@instructor_required
def manage_quiz(request, quiz_id):
    """Quiz builder: lists questions and adds a new one inline."""
    quiz = _own_quiz(request, quiz_id)
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        question = form.save(commit=False)
        question.quiz = quiz
        question.order = quiz.questions.count() + 1
        question.save()
        messages.success(request, "Question added.")
        return redirect("manage_quiz", quiz_id=quiz.id)
    attempts = quiz.attempts.select_related("enrollment__user")[:10]
    return render(request, "instructor/manage_quiz.html", {
        "quiz": quiz, "course": quiz.course, "questions": quiz.questions.all(), "form": form, "attempts": attempts,
    })


@instructor_required
def question_edit(request, question_id):
    question = get_object_or_404(Question.objects.select_related("quiz__course"), pk=question_id)
    if question.quiz.course.instructor_id != request.user.id and not request.user.is_staff:
        raise PermissionDenied
    form = QuestionForm(request.POST or None, instance=question)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Question updated.")
        return redirect("manage_quiz", quiz_id=question.quiz_id)
    return render(request, "instructor/question_form.html", {"form": form, "quiz": question.quiz, "course": question.quiz.course, "question": question})


@instructor_required
@require_POST
def question_delete(request, question_id):
    question = get_object_or_404(Question.objects.select_related("quiz__course"), pk=question_id)
    if question.quiz.course.instructor_id != request.user.id and not request.user.is_staff:
        raise PermissionDenied
    quiz_id = question.quiz_id
    question.delete()
    messages.success(request, "Question removed.")
    return redirect("manage_quiz", quiz_id=quiz_id)
