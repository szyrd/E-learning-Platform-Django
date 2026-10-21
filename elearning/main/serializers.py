from rest_framework import serializers

from .models import Category, Course, Enrollment, Lesson, Quiz, Review, User


class UserPublicSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="display_name", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "name", "headline")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon")


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ("id", "title", "order", "duration_minutes", "is_preview", "video_url", "content")


class LessonSummarySerializer(serializers.ModelSerializer):
    """Hides content/video for users who are not enrolled."""

    class Meta:
        model = Lesson
        fields = ("id", "title", "order", "duration_minutes", "is_preview")


class QuizSummarySerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source="questions.count", read_only=True)

    class Meta:
        model = Quiz
        fields = ("id", "title", "pass_mark", "order", "question_count")


class CourseListSerializer(serializers.ModelSerializer):
    instructor = UserPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    rating = serializers.FloatField(read_only=True)
    students = serializers.IntegerField(read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Course
        fields = (
            "id", "title", "slug", "subtitle", "category", "level", "language", "price", "is_free",
            "thumbnail", "instructor", "rating", "students", "created_at", "url",
        )


class CourseDetailSerializer(CourseListSerializer):
    lessons = LessonSummarySerializer(many=True, read_only=True)
    quizzes = QuizSummarySerializer(many=True, read_only=True)
    outcomes = serializers.ListField(child=serializers.CharField(), read_only=True)
    prerequisites = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + ("description", "outcomes", "prerequisites", "lessons", "quizzes")


class ReviewSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ("id", "user", "rating", "comment", "created_at")


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    progress = serializers.IntegerField(source="progress_percent", read_only=True)

    class Meta:
        model = Enrollment
        fields = ("id", "course", "enrolled_at", "completed_at", "progress")
