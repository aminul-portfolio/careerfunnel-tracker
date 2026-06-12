from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.models import JobApplication


class AccountsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aminul",
            email="aminul@example.com",
            password="StrongPass12345",
            first_name="Aminul",
            last_name="Islam",
        )

    def test_register_page_loads(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to CareerFunnel")

    def test_user_can_register(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_login_with_valid_credentials_works(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "aminul", "password": "StrongPass12345"},
        )
        self.assertRedirects(response, reverse("dashboard:overview"))

    def test_login_with_invalid_credentials_shows_error(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "aminul", "password": "WrongPassword123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")

    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("accounts:login"))
        self.assertRedirects(response, reverse("dashboard:overview"))

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_settings_requires_login(self):
        response = self.client.get(reverse("accounts:settings"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_authenticated_user_can_view_profile(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aminul Islam")
        self.assertContains(response, "aminul@example.com")
        self.assertContains(response, "Manual career intelligence workspace member")

    def test_authenticated_user_can_view_settings(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("accounts:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workspace preferences")
        self.assertContains(response, "Change password")

    def test_settings_can_update_allowed_user_fields(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("accounts:settings"),
            {
                "first_name": "Aminul",
                "last_name": "Islam",
                "email": "updated@example.com",
            },
        )
        self.assertRedirects(response, reverse("accounts:settings"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "updated@example.com")

    def test_logout_works(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_topbar_shows_authenticated_display_name(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Aminul Islam")
        self.assertContains(response, "account-pill__avatar")
        self.assertContains(response, reverse("accounts:profile"))
        self.assertContains(response, reverse("accounts:settings"))

    def test_anonymous_user_sees_sign_in_option(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, "Sign in")

    def test_profile_shows_workspace_summary_from_saved_records(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Analyst",
            date_applied=date(2026, 5, 1),
        )
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "Saved applications")
        self.assertContains(response, ">1<", html=False)

    def test_account_pages_avoid_oauth_and_auto_apply_claims(self):
        self.client.login(username="aminul", password="StrongPass12345")
        for url_name in ("accounts:profile", "accounts:settings", "accounts:login"):
            response = self.client.get(reverse(url_name))
            content = response.content.decode().lower()
            self.assertNotIn("oauth", content)
            self.assertNotIn("google login", content)
            self.assertNotIn("live saas users", content)
            self.assertNotIn("customers", content)

    def test_dashboard_still_renders_for_authenticated_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
