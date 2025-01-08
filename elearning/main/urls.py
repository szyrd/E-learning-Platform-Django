from django.urls import path
from . import views
from .views import instructor_dashboard, student_dashboard, submit_quiz, play_lesson, submit_review, CourseListView, \
    LessonListView, ReviewListView

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('instructor/', views.instructor_dashboard, name='instructor_dashboard'),
    path('add-course/', views.create_course, name='create_course'),  # Add this line
    path('logout/', views.logout_view, name='logout'),
    # instructor course
    path('instructor/create_course/', views.create_course, name='create_course'),
    path('instructor/my_courses/', views.my_courses, name='my_courses'),
    # Enrollment
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('student/enrollments/', views.student_enrollments, name='student_enrollments'),
    path('instructor/enrollments/', views.instructor_enrollments, name='instructor_enrollments'),
    path('process_payment/', views.process_payment, name='process_payment'),

    path('course/<int:course_id>/', views.course_page, name='course_page'),
    path('course/<int:course_id>/add_lesson/', views.add_lesson, name='add_lesson'),
    path('course/<int:course_id>/add_quiz/', views.add_quiz, name='add_quiz'),
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('quiz/<int:quiz_id>/add_questions/', views.add_quiz_questions, name='add_quiz_questions'),
    path("quiz/<int:quiz_id>/start/", views.start_quiz, name="quiz_start"),

    path('progression/', views.my_progression, name='my_progression'),
    # Lessons
    path('lesson/edit/<int:lesson_id>/', views.edit_lesson, name='edit_lesson'),
    path('lesson/delete/<int:lesson_id>/', views.delete_lesson, name='delete_lesson'),
    # Quizzes
    path('quiz/edit/<int:quiz_id>/', views.edit_quiz, name='edit_quiz'),
    path('quiz/delete/<int:quiz_id>/', views.delete_quiz, name='delete_quiz'),
    path('quiz/<int:quiz_id>/submit/', submit_quiz, name='submit_quiz'),
    path('lesson/<int:lesson_id>/play/', play_lesson, name='play_lesson'),
    path('course/<int:course_id>/submit_review/', submit_review, name='submit_review'),

    # DRF
    path('api/courses/', CourseListView.as_view(), name='api-courses'),
    path('api/courses/<int:course_id>/lessons/', LessonListView.as_view(), name='api-lessons'),
    path('api/reviews/', ReviewListView.as_view(), name='api-reviews'),
]
