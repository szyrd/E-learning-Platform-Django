from django.test import TestCase
from django.urls import reverse

from main.models import Course, Lesson, Question, Quiz

from .factories import PASSWORD, make_course, make_instructor, make_student


class InstructorTests(TestCase):
    def setUp(self):
        self.me = make_instructor("me")
        self.other = make_instructor("other")
        self.course = make_course(self.me, title="Mine")
        self.theirs = make_course(self.other, title="Theirs")
        self.client.login(username="me", password=PASSWORD)

    def test_dashboard_and_students_pages(self):
        self.assertContains(self.client.get(reverse("instructor_dashboard")), "Mine")
        self.assertEqual(self.client.get(reverse("instructor_students")).status_code, 200)

    def test_create_course(self):
        resp = self.client.post(reverse("course_create"), {
            "title": "Brand New", "subtitle": "", "level": "beginner", "language": "English", "price": "0",
            "description": "desc", "what_you_learn": "", "requirements": "", "is_published": "on",
        })
        course = Course.objects.get(title="Brand New")
        self.assertRedirects(resp, reverse("manage_course", args=[course.slug]), fetch_redirect_response=False)
        self.assertEqual(course.instructor, self.me)

    def test_cannot_manage_other_instructors_course(self):
        self.assertEqual(self.client.get(reverse("manage_course", args=[self.theirs.slug])).status_code, 403)
        self.assertEqual(self.client.get(reverse("course_edit", args=[self.theirs.slug])).status_code, 403)
        lesson = self.theirs.lessons.first()
        self.assertEqual(self.client.post(reverse("lesson_delete", args=[lesson.id])).status_code, 403)
        self.assertTrue(Lesson.objects.filter(pk=lesson.pk).exists())
        quiz = self.theirs.quizzes.first()
        self.assertEqual(self.client.get(reverse("manage_quiz", args=[quiz.id])).status_code, 403)

    def test_delete_requires_post(self):
        lesson = self.course.lessons.first()
        self.assertEqual(self.client.get(reverse("lesson_delete", args=[lesson.id])).status_code, 405)
        self.assertEqual(self.client.get(reverse("course_delete", args=[self.course.slug])).status_code, 405)

    def test_lesson_crud_and_reorder(self):
        resp = self.client.post(reverse("lesson_create", args=[self.course.slug]), {
            "title": "Lesson 3", "video_url": "https://youtu.be/abcdefghijk", "duration_minutes": 7, "content": "",
        })
        self.assertEqual(resp.status_code, 302)
        lessons = list(self.course.lessons.all())
        self.assertEqual([l.title for l in lessons], ["Lesson 1", "Lesson 2", "Lesson 3"])
        self.client.post(reverse("lesson_move", args=[lessons[2].id, "up"]))
        self.assertEqual([l.title for l in self.course.lessons.all()], ["Lesson 1", "Lesson 3", "Lesson 2"])
        self.client.post(reverse("lesson_delete", args=[lessons[0].id]))
        self.assertEqual(self.course.lessons.count(), 2)

    def test_quiz_builder(self):
        resp = self.client.post(reverse("quiz_create", args=[self.course.slug]), {"title": "Final", "description": "", "pass_mark": 80})
        quiz = Quiz.objects.get(title="Final")
        self.assertRedirects(resp, reverse("manage_quiz", args=[quiz.id]), fetch_redirect_response=False)
        self.client.post(reverse("manage_quiz", args=[quiz.id]), {
            "text": "2+2?", "option_a": "3", "option_b": "4", "option_c": "5", "option_d": "6", "correct_option": "B", "explanation": "",
        })
        q = Question.objects.get(text="2+2?")
        self.assertEqual(q.order, 1)
        self.client.post(reverse("question_delete", args=[q.id]))
        self.assertEqual(quiz.questions.count(), 0)

    def test_students_cannot_access_builder(self):
        student = make_student()
        self.client.login(username=student.username, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("course_create")).status_code, 403)

    def test_unpublish_hides_from_catalog(self):
        self.client.post(reverse("course_toggle_publish", args=[self.course.slug]))
        self.course.refresh_from_db()
        self.assertFalse(self.course.is_published)
        self.assertNotContains(self.client.get(reverse("course_list")), "Mine")
