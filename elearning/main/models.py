from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    headline = models.CharField(max_length=120, blank=True, help_text="Short title shown on your profile, e.g. 'Senior Data Scientist'.")
    bio = models.TextField(blank=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_instructor(self) -> bool:
        return self.role == self.Role.INSTRUCTOR

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.username

    @property
    def initials(self) -> str:
        name = self.display_name.strip()
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper()


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    icon = models.CharField(max_length=60, default="bi-journal-bookmark", help_text="Bootstrap Icons class, e.g. 'bi-cpu'.")
    color = models.CharField(max_length=7, default="#0056d2", help_text="Hex colour used for placeholder covers.")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return f"{reverse('course_list')}?category={self.slug}"


class CourseQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def with_stats(self):
        return self.annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews", distinct=True),
            student_count=Count("enrollments", distinct=True),
            lesson_count=Count("lessons", distinct=True),
        )


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    subtitle = models.CharField(max_length=255, blank=True, help_text="One-line pitch shown on cards.")
    description = models.TextField(help_text="Full description shown on the course page.")
    what_you_learn = models.TextField(blank=True, help_text="One learning outcome per line.")
    requirements = models.TextField(blank=True, help_text="One prerequisite per line.")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses")
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    language = models.CharField(max_length=40, default="English")
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0"))])
    thumbnail = models.ImageField(upload_to="courses/", blank=True, null=True)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses_taught")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CourseQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "course"
            slug = base
            counter = 2
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("course_detail", kwargs={"slug": self.slug})

    # -- derived data -------------------------------------------------------
    @property
    def is_free(self) -> bool:
        return self.price is None or self.price <= 0

    @property
    def outcomes(self) -> list[str]:
        return [line.strip() for line in self.what_you_learn.splitlines() if line.strip()]

    @property
    def prerequisites(self) -> list[str]:
        return [line.strip() for line in self.requirements.splitlines() if line.strip()]

    @property
    def total_minutes(self) -> int:
        return sum(self.lessons.values_list("duration_minutes", flat=True))

    @property
    def rating(self) -> float | None:
        value = getattr(self, "avg_rating", None)
        if value is None:
            value = self.reviews.aggregate(v=Avg("rating"))["v"]
        return round(value, 1) if value else None

    @property
    def students(self) -> int:
        value = getattr(self, "student_count", None)
        return value if value is not None else self.enrollments.count()

    @property
    def cover_color(self) -> str:
        return self.category.color if self.category else "#0056d2"

    def content_item_count(self) -> int:
        return self.lessons.count() + self.quizzes.count()


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, help_text="Lesson notes / reading material.")
    video_url = models.URLField(blank=True, help_text="YouTube, Vimeo or a direct .mp4 link.")
    duration_minutes = models.PositiveIntegerField(default=10)
    order = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False, help_text="Previews can be watched without enrolling.")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.course.title} · {self.title}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.order:
            last = self.course.lessons.aggregate(m=models.Max("order"))["m"] or 0
            self.order = last + 1
        super().save(*args, **kwargs)


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pass_mark = models.PositiveIntegerField(default=70, validators=[MaxValueValidator(100)], help_text="Percentage needed to pass.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name_plural = "quizzes"

    def __str__(self) -> str:
        return f"{self.course.title} · {self.title}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.order:
            last = self.course.quizzes.aggregate(m=models.Max("order"))["m"] or 0
            self.order = last + 1
        super().save(*args, **kwargs)


class Question(models.Model):
    class Option(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=Option.choices)
    explanation = models.TextField(blank=True, help_text="Shown after the attempt is graded.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.text[:80]

    @property
    def options(self) -> list[tuple[str, str]]:
        return [("A", self.option_a), ("B", self.option_b), ("C", self.option_c), ("D", self.option_d)]

    @property
    def correct_text(self) -> str:
        return dict(self.options)[self.correct_option]


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------
class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "course")]
        ordering = ["-enrolled_at"]

    def __str__(self) -> str:
        return f"{self.user} → {self.course}"

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    @property
    def status(self) -> str:
        return "Completed" if self.is_completed else "In progress"

    # progress ---------------------------------------------------------------
    def completed_lesson_ids(self) -> set[int]:
        return set(self.lesson_completions.values_list("lesson_id", flat=True))

    def passed_quiz_ids(self) -> set[int]:
        return set(
            self.quiz_attempts.filter(score__gte=models.F("quiz__pass_mark")).values_list("quiz_id", flat=True)
        )

    def progress_percent(self) -> int:
        total = self.course.lessons.count() + self.course.quizzes.count()
        if total == 0:
            return 0
        done = len(self.completed_lesson_ids()) + len(self.passed_quiz_ids())
        return min(100, round(done * 100 / total))

    def refresh_completion(self) -> None:
        """Mark the enrollment complete when everything is done (and un-mark if not)."""
        total = self.course.lessons.count() + self.course.quizzes.count()
        done = total > 0 and self.progress_percent() >= 100
        if done and not self.completed_at:
            self.completed_at = timezone.now()
            self.save(update_fields=["completed_at"])
        elif not done and self.completed_at:
            self.completed_at = None
            self.save(update_fields=["completed_at"])


class LessonCompletion(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="lesson_completions")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="completions")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("enrollment", "lesson")]

    def __str__(self) -> str:
        return f"{self.enrollment.user} completed {self.lesson.title}"


class QuizAttempt(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.FloatField(help_text="Percentage 0-100")
    correct = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=dict, blank=True, help_text="question_id -> selected option")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"{self.enrollment.user} · {self.quiz.title} · {self.score:.0f}%"

    @property
    def passed(self) -> bool:
        return self.score >= self.quiz.pass_mark


class Review(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("course", "user")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} rated {self.course} {self.rating}/5"


class Payment(models.Model):
    class Method(models.TextChoices):
        CARD = "card", "Credit / debit card"
        PAYPAL = "paypal", "PayPal"

    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCEEDED)
    reference = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} · {self.user} · {self.amount}"
