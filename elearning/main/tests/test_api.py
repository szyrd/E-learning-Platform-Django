from django.test import TestCase
from django.urls import reverse

from main.services import enroll

from .factories import PASSWORD, make_course, make_instructor, make_student


class ApiTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.student = make_student()
        self.course = make_course(self.instructor, title="API Course", price="0.00")

    def test_course_list_is_public_and_serialised(self):
        resp = self.client.get("/api/courses/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 1)
        item = data["results"][0]
        self.assertEqual(item["title"], "API Course")
        self.assertEqual(item["instructor"]["username"], "teacher")
        self.assertIn("is_free", item)

    def test_course_detail_and_lessons_hidden_until_enrolled(self):
        detail = self.client.get(f"/api/courses/{self.course.slug}/").json()
        self.assertEqual(len(detail["lessons"]), 2)
        self.assertNotIn("video_url", detail["lessons"][0])
        lessons = self.client.get(f"/api/courses/{self.course.slug}/lessons/").json()
        self.assertNotIn("video_url", lessons[0])
        enroll(self.student, self.course)
        self.client.login(username=self.student.username, password=PASSWORD)
        lessons = self.client.get(f"/api/courses/{self.course.slug}/lessons/").json()
        self.assertIn("video_url", lessons[0])

    def test_reviews_endpoint(self):
        self.assertEqual(self.client.get(f"/api/courses/{self.course.slug}/reviews/").json(), [])

    def test_jwt_flow_and_enroll(self):
        token = self.client.post(reverse("token_obtain_pair"), {"username": "student", "password": PASSWORD}).json()
        self.assertIn("access", token)
        auth = {"HTTP_AUTHORIZATION": f"Bearer {token['access']}"}
        resp = self.client.post(f"/api/courses/{self.course.slug}/enroll/", **auth)
        self.assertEqual(resp.status_code, 201)
        mine = self.client.get("/api/me/enrollments/", **auth).json()
        self.assertEqual(mine["count"], 1)
        self.assertEqual(mine["results"][0]["course"]["slug"], self.course.slug)

    def test_instructor_cannot_enroll_via_api(self):
        self.client.login(username="teacher", password=PASSWORD)
        resp = self.client.post(f"/api/courses/{self.course.slug}/enroll/")
        self.assertEqual(resp.status_code, 403)

    def test_search_filter(self):
        make_course(self.instructor, title="Other Thing")
        resp = self.client.get("/api/courses/?search=api").json()
        self.assertEqual(resp["count"], 1)
