from django.test import TestCase
from django.urls import reverse

from main.services import enroll

from .factories import PASSWORD, make_course, make_instructor, make_student


class QueryCountTests(TestCase):
    """Guard against N+1 regressions: query counts must not grow with the number of rows."""

    def _count(self, client, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        return len(ctx)

    def test_my_learning_is_constant_in_enrollments(self):
        instructor = make_instructor()
        student = make_student()
        self.client.login(username=student.username, password=PASSWORD)
        enroll(student, make_course(instructor, title="C1"))
        baseline = self._count(self.client, reverse("my_learning"))
        for i in range(2, 8):
            enroll(student, make_course(instructor, title=f"C{i}"))
        self.assertEqual(self._count(self.client, reverse("my_learning")), baseline)

    def test_instructor_students_is_constant_in_enrollments(self):
        instructor = make_instructor()
        course = make_course(instructor)
        enroll(make_student("s1"), course)
        self.client.login(username=instructor.username, password=PASSWORD)
        baseline = self._count(self.client, reverse("instructor_students"))
        for i in range(2, 8):
            enroll(make_student(f"s{i}"), course)
        self.assertEqual(self._count(self.client, reverse("instructor_students")), baseline)

    def test_catalog_is_constant_in_courses(self):
        instructor = make_instructor()
        make_course(instructor, title="C1")
        baseline = self._count(self.client, reverse("course_list"))
        for i in range(2, 8):
            make_course(instructor, title=f"C{i}")
        self.assertEqual(self._count(self.client, reverse("course_list")), baseline)
