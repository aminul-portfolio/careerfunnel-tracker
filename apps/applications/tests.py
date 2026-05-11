from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .choices import ApplicationStatus, RoleFit, WorkType
from .models import JobApplication
from .services import calculate_response_rate


class JobApplicationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_days_to_response_returns_correct_value(self):
        application = JobApplication.objects.create(user=self.user, company_name="Test Company", job_title="Data Analyst", date_applied=date(2026, 5, 1), response_date=date(2026, 5, 4), status=ApplicationStatus.ACKNOWLEDGED)
        self.assertEqual(application.days_to_response, 3)

    def test_days_to_response_returns_none_without_response_date(self):
        application = JobApplication.objects.create(user=self.user, company_name="Test Company", job_title="Data Analyst", date_applied=date(2026, 5, 1), status=ApplicationStatus.SUBMITTED)
        self.assertIsNone(application.days_to_response)


class JobApplicationViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_application_list_requires_login(self):
        response = self.client.get(reverse("applications:application_list"))
        self.assertEqual(response.status_code, 302)

    def test_application_list_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("applications:application_list"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_create_application(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(reverse("applications:application_create"), {"company_name": "Example Ltd", "job_title": "Junior Data Analyst", "job_url": "https://example.com/job", "location": "London", "work_type": WorkType.HYBRID, "salary_range": "£30,000 - £35,000", "source": "linkedin", "role_fit": RoleFit.STRONG, "date_applied": "2026-05-09", "status": ApplicationStatus.SUBMITTED, "response_date": "", "cv_version": "DA_CV_v1", "cover_letter_version": "Tailored_CL_v1", "contact_name": "", "contact_email": "", "notes": "Good fit."})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(JobApplication.objects.filter(company_name="Example Ltd").exists())


class ApplicationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_response_rate_is_zero_without_applications(self):
        self.assertEqual(calculate_response_rate(self.user), 0.0)

    def test_response_rate_calculates_correctly(self):
        JobApplication.objects.create(user=self.user, company_name="Company A", job_title="Data Analyst", date_applied=date(2026, 5, 1), status=ApplicationStatus.SUBMITTED)
        JobApplication.objects.create(user=self.user, company_name="Company B", job_title="BI Analyst", date_applied=date(2026, 5, 2), status=ApplicationStatus.ACKNOWLEDGED)
        self.assertEqual(calculate_response_rate(self.user), 50.0)
