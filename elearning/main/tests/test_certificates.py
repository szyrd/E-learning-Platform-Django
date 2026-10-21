from django.test import TestCase
from django.urls import reverse

from main.models import Certificate
from main.services import enroll, grade_quiz, mark_lesson_complete

from .factories import PASSWORD, make_course, make_instructor, make_student


class CertificateTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.student = make_student()
        self.course = make_course(self.instructor, title="Cert Course", lessons=1, quiz_questions=1)
        self.enrollment = enroll(self.student, self.course)

    def _complete(self):
        mark_lesson_complete(self.enrollment, self.course.lessons.first())
        quiz = self.course.quizzes.first()
        grade_quiz(self.enrollment, quiz, {str(q.id): q.correct_option for q in quiz.questions.all()})
        self.enrollment.refresh_from_db()

    def test_certificate_issued_on_completion_only(self):
        mark_lesson_complete(self.enrollment, self.course.lessons.first())
        self.assertFalse(Certificate.objects.exists())
        self._complete()
        cert = Certificate.objects.get(enrollment=self.enrollment)
        self.assertRegex(cert.code, r"^LH-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")
        # completing again (retaking the quiz) does not issue a second one
        quiz = self.course.quizzes.first()
        grade_quiz(self.enrollment, quiz, {str(q.id): q.correct_option for q in quiz.questions.all()})
        self.assertEqual(Certificate.objects.count(), 1)

    def test_certificate_survives_new_content(self):
        self._complete()
        from main.models import Lesson
        Lesson.objects.create(course=self.course, title="Bonus")
        self.enrollment.refresh_completion()
        self.enrollment.refresh_from_db()
        self.assertFalse(self.enrollment.is_completed)
        self.assertTrue(Certificate.objects.filter(enrollment=self.enrollment).exists())

    def test_public_verification_page(self):
        self._complete()
        cert = self.enrollment.certificate
        resp = self.client.get(reverse("certificate_verify", args=[cert.code]))  # anonymous
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Verified certificate")
        self.assertContains(resp, self.student.display_name)
        self.assertContains(resp, "Cert Course")
        self.assertContains(resp, cert.code)
        # lowercase code also works, unknown code is 404
        self.assertEqual(self.client.get(reverse("certificate_verify", args=[cert.code.lower()])).status_code, 200)
        self.assertEqual(self.client.get(reverse("certificate_verify", args=["LH-XXXX-XXXX-XXXX"])).status_code, 404)

    def test_pdf_download(self):
        self._complete()
        cert = self.enrollment.certificate
        resp = self.client.get(reverse("certificate_pdf", args=[cert.code]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertTrue(resp.content.startswith(b"%PDF"))
        self.assertGreater(len(resp.content), 2000)
        inline = self.client.get(reverse("certificate_pdf", args=[cert.code]) + "?inline=1")
        self.assertIn("inline", inline["Content-Disposition"])

    def test_entry_points_show_certificate(self):
        self._complete()
        cert = self.enrollment.certificate
        self.client.login(username=self.student.username, password=PASSWORD)
        self.assertContains(self.client.get(reverse("my_learning")), cert.get_absolute_url())
        self.assertContains(self.client.get(self.course.get_absolute_url()), cert.get_absolute_url())
        self.client.login(username=self.instructor.username, password=PASSWORD)
        self.assertContains(self.client.get(reverse("instructor_students")), cert.get_absolute_url())
