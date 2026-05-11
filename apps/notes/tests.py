from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .choices import NoteType
from .models import Note


class NoteModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_note_string_representation(self):
        note = Note.objects.create(user=self.user, note_type=NoteType.STRATEGY, title="Focus on junior Data Analyst roles", content="Avoid senior roles for now.")
        self.assertEqual(str(note), "Strategy decision — Focus on junior Data Analyst roles")

    def test_tag_list_returns_clean_tags(self):
        note = Note.objects.create(user=self.user, title="CV Update", content="Updated CV headline.", tags="CV, LinkedIn, screening ")
        self.assertEqual(note.tag_list, ["CV", "LinkedIn", "screening"])


class NoteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_note_list_requires_login(self):
        response = self.client.get(reverse("notes:note_list"))
        self.assertEqual(response.status_code, 302)

    def test_note_list_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("notes:note_list"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_create_note(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(reverse("notes:note_create"), {"note_type": NoteType.CV_CHANGE, "title": "Updated CV headline", "content": "Changed headline to Data Analyst focused version.", "tags": "CV, LinkedIn", "decision_date": "2026-05-09", "is_important": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Note.objects.filter(title="Updated CV headline").exists())


class NotePermissionTests(TestCase):
    def setUp(self):
        self.user_one = User.objects.create_user(username="userone", password="StrongPass12345")
        self.user_two = User.objects.create_user(username="usertwo", password="StrongPass12345")
        self.note = Note.objects.create(user=self.user_one, title="Private strategy note", content="Only user one should see this.")

    def test_user_cannot_view_other_users_note(self):
        self.client.login(username="usertwo", password="StrongPass12345")
        response = self.client.get(reverse("notes:note_detail", kwargs={"pk": self.note.pk}))
        self.assertEqual(response.status_code, 404)
