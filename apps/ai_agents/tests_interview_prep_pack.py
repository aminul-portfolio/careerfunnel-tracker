from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.ai_agents.interview_prep_pack import (
    build_interview_prep_pack,
    select_application_project_evidence,
)
from apps.ai_agents.services import generate_interview_prep
from apps.applications.models import JobApplication

ALL_KNOWN_PROJECTS = {
    "BakeOps Intelligence",
    "CareerFunnel Tracker",
    "MarketVista Dashboard",
    "TradeIntel 360",
    "RiskWise Planner",
    "DataBridge Market API",
}

FORBIDDEN_CLAIMS = (
    "guaranteed",
    "automatic interview success",
    "auto-apply",
)


class InterviewPrepPackServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="prep-pack", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 31),
            job_description=(
                "Junior data analyst role with KPI reporting, Excel, SQL, Python, "
                "dashboards, and operational analytics."
            ),
        )

    def test_project_set_selected_once_and_reused(self):
        projects = select_application_project_evidence(self.application)
        prep = build_interview_prep_pack(self.application)
        self.assertEqual(prep.projects_to_use, projects)
        self.assertEqual(tuple(item.name for item in prep.project_evidence), projects)
        self.assertEqual(tuple(story.project_name for story in prep.evidence_stories), projects)

    def test_technical_topics_reference_selected_projects_only(self):
        prep = build_interview_prep_pack(self.application)
        allowed = set(prep.projects_to_use)
        for topic in prep.technical_topics:
            referenced = [
                project
                for project in ALL_KNOWN_PROJECTS
                if project in topic.project_evidence
            ]
            if referenced:
                self.assertTrue(all(project in allowed for project in referenced))

    def test_star_answers_include_star_structure(self):
        prep = build_interview_prep_pack(self.application)
        self.assertGreaterEqual(len(prep.star_examples), 6)
        for star in prep.star_examples:
            self.assertTrue(star.situation)
            self.assertTrue(star.task)
            self.assertTrue(star.action)
            self.assertTrue(star.result)

    def test_likely_questions_are_grouped(self):
        prep = build_interview_prep_pack(self.application)
        group_names = {group.group_name for group in prep.likely_questions}
        self.assertIn("Motivation / Profile", group_names)
        self.assertIn("Technical", group_names)
        self.assertIn("Project Evidence", group_names)
        self.assertIn("Behavioural", group_names)

    def test_checklist_references_selected_projects(self):
        prep = build_interview_prep_pack(self.application)
        checklist_text = " ".join(prep.preparation_tasks)
        for project in prep.projects_to_use:
            self.assertIn(project, checklist_text)

    def test_unselected_projects_not_in_project_questions(self):
        prep = build_interview_prep_pack(self.application)
        project_group = next(
            group for group in prep.likely_questions if group.group_name == "Project Evidence"
        )
        combined = " ".join(project_group.questions)
        unselected = ALL_KNOWN_PROJECTS - set(prep.projects_to_use)
        for project in unselected:
            self.assertNotIn(project, combined)


class InterviewPrepPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="prep-page", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 31),
            job_description="KPI reporting, Excel, SQL, Python, dashboards, operations.",
        )
        self.url = reverse("ai_agents:interview_prep_generator")
        self.client.login(username="prep-page", password="StrongPass12345")

    def test_interview_prep_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select Application")
        self.assertContains(response, "Generate Interview Prep")

    def test_generate_interview_prep_shows_full_pack(self):
        response = self.client.post(self.url, {"application": self.application.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Interview preparation pack")
        self.assertContains(response, "Howden - Junior Data Analyst")
        self.assertContains(response, "Profile Angle")
        self.assertContains(response, "Project Evidence Set")
        self.assertContains(response, "Technical Topics to Revise")
        self.assertContains(response, "Likely Interview Questions")
        self.assertContains(response, "STAR Answer Bank")
        self.assertContains(response, "Evidence Stories to Prepare")
        self.assertContains(response, "Employer Questions to Ask")
        self.assertContains(response, "Final Interview Checklist")
        self.assertContains(response, "Situation")
        self.assertContains(response, "Task")
        self.assertContains(response, "Action")
        self.assertContains(response, "Result")

    def test_same_projects_across_sections_in_rendered_page(self):
        prep = generate_interview_prep(self.application)
        response = self.client.post(self.url, {"application": self.application.pk})
        content = response.content.decode()
        for project in prep.projects_to_use:
            self.assertGreaterEqual(content.count(project), 3)

    def test_no_forbidden_claims_on_page(self):
        response = self.client.post(self.url, {"application": self.application.pk})
        content = response.content.decode().lower()
        for phrase in FORBIDDEN_CLAIMS:
            self.assertNotIn(phrase.lower(), content)
        self.assertContains(response, "Manual review required")
        self.assertContains(response, "advisory")
