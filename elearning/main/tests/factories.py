"""Tiny helpers to build test data without an extra dependency."""
from decimal import Decimal

from django.contrib.auth import get_user_model

from main.models import Category, Course, Lesson, Question, Quiz

User = get_user_model()
PASSWORD = "Str0ng-Pass-123"


def make_user(username="user", role="student", **extra):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=PASSWORD, role=role, **extra)
    return user


def make_instructor(username="teacher"):
    return make_user(username, role="instructor", first_name="Tea", last_name="Cher")


def make_student(username="student"):
    return make_user(username, role="student", first_name="Stu", last_name="Dent")


def make_course(instructor, title="Test Course", price="0.00", published=True, lessons=2, quiz_questions=2, category=None):
    category = category or Category.objects.get_or_create(name="Testing")[0]
    course = Course.objects.create(
        title=title, description="A course", instructor=instructor, price=Decimal(price), is_published=published, category=category,
        what_you_learn="Thing one\nThing two",
    )
    for i in range(1, lessons + 1):
        Lesson.objects.create(course=course, title=f"Lesson {i}", video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", duration_minutes=5, is_preview=(i == 1))
    if quiz_questions:
        quiz = Quiz.objects.create(course=course, title="Quiz 1", pass_mark=50)
        for i in range(1, quiz_questions + 1):
            Question.objects.create(quiz=quiz, text=f"Q{i}?", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="B", order=i)
    return course
