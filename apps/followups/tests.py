from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import FollowUpStatus
from apps.applications.models import JobApplication

from .services import build_followup_email_draft, get_due_followups


class FollowupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Test Co",
            "job_title": "Data Analyst",
            "date_applied": date(2026, 5, 1),
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_due_followup_detected(self):
        self.create_application(
            follow_up_date=date(2026, 5, 2),
        )
        self.assertEqual(get_due_followups(self.user).count(), 1)

    def test_followup_page_requires_login(self):
        response = self.client.get(reverse("followups:followup_list"))
        self.assertEqual(response.status_code, 302)

    def test_follow_up_detail_shows_manual_tracking_state_message(self):
        self.create_application(
            follow_up_date=date(2026, 5, 2),
            follow_up_status=FollowUpStatus.DUE,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("followups:followup_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            (
                "Follow-up status and dates are manual tracking fields. They are not "
                "automatically updated from your email or the employer's system."
            ),
        )
        self.assertContains(
            response,
            (
                "Mark Follow-up Sent only after you have manually sent the follow-up "
                "email. This updates your tracking record only - CareerFunnel does "
                "not send emails."
            ),
        )
        self.assertNotContains(response, "CareerFunnel sends emails")
        self.assertNotContains(response, "automatically sends")
        self.assertNotContains(response, "auto-send")
        self.assertNotContains(response, "auto sync")
        self.assertNotContains(response, "auto-sync")
        self.assertNotContains(response, "Gmail")
        self.assertNotContains(response, "OAuth")
        self.assertNotContains(response, "Calendar")
        self.assertNotContains(response, "Apply Now")
        self.assertNotContains(response, "Submit Application")

    def test_follow_up_status_label_is_neutral(self):
        self.create_application(
            follow_up_date=date(2026, 5, 2),
            follow_up_status=FollowUpStatus.DUE,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("followups:followup_list"))

        self.assertContains(response, "Follow-up Status")
        self.assertContains(response, "Mark Follow-up Sent")
        self.assertNotContains(response, "Send Email")
        self.assertNotContains(response, "Apply Now")
        self.assertNotContains(response, "Submit Application")

    def test_email_draft_uses_contact_name_when_available(self):
        application = self.create_application(contact_name="Taylor Morgan")

        draft = build_followup_email_draft(application)

        self.assertTrue(draft.body.startswith("Dear Taylor Morgan,"))
        self.assertIn("Test Co", draft.body)
        self.assertIn("Data Analyst", draft.body)
        self.assertIn("May 1, 2026", draft.body)

    def test_email_draft_uses_generic_greeting_without_contact_name(self):
        application = self.create_application(contact_name="")

        draft = build_followup_email_draft(application)

        self.assertTrue(draft.body.startswith("Hello,"))

    def test_email_draft_subject_includes_application_context(self):
        application = self.create_application()

        draft = build_followup_email_draft(application)

        self.assertIn("Data Analyst", draft.subject)
        self.assertIn("Test Co", draft.subject)

    def test_email_draft_uses_contact_email_when_available(self):
        application = self.create_application(contact_email="taylor@example.com")

        draft = build_followup_email_draft(application)

        self.assertEqual(draft.recipient_email, "taylor@example.com")

    @patch("django.core.mail.send_mail")
    def test_email_draft_does_not_send_email_or_use_mail_api(self, send_mail):
        application = self.create_application(contact_email="taylor@example.com")

        draft = build_followup_email_draft(application)

        self.assertTrue(draft.copy_ready)
        send_mail.assert_not_called()
        self.assertEqual(mail.outbox, [])
