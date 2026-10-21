import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from .factories import PASSWORD, make_student


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=3)
class LoginLockoutTests(TestCase):
    def setUp(self):
        self.user = make_student("locky")
        from axes.models import AccessAttempt
        AccessAttempt.objects.all().delete()

    def _login(self, password):
        return self.client.post(reverse("login"), {"username": "locky", "password": password}, REMOTE_ADDR="10.0.0.9")

    def test_lockout_after_failures_and_custom_page(self):
        for _ in range(2):
            self.assertEqual(self._login("wrong-pass").status_code, 200)
        resp = self._login("wrong-pass")  # third failure trips the limit
        self.assertEqual(resp.status_code, 429)  # django-axes >= 8 answers 429 Too Many Requests
        self.assertContains(resp, "Too many sign-in attempts", status_code=429)
        # even the right password is refused while locked
        self.assertEqual(self._login(PASSWORD).status_code, 429)

    def test_other_ip_is_not_locked(self):
        for _ in range(3):
            self._login("wrong-pass")
        resp = self.client.post(reverse("login"), {"username": "locky", "password": PASSWORD}, REMOTE_ADDR="10.0.0.10")
        self.assertEqual(resp.status_code, 302)

    def test_success_resets_counter(self):
        self._login("wrong-pass")
        self._login("wrong-pass")
        self.assertEqual(self._login(PASSWORD).status_code, 302)
        self.client.logout()
        self._login("wrong-pass")
        self._login("wrong-pass")
        self.assertEqual(self._login(PASSWORD).status_code, 302)


class ContentSecurityPolicyTests(TestCase):
    def test_csp_header_on_pages(self):
        resp = self.client.get(reverse("home"))
        csp = resp["Content-Security-Policy"]
        self.assertIn("script-src 'self' 'nonce-", csp)
        self.assertIn("https://cdn.jsdelivr.net", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("frame-src https://www.youtube-nocookie.com", csp)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", csp)

    def test_local_script_carries_nonce(self):
        resp = self.client.get(reverse("home"))
        nonce = re.search(r"'nonce-([^']+)'", resp["Content-Security-Policy"]).group(1)
        self.assertContains(resp, f'js/app.js" nonce="{nonce}"')

    def test_api_is_excluded(self):
        resp = self.client.get("/api/courses/")
        self.assertNotIn("Content-Security-Policy", resp)

    def test_templates_have_no_inline_handlers_or_scripts(self):
        offenders = []
        for path in (Path(settings.BASE_DIR) / "templates").rglob("*.html"):
            text = path.read_text()
            if re.search(r"\son(click|change|submit|load|input)=", text) or re.search(r"<script(?![^>]*\ssrc=)", text) or "javascript:" in text:
                offenders.append(str(path.relative_to(settings.BASE_DIR)))
        self.assertEqual(offenders, [])
