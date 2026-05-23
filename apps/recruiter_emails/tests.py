import json
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import ApplicationStatus
from apps.applications.models import JobApplication
from apps.recruiter_emails.choices import EmailType, ImportSource, ReplyStatus
from apps.recruiter_emails.forms import RecruiterEmailImportForm
from apps.recruiter_emails.models import RecruiterEmail
from apps.recruiter_emails.services import (
    classify_recruiter_email,
    create_recruiter_email_from_form_data,
    generate_reply_draft,
    requires_reply_for_email_type,
    serialise_matched_signals,
    suggest_action_due_at,
    suggest_status_update,
)


class ClassifyRecruiterEmailTests(TestCase):
    def test_rejection_classification(self):
        result = classify_recruiter_email(
            subject="Application update",
            body="Unfortunately we will not be taking your application further.",
        )
        self.assertEqual(result.email_type, EmailType.REJECTION)
        self.assertIn("unfortunately", result.matched_signals)

    def test_acknowledgement_classification(self):
        result = classify_recruiter_email(
            subject="Application received",
            body="Thank you for applying. We have received your application.",
        )
        self.assertEqual(result.email_type, EmailType.ACKNOWLEDGEMENT)
        self.assertIn("thank you for applying", result.matched_signals)

    def test_interest_classification(self):
        result = classify_recruiter_email(
            subject="Your profile",
            body="We are impressed with your profile and would like to discuss the role.",
        )
        self.assertEqual(result.email_type, EmailType.INTEREST)

    def test_new_opportunity_classification(self):
        result = classify_recruiter_email(
            subject="New role",
            body="We have a new opportunity with a vacancy for a data analyst.",
        )
        self.assertEqual(result.email_type, EmailType.NEW_OPPORTUNITY)

    def test_availability_request_classification(self):
        result = classify_recruiter_email(
            subject="Call availability",
            body="Please share your availability and suitable time slots.",
        )
        self.assertEqual(result.email_type, EmailType.AVAILABILITY_REQUEST)

    def test_screening_invite_classification(self):
        result = classify_recruiter_email(
            subject="Screening call",
            body="We would like to arrange a screening call or phone screen.",
        )
        self.assertEqual(result.email_type, EmailType.SCREENING_INVITE)

    def test_interview_invite_classification(self):
        result = classify_recruiter_email(
            subject="Interview invite",
            body="We would like to invite you to interview and share interview availability.",
        )
        self.assertEqual(result.email_type, EmailType.INTERVIEW_INVITE)

    def test_reschedule_or_cancellation_classification(self):
        result = classify_recruiter_email(
            subject="Interview update",
            body="We need to reschedule the call due to a cancellation.",
        )
        self.assertEqual(result.email_type, EmailType.RESCHEDULE_OR_CANCELLATION)

    def test_task_or_test_classification(self):
        result = classify_recruiter_email(
            subject="Assessment",
            body="Please complete this technical test and take-home task.",
        )
        self.assertEqual(result.email_type, EmailType.TASK_OR_TEST)

    def test_cv_request_classification(self):
        result = classify_recruiter_email(
            subject="CV request",
            body="Please send your cv and latest portfolio or github links.",
        )
        self.assertEqual(result.email_type, EmailType.CV_REQUEST)

    def test_document_request_classification(self):
        result = classify_recruiter_email(
            subject="Documents",
            body="Please share documents including proof of address and references.",
        )
        self.assertEqual(result.email_type, EmailType.DOCUMENT_REQUEST)

    def test_salary_question_classification(self):
        result = classify_recruiter_email(
            subject="Salary",
            body="What are your salary expectations and desired salary?",
        )
        self.assertEqual(result.email_type, EmailType.SALARY_QUESTION)

    def test_right_to_work_question_classification(self):
        result = classify_recruiter_email(
            subject="Right to work",
            body="Please confirm your right to work and visa status.",
        )
        self.assertEqual(result.email_type, EmailType.RIGHT_TO_WORK_QUESTION)

    def test_location_work_mode_question_classification(self):
        result = classify_recruiter_email(
            subject="Work mode",
            body="Can you confirm your location preference for hybrid or remote office days?",
        )
        self.assertEqual(result.email_type, EmailType.LOCATION_WORK_MODE_QUESTION)

    def test_role_closed_or_on_hold_classification(self):
        result = classify_recruiter_email(
            subject="Role update",
            body="The role has been closed and recruitment is on hold.",
        )
        self.assertEqual(result.email_type, EmailType.ROLE_CLOSED_OR_ON_HOLD)

    def test_offer_or_next_steps_classification(self):
        result = classify_recruiter_email(
            subject="Offer",
            body="We are pleased to offer you the role and outline next steps.",
        )
        self.assertEqual(result.email_type, EmailType.OFFER_OR_NEXT_STEPS)

    def test_empty_subject_and_body_returns_unknown(self):
        result = classify_recruiter_email(subject="", body="")
        self.assertEqual(result.email_type, EmailType.UNKNOWN)
        self.assertEqual(result.matched_signals, [])
        self.assertEqual(
            result.classification_rationale,
            "No recruiter email content was available to classify.",
        )
        self.assertTrue(result.requires_reply)

    def test_rejection_wins_when_rejection_and_interest_both_appear(self):
        result = classify_recruiter_email(
            subject="Update",
            body=(
                "Unfortunately we will not be taking your application further, "
                "but we are impressed with your profile."
            ),
        )
        self.assertEqual(result.email_type, EmailType.REJECTION)

    def test_matched_signals_serialise_as_json_list_text(self):
        result = classify_recruiter_email(
            subject="Rejection",
            body="Unfortunately your application was unsuccessful.",
        )
        serialised = serialise_matched_signals(result.matched_signals)
        self.assertEqual(json.loads(serialised), result.matched_signals)


class ReplyRequirementTests(TestCase):
    def test_acknowledgement_rejection_and_role_closed_do_not_require_reply(self):
        self.assertFalse(requires_reply_for_email_type(EmailType.ACKNOWLEDGEMENT))
        self.assertFalse(requires_reply_for_email_type(EmailType.REJECTION))
        self.assertFalse(requires_reply_for_email_type(EmailType.ROLE_CLOSED_OR_ON_HOLD))

    def test_interview_and_unknown_require_reply(self):
        self.assertTrue(requires_reply_for_email_type(EmailType.INTERVIEW_INVITE))
        self.assertTrue(requires_reply_for_email_type(EmailType.UNKNOWN))
        self.assertTrue(requires_reply_for_email_type(EmailType.OTHER))


class ActionDueDateTests(TestCase):
    def setUp(self):
        self.received = timezone.make_aware(datetime(2026, 5, 21, 9, 0, 0))

    def test_interview_invite_due_in_24_hours(self):
        due = suggest_action_due_at(EmailType.INTERVIEW_INVITE, self.received)
        self.assertEqual(due, self.received + timedelta(hours=24))

    def test_screening_invite_due_in_24_hours(self):
        due = suggest_action_due_at(EmailType.SCREENING_INVITE, self.received)
        self.assertEqual(due, self.received + timedelta(hours=24))

    def test_availability_request_due_in_48_hours(self):
        due = suggest_action_due_at(EmailType.AVAILABILITY_REQUEST, self.received)
        self.assertEqual(due, self.received + timedelta(hours=48))

    def test_acknowledgement_has_no_action_due(self):
        self.assertIsNone(
            suggest_action_due_at(EmailType.ACKNOWLEDGEMENT, self.received)
        )


class ReplyDraftTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="FinSight Group",
            job_title="Junior Data Analyst",
            salary_range="",
            date_applied=timezone.localdate(),
        )

    def test_draft_without_application_uses_placeholders_not_invented_facts(self):
        draft = generate_reply_draft(EmailType.INTEREST, application=None)
        self.assertIn("[Company name]", draft)
        self.assertIn("[Role title]", draft)
        self.assertNotIn("FinSight Group", draft)

    def test_right_to_work_draft_contains_placeholder_warning(self):
        draft = generate_reply_draft(
            EmailType.RIGHT_TO_WORK_QUESTION,
            application=self.application,
        )
        self.assertIn("[Confirm your right-to-work status before sending.]", draft)

    def test_salary_draft_does_not_invent_number_when_salary_range_blank(self):
        draft = generate_reply_draft(
            EmailType.SALARY_QUESTION,
            application=self.application,
        )
        self.assertIn("negotiable", draft.lower())
        self.assertNotRegex(draft, "\u00a3\\s?\\d")

    def test_acknowledgement_returns_empty_draft(self):
        self.assertEqual(
            generate_reply_draft(EmailType.ACKNOWLEDGEMENT, application=self.application),
            "",
        )


class SuggestedStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="statususer", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Test Co",
            job_title="Data Analyst",
            status=ApplicationStatus.SUBMITTED,
            date_applied=timezone.localdate(),
        )

    def test_suggest_status_update_does_not_mutate_application(self):
        original_status = self.application.status
        suggestion = suggest_status_update(EmailType.REJECTION)
        self.application.refresh_from_db()
        self.assertEqual(suggestion, "rejected")
        self.assertEqual(self.application.status, original_status)


class RecruiterEmailImportFormTests(TestCase):
    EXPOSED_FIELDS = {
        "subject",
        "sender_name",
        "sender_email",
        "body",
        "date_received",
        "notes",
    }

    def setUp(self):
        self.user = User.objects.create_user(username="importuser", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Import Co",
            job_title="Data Analyst",
            date_applied=timezone.localdate(),
        )
        self.received = timezone.now()

    def _valid_data(self, **overrides):
        data = {
            "subject": "Interview invite",
            "sender_name": "Recruiter",
            "sender_email": "recruiter@example.com",
            "body": (
                "We would like to invite you to interview and share "
                "interview availability."
            ),
            "date_received": self.received.strftime("%Y-%m-%dT%H:%M"),
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_form_valid_when_application_body_and_date_received_provided(self):
        form = RecruiterEmailImportForm(
            data=self._valid_data(),
            application=self.application,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_invalid_when_application_missing(self):
        form = RecruiterEmailImportForm(data=self._valid_data(), application=None)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_form_invalid_when_body_blank(self):
        form = RecruiterEmailImportForm(
            data=self._valid_data(body=""),
            application=self.application,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_form_invalid_when_date_received_blank(self):
        form = RecruiterEmailImportForm(
            data=self._valid_data(date_received=""),
            application=self.application,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("date_received", form.errors)

    def test_form_fields_do_not_expose_classification_or_system_fields(self):
        form = RecruiterEmailImportForm(application=self.application)
        self.assertEqual(set(form.fields.keys()), self.EXPOSED_FIELDS)


class CreateRecruiterEmailFromFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="saveuser", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Save Co",
            job_title="Junior Data Analyst",
            status=ApplicationStatus.SUBMITTED,
            date_applied=timezone.localdate(),
        )
        self.received = timezone.make_aware(datetime(2026, 5, 21, 10, 0, 0))

    def test_interview_invite_save_populates_classification_fields(self):
        form = RecruiterEmailImportForm(
            data={
                "subject": "Interview invitation",
                "sender_name": "",
                "sender_email": "",
                "body": (
                    "We would like to invite you to interview and share "
                    "interview availability."
                ),
                "date_received": self.received.strftime("%Y-%m-%dT%H:%M"),
                "notes": "",
            },
            application=self.application,
        )
        self.assertTrue(form.is_valid(), form.errors)
        recruiter_email = form.save()

        self.assertEqual(recruiter_email.application, self.application)
        self.assertEqual(recruiter_email.email_type, EmailType.INTERVIEW_INVITE)
        matched = json.loads(recruiter_email.matched_signals)
        self.assertIn("interview", matched)
        self.assertGreater(len(matched), 0)
        self.assertTrue(recruiter_email.reply_draft.strip())
        self.assertEqual(recruiter_email.reply_status, ReplyStatus.DRAFTED)
        self.assertTrue(recruiter_email.requires_reply)
        self.assertIsNotNone(recruiter_email.action_due_at)
        self.assertEqual(recruiter_email.suggested_application_status, "interview")
        self.assertEqual(recruiter_email.import_source, ImportSource.MANUAL)

    def test_acknowledgement_save_sets_not_required_and_no_action_due(self):
        form = RecruiterEmailImportForm(
            data={
                "subject": "Application received",
                "sender_name": "",
                "sender_email": "",
                "body": "Thank you for applying. We have received your application.",
                "date_received": self.received.strftime("%Y-%m-%dT%H:%M"),
                "notes": "",
            },
            application=self.application,
        )
        self.assertTrue(form.is_valid(), form.errors)
        recruiter_email = form.save()

        self.assertEqual(recruiter_email.email_type, EmailType.ACKNOWLEDGEMENT)
        self.assertEqual(recruiter_email.reply_status, ReplyStatus.NOT_REQUIRED)
        self.assertFalse(recruiter_email.requires_reply)
        self.assertIsNone(recruiter_email.action_due_at)

    def test_save_does_not_mutate_job_application_status(self):
        original_status = self.application.status
        form = RecruiterEmailImportForm(
            data={
                "subject": "Rejection",
                "sender_name": "",
                "sender_email": "",
                "body": "Unfortunately we will not be taking your application further.",
                "date_received": self.received.strftime("%Y-%m-%dT%H:%M"),
                "notes": "",
            },
            application=self.application,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, original_status)

    def test_save_with_commit_false_raises_value_error(self):
        form = RecruiterEmailImportForm(
            data={
                "subject": "Interview",
                "sender_name": "",
                "sender_email": "",
                "body": (
                    "We would like to invite you to interview and share "
                    "interview availability."
                ),
                "date_received": self.received.strftime("%Y-%m-%dT%H:%M"),
                "notes": "",
            },
            application=self.application,
        )
        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaises(ValueError):
            form.save(commit=False)

    def test_create_service_requires_application(self):
        with self.assertRaises(ValueError):
            create_recruiter_email_from_form_data(
                application=None,
                cleaned_data={
                    "subject": "",
                    "body": "Thank you for applying.",
                    "date_received": self.received,
                },
            )

    def test_create_service_persists_recruiter_email(self):
        recruiter_email = create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data={
                "subject": "Interview",
                "sender_name": "",
                "sender_email": "",
                "body": (
                    "We would like to invite you to interview and share "
                    "interview availability."
                ),
                "date_received": self.received,
                "notes": "Imported manually",
            },
        )
        self.assertTrue(RecruiterEmail.objects.filter(pk=recruiter_email.pk).exists())


class RecruiterEmailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="viewuser", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="View Co",
            job_title="Data Analyst",
            status=ApplicationStatus.SUBMITTED,
            date_applied=timezone.localdate(),
        )
        self.received = timezone.now()
        self.client.login(username="viewuser", password="StrongPass12345")

    def _import_post_data(self, **overrides):
        data = {
            "subject": "Interview invitation",
            "sender_name": "Recruiter",
            "sender_email": "recruiter@example.com",
            "body": (
                "We would like to invite you to interview and share "
                "interview availability."
            ),
            "date_received": self.received.strftime("%Y-%m-%dT%H:%M"),
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_import_form_get_returns_200_for_logged_in_owner(self):
        response = self.client.get(
            reverse("recruiter_emails:import", kwargs={"application_id": self.application.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import Recruiter Email")

    def test_import_form_post_creates_recruiter_email_and_redirects(self):
        original_status = self.application.status
        response = self.client.post(
            reverse("recruiter_emails:import", kwargs={"application_id": self.application.pk}),
            self._import_post_data(),
        )
        recruiter_email = RecruiterEmail.objects.get(application=self.application)
        self.assertRedirects(
            response,
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk}),
        )
        self.assertEqual(recruiter_email.application, self.application)
        self.assertEqual(recruiter_email.email_type, EmailType.INTERVIEW_INVITE)
        self.assertTrue(recruiter_email.matched_signals)
        self.assertTrue(recruiter_email.reply_draft.strip())
        self.assertEqual(recruiter_email.reply_status, ReplyStatus.DRAFTED)
        self.assertTrue(recruiter_email.requires_reply)
        self.assertIsNotNone(recruiter_email.action_due_at)
        self.assertEqual(recruiter_email.suggested_application_status, "interview")
        self.assertEqual(recruiter_email.import_source, ImportSource.MANUAL)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, original_status)

    def test_acknowledgement_import_sets_not_required_via_view(self):
        response = self.client.post(
            reverse("recruiter_emails:import", kwargs={"application_id": self.application.pk}),
            self._import_post_data(
                subject="Application received",
                body="Thank you for applying. We have received your application.",
            ),
        )
        recruiter_email = RecruiterEmail.objects.get(application=self.application)
        self.assertRedirects(
            response,
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk}),
        )
        self.assertEqual(recruiter_email.email_type, EmailType.ACKNOWLEDGEMENT)
        self.assertEqual(recruiter_email.reply_status, ReplyStatus.NOT_REQUIRED)
        self.assertFalse(recruiter_email.requires_reply)
        self.assertIsNone(recruiter_email.action_due_at)

    def test_detail_page_returns_200_and_shows_suggestion_label(self):
        recruiter_email = create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data={
                "subject": "Interview",
                "sender_name": "",
                "sender_email": "",
                "body": (
                    "We would like to invite you to interview and share "
                    "interview availability."
                ),
                "date_received": self.received,
                "notes": "",
            },
        )
        response = self.client.get(
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, recruiter_email.reply_draft)
        self.assertContains(response, "interview (suggestion only)")
        self.assertContains(response, "advisory only")

    def test_mark_sent_post_updates_reply_status(self):
        recruiter_email = create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data={
                "subject": "Interview",
                "sender_name": "",
                "sender_email": "",
                "body": (
                    "We would like to invite you to interview and share "
                    "interview availability."
                ),
                "date_received": self.received,
                "notes": "",
            },
        )
        original_status = self.application.status
        response = self.client.post(
            reverse("recruiter_emails:mark_sent", kwargs={"pk": recruiter_email.pk})
        )
        recruiter_email.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk}),
        )
        self.assertEqual(recruiter_email.reply_status, ReplyStatus.SENT_MANUALLY)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, original_status)

    def test_mark_sent_get_returns_405_without_mutation(self):
        recruiter_email = create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data={
                "subject": "Interview",
                "sender_name": "",
                "sender_email": "",
                "body": (
                    "We would like to invite you to interview and share "
                    "interview availability."
                ),
                "date_received": self.received,
                "notes": "",
            },
        )
        response = self.client.get(
            reverse("recruiter_emails:mark_sent", kwargs={"pk": recruiter_email.pk})
        )
        self.assertEqual(response.status_code, 405)
        recruiter_email.refresh_from_db()
        self.assertEqual(recruiter_email.reply_status, ReplyStatus.DRAFTED)


class RecruiterEmailWorkflowPolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="polish", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Polish Co",
            job_title="Data Analyst",
            status=ApplicationStatus.SUBMITTED,
            date_applied=timezone.localdate(),
        )
        self.received = timezone.now()
        self.client.login(username="polish", password="StrongPass12345")

    def _import_post_data(self, **overrides):
        data = {
            "subject": "Interview invitation",
            "sender_name": "Recruiter",
            "sender_email": "recruiter@example.com",
            "body": (
                "We would like to invite you to interview and share "
                "interview availability."
            ),
            "date_received": self.received.strftime("%Y-%m-%dT%H:%M"),
            "notes": "",
        }
        data.update(overrides)
        return data

    def _create_email(self, *, subject="Interview", body=None):
        if body is None:
            body = (
                "We would like to invite you to interview and share "
                "interview availability."
            )
        return create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data={
                "subject": subject,
                "sender_name": "",
                "sender_email": "",
                "body": body,
                "date_received": self.received,
                "notes": "",
            },
        )

    def test_import_form_shows_manual_workflow_steps(self):
        response = self.client.get(
            reverse("recruiter_emails:import", kwargs={"application_id": self.application.pk})
        )

        self.assertContains(response, "Paste the recruiter email manually")
        self.assertContains(response, "classifies the email locally")
        self.assertContains(response, "Mark the reply as sent manually only after you send it")
        self.assertContains(response, "No Gmail, Calendar, OAuth")

    def test_detail_shows_manual_reply_workflow_steps(self):
        recruiter_email = self._create_email()
        response = self.client.get(
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk})
        )

        self.assertContains(response, "Review classification and suggested action")
        self.assertContains(response, "Copy the draft into your email client")
        self.assertContains(response, "Mark reply as sent manually after you send it")
        self.assertContains(response, "Update application status yourself if needed")

    def test_detail_mark_sent_does_not_send_email(self):
        from apps.interviews.models import InterviewPrep

        recruiter_email = self._create_email()
        original_status = self.application.status
        prep_count_before = InterviewPrep.objects.count()

        response = self.client.post(
            reverse("recruiter_emails:mark_sent", kwargs={"pk": recruiter_email.pk}),
            follow=True,
        )

        recruiter_email.refresh_from_db()
        self.application.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(recruiter_email.reply_status, ReplyStatus.SENT_MANUALLY)
        self.assertEqual(self.application.status, original_status)
        self.assertEqual(InterviewPrep.objects.count(), prep_count_before)
        self.assertContains(response, "It does not send an email")

    def test_detail_no_gmail_oauth_calendar_claims(self):
        recruiter_email = self._create_email()
        response = self.client.get(
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk})
        )

        self.assertContains(response, "No Gmail, Calendar, OAuth")
        self.assertContains(response, "This page does not send email")

    def test_detail_shows_interview_prep_link_for_interview_signal(self):
        recruiter_email = self._create_email()
        interview_create_url = (
            reverse("interviews:interview_create")
            + f"?application={self.application.pk}"
        )

        response = self.client.get(
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk})
        )

        self.assertTrue(response.context["show_interview_prep_prompt"])
        self.assertContains(response, "Interview Prep Recommended")
        self.assertContains(response, interview_create_url)
        self.assertContains(response, "create interview prep automatically")

    def test_detail_hides_interview_prep_link_without_signal(self):
        recruiter_email = create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data={
                "subject": "Application received",
                "sender_name": "",
                "sender_email": "",
                "body": "Thank you for applying. We have received your application.",
                "date_received": self.received,
                "notes": "",
            },
        )

        response = self.client.get(
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk})
        )

        self.assertFalse(response.context["show_interview_prep_prompt"])
        self.assertNotContains(response, "Interview Prep Recommended")

    def test_import_save_still_does_not_mutate_application_status(self):
        original_status = self.application.status
        self.client.post(
            reverse("recruiter_emails:import", kwargs={"application_id": self.application.pk}),
            self._import_post_data(),
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, original_status)

    def test_detail_links_to_application_detail_and_ai_pack(self):
        recruiter_email = self._create_email()
        application_url = reverse(
            "applications:application_detail",
            kwargs={"pk": self.application.pk},
        )
        import_url = reverse(
            "recruiter_emails:import",
            kwargs={"application_id": self.application.pk},
        )
        pack_url = reverse(
            "ai_agents:application_agent_pack",
            kwargs={"pk": self.application.pk},
        )

        response = self.client.get(
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk})
        )

        self.assertContains(response, application_url)
        self.assertContains(response, import_url)
        self.assertContains(response, pack_url)
        self.assertContains(response, "Application Detail")
        self.assertContains(response, "Import another email")
        self.assertContains(response, "Application AI Pack")


class RecruiterEmailSecurityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="StrongPass12345")
        self.other = User.objects.create_user(username="other", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.owner,
            company_name="Owner Co",
            job_title="Analyst",
            date_applied=timezone.localdate(),
        )
        self.recruiter_email = create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data={
                "subject": "Interview",
                "sender_name": "",
                "sender_email": "",
                "body": (
                    "We would like to invite you to interview and share "
                    "interview availability."
                ),
                "date_received": timezone.now(),
                "notes": "",
            },
        )
        self.client.login(username="other", password="StrongPass12345")

    def test_other_user_cannot_access_import_form(self):
        response = self.client.get(
            reverse("recruiter_emails:import", kwargs={"application_id": self.application.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_post_import(self):
        response = self.client.post(
            reverse("recruiter_emails:import", kwargs={"application_id": self.application.pk}),
            {
                "subject": "Interview",
                "sender_name": "",
                "sender_email": "",
                "body": (
                    "We would like to invite you to interview and share "
                    "interview availability."
                ),
                "date_received": timezone.now().strftime("%Y-%m-%dT%H:%M"),
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(RecruiterEmail.objects.filter(application=self.application).count(), 1)

    def test_other_user_cannot_view_detail(self):
        response = self.client.get(
            reverse("recruiter_emails:detail", kwargs={"pk": self.recruiter_email.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_mark_sent(self):
        response = self.client.post(
            reverse("recruiter_emails:mark_sent", kwargs={"pk": self.recruiter_email.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.recruiter_email.refresh_from_db()
        self.assertEqual(self.recruiter_email.reply_status, ReplyStatus.DRAFTED)


class ApplicationDetailIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="detailuser", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Detail Co",
            job_title="Reporting Analyst",
            date_applied=timezone.localdate(),
        )
        self.client.login(username="detailuser", password="StrongPass12345")

    def test_application_detail_includes_import_link(self):
        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": self.application.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import Recruiter Email")
        self.assertContains(
            response,
            reverse("recruiter_emails:import", kwargs={"application_id": self.application.pk}),
        )

    def test_application_detail_lists_linked_recruiter_email(self):
        recruiter_email = create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data={
                "subject": "Screening call invite",
                "sender_name": "",
                "sender_email": "",
                "body": "We would like to arrange a screening call.",
                "date_received": timezone.now(),
                "notes": "",
            },
        )
        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": self.application.pk})
        )
        self.assertContains(response, recruiter_email.subject)
        self.assertContains(
            response,
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk}),
        )

