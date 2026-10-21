from django.urls import path

from .views import auth, catalog, certificates, instructor, learning, student

urlpatterns = [
    # public catalog
    path("", catalog.home, name="home"),
    path("courses/", catalog.course_list, name="course_list"),
    path("courses/<slug:slug>/", catalog.course_detail, name="course_detail"),

    # accounts
    path("accounts/login/", auth.SignInView.as_view(), name="login"),
    path("accounts/register/", auth.register, name="register"),
    path("accounts/logout/", auth.sign_out, name="logout"),
    path("accounts/profile/", auth.profile, name="profile"),
    path("dashboard/", auth.dashboard, name="dashboard"),

    # student
    path("my-learning/", student.my_learning, name="my_learning"),
    path("my-learning/payments/", student.payments, name="payments"),
    path("courses/<slug:slug>/enroll/", student.enroll_course, name="enroll"),
    path("courses/<slug:slug>/checkout/", student.checkout, name="checkout"),
    path("courses/<slug:slug>/review/", student.submit_review, name="submit_review"),

    # certificates (public verification)
    path("certificates/<str:code>/", certificates.verify, name="certificate_verify"),
    path("certificates/<str:code>/pdf/", certificates.download, name="certificate_pdf"),

    # learning
    path("learn/<slug:slug>/", learning.learn, name="learn"),
    path("learn/<slug:slug>/lesson/<int:lesson_id>/", learning.lesson, name="lesson"),
    path("learn/<slug:slug>/lesson/<int:lesson_id>/complete/", learning.complete_lesson, name="complete_lesson"),
    path("learn/<slug:slug>/quiz/<int:quiz_id>/", learning.quiz, name="quiz"),
    path("learn/<slug:slug>/quiz/<int:quiz_id>/result/<int:attempt_id>/", learning.quiz_result, name="quiz_result"),

    # instructor
    path("teach/", instructor.dashboard, name="instructor_dashboard"),
    path("teach/students/", instructor.students, name="instructor_students"),
    path("teach/courses/new/", instructor.course_create, name="course_create"),
    path("teach/courses/<slug:slug>/", instructor.manage_course, name="manage_course"),
    path("teach/courses/<slug:slug>/edit/", instructor.course_edit, name="course_edit"),
    path("teach/courses/<slug:slug>/delete/", instructor.course_delete, name="course_delete"),
    path("teach/courses/<slug:slug>/publish/", instructor.course_toggle_publish, name="course_toggle_publish"),
    path("teach/courses/<slug:slug>/lessons/new/", instructor.lesson_create, name="lesson_create"),
    path("teach/lessons/<int:lesson_id>/edit/", instructor.lesson_edit, name="lesson_edit"),
    path("teach/lessons/<int:lesson_id>/delete/", instructor.lesson_delete, name="lesson_delete"),
    path("teach/lessons/<int:lesson_id>/move/<str:direction>/", instructor.lesson_move, name="lesson_move"),
    path("teach/courses/<slug:slug>/quizzes/new/", instructor.quiz_create, name="quiz_create"),
    path("teach/quizzes/<int:quiz_id>/", instructor.manage_quiz, name="manage_quiz"),
    path("teach/quizzes/<int:quiz_id>/edit/", instructor.quiz_edit, name="quiz_edit"),
    path("teach/quizzes/<int:quiz_id>/delete/", instructor.quiz_delete, name="quiz_delete"),
    path("teach/questions/<int:question_id>/edit/", instructor.question_edit, name="question_edit"),
    path("teach/questions/<int:question_id>/delete/", instructor.question_delete, name="question_delete"),
]
