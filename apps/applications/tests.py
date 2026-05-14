from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .choices import (
    ApplicationSource,
    ApplicationStatus,
    FollowUpStatus,
    RoleFit,
    WorkType,
)
from .models import JobApplication
from .services import calculate_response_rate


class ApplicationChoiceTests(TestCase):
    def test_reed_and_bookmarklet_sources_exist(self):
        self.assertEqual(ApplicationSource.REED, "reed")
        self.assertEqual(ApplicationSource.BOOKMARKLET, "bookmarklet")
        self.assertIn(("reed", "Reed.co.uk"), ApplicationSource.choices)
        self.assertIn(("bookmarklet", "Bookmarklet"), ApplicationSource.choices)


class JobApplicationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_days_to_response_returns_correct_value(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Test Company",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            response_date=date(2026, 5, 4),
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        self.assertEqual(application.days_to_response, 3)

    def test_days_to_response_returns_none_without_response_date(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Test Company",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            status=ApplicationStatus.SUBMITTED,
        )
        self.assertIsNone(application.days_to_response)


class JobApplicationViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Example Ltd",
            "job_title": "Junior Data Analyst",
            "date_applied": date(2026, 5, 9),
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_application_list_requires_login(self):
        response = self.client.get(reverse("applications:application_list"))
        self.assertEqual(response.status_code, 302)

    def test_application_list_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("applications:application_list"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_create_application(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("applications:application_create"),
            {
                "company_name": "Example Ltd",
                "job_title": "Junior Data Analyst",
                "job_url": "https://example.com/job",
                "location": "London",
                "work_type": WorkType.HYBRID,
                "salary_range": "£30,000 - £35,000",
                "source": ApplicationSource.LINKEDIN,
                "role_fit": RoleFit.STRONG,
                "date_applied": "2026-05-09",
                "status": ApplicationStatus.SUBMITTED,
                "response_date": "",
                "cv_version": "DA_CV_v1",
                "cover_letter_version": "Tailored_CL_v1",
                "contact_name": "",
                "contact_email": "",
                "notes": "Good fit.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(JobApplication.objects.filter(company_name="Example Ltd").exists())

    def test_application_detail_includes_followup_email_draft_context(self):
        application = self.create_application(contact_email="hiring@example.com")
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("followup_email_draft", response.context)
        self.assertEqual(
            response.context["followup_email_draft"].recipient_email,
            "hiring@example.com",
        )

    def test_application_detail_displays_followup_email_draft_content(self):
        application = self.create_application(
            contact_name="Taylor Morgan",
            contact_email="hiring@example.com",
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Follow-up Email Draft")
        self.assertContains(response, "hiring@example.com")
        self.assertContains(
            response,
            "Follow-up on Junior Data Analyst application at Example Ltd",
        )
        self.assertContains(response, "Dear Taylor Morgan,")
        self.assertContains(response, "I applied for the Junior Data Analyst")
        self.assertContains(response, "Manual draft only.")

    def test_application_detail_makes_draft_manual_only(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Manual Only")
        self.assertContains(response, "CareerFunnel Tracker does not send email.")
        self.assertContains(response, "Use this manual workflow")
        self.assertContains(response, "manual copy only")
        self.assertNotContains(response, "Send Email")

    def test_application_detail_displays_manual_followup_workflow_steps(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Manual follow-up workflow")
        self.assertContains(response, "Review the draft below.")
        self.assertContains(
            response,
            "Copy and send it manually outside CareerFunnel Tracker.",
        )
        self.assertContains(response, "Click Mark Follow-up Sent after sending.")

    def test_application_detail_displays_mark_followup_sent_button(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Mark Follow-up Sent")
        self.assertContains(
            response,
            "Use this only after you have sent the email manually outside CareerFunnel Tracker.",
        )

    def test_mark_followup_sent_requires_login(self):
        application = self.create_application()

        response = self.client.post(
            reverse(
                "applications:application_mark_followup_sent",
                kwargs={"pk": application.pk},
            ),
        )

        self.assertEqual(response.status_code, 302)

    def test_mark_followup_sent_rejects_get(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse(
                "applications:application_mark_followup_sent",
                kwargs={"pk": application.pk},
            ),
        )

        self.assertEqual(response.status_code, 405)

    @patch("django.core.mail.EmailMessage.send")
    @patch("django.core.mail.send_mail")
    def test_mark_followup_sent_post_updates_application_without_email(
        self,
        send_mail,
        email_message_send,
    ):
        application = self.create_application(
            follow_up_status=FollowUpStatus.DUE,
            last_contacted_date=None,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.post(
            reverse(
                "applications:application_mark_followup_sent",
                kwargs={"pk": application.pk},
            ),
            follow=True,
        )
        application.refresh_from_db()

        self.assertRedirects(response, application.get_absolute_url())
        self.assertEqual(application.follow_up_status, FollowUpStatus.SENT)
        self.assertEqual(application.last_contacted_date, timezone.localdate())
        self.assertContains(response, "Follow-up marked as sent.")
        send_mail.assert_not_called()
        email_message_send.assert_not_called()
        self.assertEqual(mail.outbox, [])


class ApplicationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_response_rate_is_zero_without_applications(self):
        self.assertEqual(calculate_response_rate(self.user), 0.0)

    def test_response_rate_calculates_correctly(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Company A",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            status=ApplicationStatus.SUBMITTED,
        )
        JobApplication.objects.create(
            user=self.user,
            company_name="Company B",
            job_title="BI Analyst",
            date_applied=date(2026, 5, 2),
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        self.assertEqual(calculate_response_rate(self.user), 50.0)