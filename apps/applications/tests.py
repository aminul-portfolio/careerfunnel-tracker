from datetime import date
from unittest.mock import patch
from urllib.parse import quote

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from .choices import (
    ApplicationSource,
    ApplicationStatus,
    FollowUpStatus,
    PipelineStage,
    RoleFit,
    WorkType,
)
from .models import JobApplication
from .services import (
    ITEM_COMPANY_RESEARCHED,
    ITEM_CONTACT_EMAIL,
    ITEM_CV_VERSION,
    ITEM_FOLLOW_UP_DATE,
    ITEM_FOLLOW_UP_STATUS,
    ITEM_JOB_DESCRIPTION,
    ITEM_JOB_URL,
    ITEM_PORTFOLIO_PROJECT,
    READINESS_LABEL_MISSING_KEY,
    READINESS_LABEL_NEEDS_IMPROVEMENT,
    READINESS_LABEL_STRONG,
    build_application_evidence_readiness,
    calculate_response_rate,
)


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

    def test_application_detail_includes_evidence_readiness_context(self):
        application = self.create_application(cv_version="DA_CV_v1")
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("evidence_readiness", response.context)
        self.assertEqual(
            response.context["evidence_readiness"],
            build_application_evidence_readiness(application),
        )

    def test_application_detail_displays_evidence_readiness(self):
        application = self.create_application(
            cv_version="DA_CV_v2",
            cover_letter_version="Tailored_CL_v2",
            job_url="https://example.com/jobs/123",
            required_skills="Python, SQL, Excel",
            job_description=(
                "Junior data analyst role focused on reporting, dashboards, "
                "and stakeholder support."
            ),
            contact_email="hiring@example.com",
            company_researched=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        readiness = build_application_evidence_readiness(application)

        self.assertContains(response, "Evidence Readiness")
        self.assertContains(response, readiness.readiness_label)
        self.assertContains(response, ITEM_CV_VERSION)
        self.assertContains(response, ITEM_PORTFOLIO_PROJECT)
        self.assertContains(response, readiness.recommended_next_improvement)
        self.assertContains(response, "CareerFunnel Tracker does not send email.")
        self.assertContains(response, "Manual follow-up workflow")

    def test_application_detail_displays_complete_evidence_readiness_state(self):
        application = self.create_application(
            cv_version="DA_CV_v2",
            cover_letter_version="Tailored_CL_v2",
            job_url="https://example.com/jobs/123",
            required_skills="Python, SQL, Excel, Tableau",
            job_description=(
                "Junior data analyst role focused on reporting, dashboards, "
                "and stakeholder support."
            ),
            contact_email="hiring@example.com",
            company_researched=True,
            portfolio_project_included=True,
            follow_up_date=date(2026, 5, 20),
            follow_up_status=FollowUpStatus.DUE,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, READINESS_LABEL_STRONG)
        self.assertContains(response, "All evidence items complete")

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
        application = self.create_application(follow_up_status=FollowUpStatus.DUE)
        self.client.login(username="aminul", password="StrongPass12345")
        mark_followup_url = reverse(
            "applications:application_mark_followup_sent",
            kwargs={"pk": application.pk},
        )

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Mark Follow-up Sent")
        self.assertContains(response, f'action="{mark_followup_url}"')
        self.assertContains(
            response,
            "Use this only after you have sent the email manually outside CareerFunnel Tracker.",
        )

    def test_application_detail_displays_completed_state_for_sent_followup(self):
        last_contacted_date = date(2026, 5, 12)
        application = self.create_application(
            follow_up_status=FollowUpStatus.SENT,
            last_contacted_date=last_contacted_date,
        )
        self.client.login(username="aminul", password="StrongPass12345")
        mark_followup_url = reverse(
            "applications:application_mark_followup_sent",
            kwargs={"pk": application.pk},
        )

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Follow-up already marked as sent.")
        self.assertContains(
            response,
            f"Last contacted: {date_format(last_contacted_date, 'DATE_FORMAT')}",
        )
        self.assertNotContains(response, f'action="{mark_followup_url}"')
        self.assertContains(response, "CareerFunnel Tracker does not send email.")

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


class ApplicationEvidenceReadinessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _base_application_kwargs(self):
        return {
            "user": self.user,
            "company_name": "Example Ltd",
            "job_title": "Junior Data Analyst",
            "date_applied": date(2026, 5, 9),
        }

    def _well_prepared_kwargs(self):
        return {
            **self._base_application_kwargs(),
            "cv_version": "DA_CV_v2",
            "cover_letter_version": "Tailored_CL_v2",
            "job_url": "https://example.com/jobs/123",
            "required_skills": "Python, SQL, Excel, Tableau",
            "job_description": (
                "Junior data analyst role focused on reporting, dashboards, "
                "and stakeholder support."
            ),
            "contact_email": "hiring@example.com",
            "company_researched": True,
            "portfolio_project_included": True,
            "follow_up_date": date(2026, 5, 20),
            "follow_up_status": FollowUpStatus.DUE,
        }

    def test_well_prepared_application_receives_strong_evidence_label(self):
        application = JobApplication.objects.create(**self._well_prepared_kwargs())

        readiness = build_application_evidence_readiness(application)

        self.assertEqual(readiness.readiness_label, READINESS_LABEL_STRONG)
        self.assertEqual(readiness.missing_items, ())
        self.assertEqual(
            readiness.recommended_next_improvement,
            "Evidence is complete; keep records updated as the application progresses.",
        )

    def test_sparse_application_receives_missing_key_evidence_label(self):
        application = JobApplication.objects.create(**self._base_application_kwargs())

        readiness = build_application_evidence_readiness(application)

        self.assertEqual(readiness.readiness_label, READINESS_LABEL_MISSING_KEY)

    def test_missing_items_are_detected_correctly(self):
        kwargs = self._well_prepared_kwargs()
        kwargs.update({"cv_version": "", "contact_email": "", "follow_up_date": None})
        application = JobApplication.objects.create(**kwargs)

        readiness = build_application_evidence_readiness(application)

        self.assertIn(ITEM_CV_VERSION, readiness.missing_items)
        self.assertIn(ITEM_CONTACT_EMAIL, readiness.missing_items)
        self.assertIn(ITEM_FOLLOW_UP_DATE, readiness.missing_items)
        self.assertNotIn(ITEM_JOB_URL, readiness.missing_items)

    def test_ready_items_are_detected_correctly(self):
        kwargs = self._well_prepared_kwargs()
        kwargs.update({"cv_version": "", "follow_up_status": FollowUpStatus.NOT_SET})
        application = JobApplication.objects.create(**kwargs)

        readiness = build_application_evidence_readiness(application)

        self.assertIn(ITEM_JOB_URL, readiness.ready_items)
        self.assertIn(ITEM_JOB_DESCRIPTION, readiness.ready_items)
        self.assertIn(ITEM_COMPANY_RESEARCHED, readiness.ready_items)
        self.assertNotIn(ITEM_CV_VERSION, readiness.ready_items)
        self.assertNotIn(ITEM_FOLLOW_UP_STATUS, readiness.ready_items)

    def test_recommended_next_improvement_is_deterministic_and_practical(self):
        kwargs = self._well_prepared_kwargs()
        kwargs["cv_version"] = ""
        application = JobApplication.objects.create(**kwargs)
        readiness = build_application_evidence_readiness(application)
        self.assertEqual(
            readiness.recommended_next_improvement,
            "Save the CV version used for this application.",
        )

        application.cv_version = "DA_CV_v2"
        application.cover_letter_version = ""
        application.save(update_fields=["cv_version", "cover_letter_version"])
        readiness = build_application_evidence_readiness(application)
        self.assertEqual(
            readiness.recommended_next_improvement,
            "Save the cover letter version used for this application.",
        )

    def test_partially_prepared_application_receives_needs_improvement_label(self):
        application = JobApplication.objects.create(
            **self._base_application_kwargs(),
            cv_version="DA_CV_v2",
            cover_letter_version="Tailored_CL_v2",
            job_url="https://example.com/jobs/123",
            required_skills="Python, SQL, Excel",
            job_description=(
                "Junior data analyst role focused on reporting, dashboards, "
                "and stakeholder support."
            ),
            contact_email="hiring@example.com",
            company_researched=True,
        )

        readiness = build_application_evidence_readiness(application)

        self.assertEqual(readiness.readiness_label, READINESS_LABEL_NEEDS_IMPROVEMENT)
        self.assertIn(ITEM_PORTFOLIO_PROJECT, readiness.missing_items)
        self.assertIn(ITEM_FOLLOW_UP_DATE, readiness.missing_items)
        self.assertIn(ITEM_FOLLOW_UP_STATUS, readiness.missing_items)
        self.assertEqual(
            readiness.recommended_next_improvement,
            "Note whether a portfolio project was included or referenced.",
        )


class ApplicationCreatePrefillTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="prefill", password="StrongPass12345")
        self.client.login(username="prefill", password="StrongPass12345")
        self.create_url = reverse("applications:application_create")

    def _get_create(self, query_string=""):
        url = self.create_url if not query_string else f"{self.create_url}?{query_string}"
        return self.client.get(url)

    def test_application_create_get_without_params_renders_normally(self):
        response = self._get_create()
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("company_name"), None)
        self.assertEqual(form.initial.get("pipeline_stage"), None)

    def test_company_name_get_param_appears_in_form_initial(self):
        response = self._get_create("company_name=FinSight")
        self.assertEqual(response.context["form"].initial.get("company_name"), "FinSight")

    def test_job_title_get_param_appears_in_form_initial(self):
        response = self._get_create("job_title=Junior+Data+Analyst")
        self.assertEqual(
            response.context["form"].initial.get("job_title"),
            "Junior Data Analyst",
        )

    def test_location_get_param_appears_in_form_initial(self):
        response = self._get_create("location=Hybrid+London")
        self.assertEqual(response.context["form"].initial.get("location"), "Hybrid London")

    def test_fit_score_at_least_60_maps_to_role_fit_strong(self):
        response = self._get_create("fit_score=60")
        self.assertEqual(response.context["form"].initial.get("role_fit"), RoleFit.STRONG)

    def test_fit_score_40_to_59_maps_to_role_fit_medium(self):
        response = self._get_create("fit_score=45")
        self.assertEqual(response.context["form"].initial.get("role_fit"), RoleFit.MEDIUM)

    def test_fit_score_below_40_maps_to_role_fit_weak(self):
        response = self._get_create("fit_score=25")
        self.assertEqual(response.context["form"].initial.get("role_fit"), RoleFit.WEAK)

    def test_invalid_fit_score_does_not_raise_server_error(self):
        response = self._get_create("fit_score=not-a-number")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["form"].initial.get("role_fit"))

    def test_pipeline_stage_fit_checked_when_prefill_params_exist(self):
        response = self._get_create("company_name=FinSight")
        self.assertEqual(
            response.context["form"].initial.get("pipeline_stage"),
            PipelineStage.FIT_CHECKED,
        )

    def test_post_create_application_flow_still_works(self):
        response = self.client.post(
            self.create_url,
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


class JobPostingAnalyzerPrefillBridgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="analyzer", password="StrongPass12345")
        self.client.login(username="analyzer", password="StrongPass12345")
        self.analyzer_url = reverse("ai_agents:job_posting_analyzer")

    def test_save_as_application_not_shown_before_analysis(self):
        response = self.client.get(self.analyzer_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Save as Application")

    def test_save_as_application_shown_after_analysis(self):
        response = self.client.post(
            self.analyzer_url,
            {
                "company_name": "FinSight",
                "job_title": "Junior Finance Data Analyst",
                "location": "Hybrid London",
                "job_posting": "Python SQL Excel reporting dashboards junior 0-2 years",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save as Application")
        self.assertContains(response, "pre-filled Add Application form")
        self.assertContains(response, "Nothing is saved until you review and submit")

    def test_save_as_application_link_contains_encoded_get_params(self):
        job_title = "Junior Finance Data Analyst"
        location = "Hybrid London"
        response = self.client.post(
            self.analyzer_url,
            {
                "company_name": "FinSight",
                "job_title": job_title,
                "location": location,
                "job_posting": "Python SQL Excel reporting dashboards junior 0-2 years",
            },
        )
        self.assertContains(response, "company_name=FinSight")
        self.assertContains(response, f"job_title={quote(job_title)}")
        self.assertContains(response, f"location={quote(location)}")
        self.assertContains(response, "fit_score=")

    def test_save_as_application_link_encodes_special_characters_in_company_name(self):
        company_name = "Smith & Jones Ltd"
        response = self.client.post(
            self.analyzer_url,
            {
                "company_name": company_name,
                "job_title": "Junior Data Analyst",
                "location": "London",
                "job_posting": "Python SQL Excel reporting junior dashboard",
            },
        )
        encoded_company = quote(company_name)
        self.assertContains(response, f"company_name={encoded_company}")