from django.test import TestCase
from django.urls import reverse

from main.models import User

from .factories import PASSWORD, make_instructor, make_student


class RegistrationTests(TestCase):
    def test_register_student_logs_in_and_redirects(self):
        resp = self.client.post(reverse("register"), {
            "first_name": "Ada", "last_name": "Lovelace", "username": "ada", "email": "ada@example.com",
            "role": "student", "password1": "Correct-Horse-9", "password2": "Correct-Horse-9",
        }, follow=True)
        self.assertRedirects(resp, reverse("my_learning"))
        user = User.objects.get(username="ada")
        self.assertTrue(user.is_student)

    def test_register_instructor_redirects_to_teach(self):
        resp = self.client.post(reverse("register"), {
            "first_name": "Grace", "last_name": "Hopper", "username": "grace", "email": "grace@example.com",
            "role": "instructor", "password1": "Correct-Horse-9", "password2": "Correct-Horse-9",
        }, follow=True)
        self.assertRedirects(resp, reverse("instructor_dashboard"))

    def test_duplicate_email_rejected(self):
        make_student("sam")
        resp = self.client.post(reverse("register"), {
            "first_name": "A", "last_name": "B", "username": "other", "email": "sam@example.com",
            "role": "student", "password1": "Correct-Horse-9", "password2": "Correct-Horse-9",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already exists")

    def test_weak_password_rejected(self):
        resp = self.client.post(reverse("register"), {
            "first_name": "A", "last_name": "B", "username": "weak", "email": "weak@example.com",
            "role": "student", "password1": "12345678", "password2": "12345678",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak").exists())


class LoginTests(TestCase):
    def test_login_with_email(self):
        make_student("sam")
        resp = self.client.post(reverse("login"), {"username": "sam@example.com", "password": PASSWORD})
        self.assertRedirects(resp, reverse("dashboard"), fetch_redirect_response=False)

    def test_login_required_redirects_to_login_page(self):
        resp = self.client.get(reverse("my_learning"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_logout_requires_post(self):
        make_student("sam")
        self.client.login(username="sam", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)

    def test_role_pages_are_protected(self):
        student = make_student()
        instructor = make_instructor()
        self.client.login(username=student.username, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("instructor_dashboard")).status_code, 403)
        self.client.login(username=instructor.username, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("my_learning")).status_code, 403)
