from rest_framework.routers import DefaultRouter

from .views.api import CategoryViewSet, CourseViewSet, MyEnrollmentViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="api-category")
router.register("courses", CourseViewSet, basename="api-course")
router.register("me/enrollments", MyEnrollmentViewSet, basename="api-my-enrollment")

urlpatterns = router.urls
