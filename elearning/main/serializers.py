from rest_framework import serializers

from main.models import Course, Lesson, Review


class CourseSerializer(serializers.Serializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'price', 'category', 'created_at', 'instructor']



class LessonSerializer(serializers.Serializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'content', 'video_url']


class ReviewSerializer(serializers.Serializer):
    class Meta:
        model = Review
        fields = ['id', 'course', 'user', 'rating', 'comment', 'created_at']