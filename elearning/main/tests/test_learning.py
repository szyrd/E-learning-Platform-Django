from django.test import TestCase
from django.urls import reverse

from main.models import Enrollment, LessonCompletion, Payment, QuizAttempt, Review
from main.services import EnrollmentError, enroll

from .factories import PASSWORD, make_course, make_instructor, make_student


class EnrollmentTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.student = make_student()
        self.free = make_course(self.instructor, title="Free", price="0.00")
        self.paid = make_course(self.instructor, title="Paid", price="30.00")
        self.client.login(username=self.student.username, password=PASSWORD)

    def test_enroll_free_course(self):
        resp = self.client.post(reverse("enroll", args=[self.free.slug]))
        self.assertRedirects(resp, reverse("learn", args=[self.free.slug]), fetch_redirect_response=False)
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.free).exists())
        # second time is a no-op, not an error
        self.client.post(reverse("enroll", args=[self.free.slug]))
        self.assertEqual(Enrollment.objects.filter(user=self.student, course=self.free).count(), 1)

    def test_enroll_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("enroll", args=[self.free.slug])).status_code, 405)

    def test_paid_course_goes_through_checkout(self):
        resp = self.client.post(reverse("enroll", args=[self.paid.slug]))
        self.assertRedirects(resp, reverse("checkout", args=[self.paid.slug]), fetch_redirect_response=False)
        self.assertFalse(Enrollment.objects.filter(course=self.paid).exists())
        resp = self.client.post(reverse("checkout", args=[self.paid.slug]), {
            "method": "card", "cardholder": "Stu Dent", "card_number": "4242 4242 4242 4242", "expiry": "12/30", "cvc": "123",
        })
        self.assertRedirects(resp, reverse("learn", args=[self.paid.slug]), fetch_redirect_response=False)
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.paid).exists())
        payment = Payment.objects.get(user=self.student)
        self.assertEqual(str(payment.amount), "30.00")

    def test_checkout_rejects_bad_card(self):
        resp = self.client.post(reverse("checkout", args=[self.paid.slug]), {"method": "card", "card_number": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Enrollment.objects.filter(course=self.paid).exists())

    def test_instructor_cannot_enroll_in_own_course(self):
        with self.assertRaises(EnrollmentError):
            enroll(self.instructor, self.free)

    def test_locked_content_requires_enrollment(self):
        self.assertEqual(self.client.get(reverse("learn", args=[self.free.slug])).status_code, 403)
        quiz = self.free.quizzes.first()
        self.assertEqual(self.client.get(reverse("quiz", args=[self.free.slug, quiz.id])).status_code, 403)


class ProgressTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.student = make_student()
        self.course = make_course(self.instructor, lessons=2, quiz_questions=2)
        self.enrollment = enroll(self.student, self.course)
        self.client.login(username=self.student.username, password=PASSWORD)

    def test_mark_lesson_complete_and_progress(self):
        lesson = self.course.lessons.first()
        resp = self.client.post(reverse("complete_lesson", args=[self.course.slug, lesson.id]), HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["progress"], 33)  # 1 of 3 items
        self.assertEqual(LessonCompletion.objects.count(), 1)
        # idempotent
        self.client.post(reverse("complete_lesson", args=[self.course.slug, lesson.id]))
        self.assertEqual(LessonCompletion.objects.count(), 1)

    def test_quiz_grading_pass_and_fail(self):
        quiz = self.course.quizzes.first()
        q1, q2 = quiz.questions.all()
        resp = self.client.post(reverse("quiz", args=[self.course.slug, quiz.id]), {f"q{q1.id}": "B", f"q{q2.id}": "A"})
        attempt = QuizAttempt.objects.get()
        self.assertRedirects(resp, reverse("quiz_result", args=[self.course.slug, quiz.id, attempt.id]), fetch_redirect_response=False)
        self.assertEqual(attempt.score, 50.0)
        self.assertTrue(attempt.passed)  # pass mark 50
        result = self.client.get(reverse("quiz_result", args=[self.course.slug, quiz.id, attempt.id]))
        self.assertContains(result, "you passed")

    def test_quiz_requires_all_answers(self):
        quiz = self.course.quizzes.first()
        q1, _ = quiz.questions.all()
        resp = self.client.post(reverse("quiz", args=[self.course.slug, quiz.id]), {f"q{q1.id}": "B"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(QuizAttempt.objects.count(), 0)

    def test_course_completion_flag(self):
        for lesson in self.course.lessons.all():
            self.client.post(reverse("complete_lesson", args=[self.course.slug, lesson.id]))
        quiz = self.course.quizzes.first()
        self.client.post(reverse("quiz", args=[self.course.slug, quiz.id]), {f"q{q.id}": "B" for q in quiz.questions.all()})
        self.enrollment.refresh_from_db()
        self.assertTrue(self.enrollment.is_completed)
        self.assertEqual(self.enrollment.progress_percent(), 100)

    def test_learn_resumes_at_first_unfinished_item(self):
        first, second = self.course.lessons.all()
        self.client.post(reverse("complete_lesson", args=[self.course.slug, first.id]))
        resp = self.client.get(reverse("learn", args=[self.course.slug]))
        self.assertRedirects(resp, reverse("lesson", args=[self.course.slug, second.id]), fetch_redirect_response=False)

    def test_review_requires_enrollment_and_is_unique(self):
        other = make_course(self.instructor, title="Other")
        resp = self.client.post(reverse("submit_review", args=[other.slug]), {"rating": 5, "comment": "x"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)
        self.client.post(reverse("submit_review", args=[self.course.slug]), {"rating": 4, "comment": "Nice"})
        self.client.post(reverse("submit_review", args=[self.course.slug]), {"rating": 5, "comment": "Even nicer"})
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().rating, 5)

    def test_my_learning_page(self):
        resp = self.client.get(reverse("my_learning"))
        self.assertContains(resp, self.course.title)
