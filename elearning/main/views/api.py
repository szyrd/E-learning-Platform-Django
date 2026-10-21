from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Category, Course, Enrollment, Review
from ..serializers import (
    CategorySerializer, CourseDetailSerializer, CourseListSerializer, EnrollmentSerializer,
    LessonSerializer, LessonSummarySerializer, ReviewSerializer,
)
from ..services import EnrollmentError, enroll, get_enrollment


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """Public course catalog. Enrolled users can also read lesson content and enroll."""

    queryset = Course.objects.published().with_stats().select_related("instructor", "category")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "slug"
    filterset_fields = {"level": ["exact"], "category__slug": ["exact"], "price": ["lte", "gte"]}
    search_fields = ["title", "subtitle", "description"]
    ordering_fields = ["created_at", "price", "student_count", "avg_rating"]
    ordering = ["-student_count"]

    def get_serializer_class(self):
        return CourseDetailSerializer if self.action == "retrieve" else CourseListSerializer

    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny])
    def lessons(self, request, slug=None):
        course = self.get_object()
        enrolled = bool(get_enrollment(request.user, course)) or (request.user.is_authenticated and course.instructor_id == request.user.id)
        serializer = (LessonSerializer if enrolled else LessonSummarySerializer)(course.lessons.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny])
    def reviews(self, request, slug=None):
        course = self.get_object()
        return Response(ReviewSerializer(course.reviews.select_related("user"), many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def enroll(self, request, slug=None):
        course = self.get_object()
        if not request.user.is_student:
            return Response({"detail": "Only student accounts can enroll."}, status=status.HTTP_403_FORBIDDEN)
        try:
            enrollment = enroll(request.user, course, payment_method=request.data.get("payment_method"))
        except EnrollmentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)


class MyEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(user=self.request.user).select_related("course", "course__instructor", "course__category")
