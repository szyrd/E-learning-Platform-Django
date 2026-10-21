from django.test import TestCase
from django.urls import reverse

from main.models import Category

from .factories import PASSWORD, make_course, make_instructor, make_student


class CatalogTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.free = make_course(self.instructor, title="Free Python", price="0.00")
        self.paid = make_course(self.instructor, title="Paid Django", price="49.00")
        self.draft = make_course(self.instructor, title="Secret Draft", published=False)

    def test_home_renders(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Free Python")
        self.assertNotContains(resp, "Secret Draft")

    def test_list_search_and_filters(self):
        resp = self.client.get(reverse("course_list"), {"q": "django"})
        self.assertContains(resp, "Paid Django")
        self.assertNotContains(resp, "Free Python")
        resp = self.client.get(reverse("course_list"), {"price": "free"})
        self.assertContains(resp, "Free Python")
        self.assertNotContains(resp, "Paid Django")
        cat = Category.objects.get(name="Testing")
        resp = self.client.get(reverse("course_list"), {"category": cat.slug, "sort": "rating"})
        self.assertEqual(resp.status_code, 200)

    def test_detail_public_and_draft_hidden(self):
        self.assertEqual(self.client.get(self.free.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 404)
        self.client.login(username=self.instructor.username, password=PASSWORD)
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 200)

    def test_preview_lesson_is_watchable_without_enrollment(self):
        student = make_student()
        self.client.login(username=student.username, password=PASSWORD)
        preview = self.free.lessons.first()
        locked = self.free.lessons.last()
        self.assertEqual(self.client.get(reverse("lesson", args=[self.free.slug, preview.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("lesson", args=[self.free.slug, locked.id])).status_code, 403)

    def test_slug_is_unique(self):
        other = make_course(self.instructor, title="Free Python")
        self.assertNotEqual(other.slug, self.free.slug)
        self.assertTrue(other.slug.startswith("free-python"))
