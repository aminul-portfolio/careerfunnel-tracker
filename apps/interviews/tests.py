from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.applications.models import JobApplication
from apps.applications.services import build_application_evidence_readiness
from apps.job_intelligence.services import build_smart_review
from apps.recruiter_emails.models import RecruiterEmail

from .models import InterviewPrep


class InterviewPrepTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Test Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            cv_version="Finance_DA_CV_v1",
            cover_letter_version="Tailored_CL_v1",
            portfolio_project_included=True,
            required_skills="Python SQL finance reporting dashboards",
            job_description=(
                "Junior finance data analyst role focused on reporting, "
                "dashboards, SQL, and stakeholder evidence."
            ),
        )

    def test_readiness_score(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
            profile_answer_prepared=True,
            company_answer_prepared=True,
        )
        self.assertGreater(interview.readiness_score, 0)

    def test_interview_list_requires_login(self):
        response = self.client.get(reverse("interviews:interview_list"))
        self.assertEqual(response.status_code, 302)

    def test_interview_detail_requires_login(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
        )

        response = self.client.get(
            reverse("interviews:interview_detail", kwargs={"pk": interview.pk}),
        )

        self.assertEqual(response.status_code, 302)

    def test_interview_create_works(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("interviews:interview_create"),
            {
                "application": self.application.pk,
                "interview_date": "2026-05-10",
                "stage": "screening",
                "outcome": "scheduled",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InterviewPrep.objects.count(), 1)

    def test_interview_detail_loads_for_logged_in_user(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("interviews:interview_detail", kwargs={"pk": interview.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.application.company_name)
        self.assertContains(response, self.application.job_title)

    def test_interview_detail_includes_evidence_readiness_context(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("interviews:interview_detail", kwargs={"pk": interview.pk}),
        )

        self.assertIn("evidence_readiness", response.context)
        self.assertEqual(
            response.context["evidence_readiness"],
            build_application_evidence_readiness(self.application),
        )

    def test_interview_detail_includes_smart_review_context(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("interviews:interview_detail", kwargs={"pk": interview.pk}),
        )

        self.assertIn("smart_review", response.context)
        self.assertEqual(response.context["smart_review"], build_smart_review(self.application))

    def test_interview_detail_displays_evidence_workspace(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
        )
        readiness = build_application_evidence_readiness(self.application)
        smart_review = build_smart_review(self.application)
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("interviews:interview_detail", kwargs={"pk": interview.pk}),
        )

        self.assertContains(response, "Interview Evidence Workspace")
        self.assertContains(response, readiness.readiness_label)
        self.assertContains(response, smart_review.recommended_cv)
        self.assertContains(response, smart_review.recommended_projects[0])
        self.assertContains(response, "Questions for employer")


class InterviewPrepHandoffPolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="handoff", password="StrongPass12345")
        self.other_user = User.objects.create_user(username="other", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Handoff Co",
            job_title="BI Analyst",
            date_applied=date(2026, 5, 1),
        )
        self.other_application = JobApplication.objects.create(
            user=self.other_user,
            company_name="Other Co",
            job_title="Analyst",
            date_applied=date(2026, 5, 1),
        )
        self.client.login(username="handoff", password="StrongPass12345")

    def test_interview_create_prefills_application_from_query_param(self):
        response = self.client.get(
            reverse("interviews:interview_create")
            + f"?application={self.application.pk}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial.get("application"),
            self.application.pk,
        )
        self.assertContains(response, "Handoff Co")
        self.assertContains(response, "You still need to save interview prep manually")
        self.assertEqual(InterviewPrep.objects.count(), 0)

    def test_interview_create_ignores_other_users_application_query_param(self):
        response = self.client.get(
            reverse("interviews:interview_create")
            + f"?application={self.other_application.pk}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("application", response.context["form"].initial)
        self.assertNotContains(response, "Other Co")
        self.assertIsNone(response.context["prefill_application"])

    def test_interview_form_shows_manual_only_workflow_copy(self):
        response = self.client.get(reverse("interviews:interview_create"))

        self.assertContains(response, "saved only when you manually submit this form")
        self.assertContains(response, "No email, calendar, Gmail, OAuth")

    def test_interview_detail_links_to_application_detail(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
        )
        application_url = reverse(
            "applications:application_detail",
            kwargs={"pk": self.application.pk},
        )

        response = self.client.get(
            reverse("interviews:interview_detail", kwargs={"pk": interview.pk}),
        )

        self.assertContains(response, application_url)
        self.assertContains(response, "Application Detail")

    def test_interview_detail_links_to_application_agent_pack(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
        )
        pack_url = reverse(
            "ai_agents:application_agent_pack",
            kwargs={"pk": self.application.pk},
        )

        response = self.client.get(
            reverse("interviews:interview_detail", kwargs={"pk": interview.pk}),
        )

        self.assertContains(response, pack_url)
        self.assertContains(response, "Application AI Pack")

    def test_interview_detail_does_not_auto_create_prep(self):
        count_before = InterviewPrep.objects.count()
        response = self.client.get(
            reverse("interviews:interview_create")
            + f"?application={self.application.pk}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(InterviewPrep.objects.count(), count_before)

    def test_interview_list_shows_manual_workflow_copy(self):
        response = self.client.get(reverse("interviews:interview_list"))

        self.assertContains(
            response,
            "Create interview prep manually when an application reaches screening",
        )
        self.assertContains(response, "does not create interview prep automatically")

    def test_interview_detail_shows_recruiter_email_section_link_when_emails_exist(
        self,
    ):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
        )
        RecruiterEmail.objects.create(
            application=self.application,
            subject="Interview invite",
            body="We would like to invite you to interview.",
            date_received=timezone.now(),
        )
        recruiter_section_url = (
            reverse("applications:application_detail", kwargs={"pk": self.application.pk})
            + "#recruiter-emails"
        )

        response = self.client.get(
            reverse("interviews:interview_detail", kwargs={"pk": interview.pk}),
        )

        self.assertContains(response, recruiter_section_url)
        self.assertContains(response, "Recruiter emails on application")
