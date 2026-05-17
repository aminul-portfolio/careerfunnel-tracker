from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.models import JobApplication
from apps.applications.services import build_application_evidence_readiness
from apps.job_intelligence.services import build_smart_review

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
