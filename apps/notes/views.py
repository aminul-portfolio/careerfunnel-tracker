from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import NoteForm
from .models import Note


@login_required
def note_list(request):
    notes = Note.objects.filter(user=request.user)
    note_type_filter = request.GET.get("type")
    search_query = request.GET.get("q")
    important_filter = request.GET.get("important")
    if note_type_filter:
        notes = notes.filter(note_type=note_type_filter)
    if important_filter == "1":
        notes = notes.filter(is_important=True)
    if search_query:
        notes = notes.filter(Q(title__icontains=search_query) | Q(content__icontains=search_query) | Q(tags__icontains=search_query))
    return render(request, "notes/note_list.html", {"notes": notes, "note_type_filter": note_type_filter or "", "search_query": search_query or "", "important_filter": important_filter or ""})


@login_required
def note_detail(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    return render(request, "notes/note_detail.html", {"note": note})


@login_required
def note_create(request):
    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            messages.success(request, "Note created successfully.")
            return redirect(note.get_absolute_url())
    else:
        form = NoteForm()
    return render(request, "notes/note_form.html", {"form": form, "page_title": "Add Note / Decision", "submit_label": "Save Note"})


@login_required
def note_update(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, "Note updated successfully.")
            return redirect(note.get_absolute_url())
    else:
        form = NoteForm(instance=note)
    return render(request, "notes/note_form.html", {"form": form, "page_title": "Edit Note / Decision", "submit_label": "Update Note", "note": note})


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == "POST":
        note.delete()
        messages.success(request, "Note deleted successfully.")
        return redirect("notes:note_list")
    return render(request, "notes/note_confirm_delete.html", {"note": note})
