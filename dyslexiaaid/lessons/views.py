from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
import json

from .models import Lesson, Attempt, Module
from accounts.models import ChildProfile 



def child_modules(request, child_id):
    # Get the child profile
    child_profile = get_object_or_404(ChildProfile, child_id=child_id)

    # Fetch all modules (later you can filter by dyslexia_type if needed)
    modules = Module.objects.all()

    return render(request, "lessons/child_modules.html", {
        "child_profile": child_profile,
        "modules": modules,
    })

@login_required
def lesson_list(request):
    # If the logged-in user is a child, filter by their dyslexia_type
    dyslexia_type = None
    try:
        cp = ChildProfile.objects.get(child=request.user)
        dyslexia_type = cp.dyslexia_type
    except ChildProfile.DoesNotExist:
        pass

    if dyslexia_type:
        lessons = Lesson.objects.filter(dyslexia_type=dyslexia_type)
    else:
        lessons = Lesson.objects.all()

    return render(request, "lessons/lesson_list.html", {
        "lessons": lessons,
        "dyslexia_type": dyslexia_type,
        "title": "Lessons",
    })


@login_required
def lesson_detail(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)

    # optional: only allow CHILD role to open lessons
    if getattr(request.user, "role", None) == "PARENT":
        return HttpResponseForbidden("Parents cannot take lessons.")

    return render(request, "lessons/lesson_detail.html", {
        "lesson": lesson,
        "title": lesson.title,
    })


@login_required
@csrf_exempt
def record_attempt(request, lesson_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    selected = (data.get("selected_choice") or "").upper().strip()
    time_spent_ms = int(data.get("time_spent_ms") or 0)
    tts_plays = int(data.get("tts_plays") or 0)
    repeats = int(data.get("repeats") or 0)

    lesson = get_object_or_404(Lesson, pk=lesson_id)
    correct = (selected == lesson.correct_choice.upper()) if lesson.correct_choice else False

    Attempt.objects.create(
        child=request.user,
        lesson=lesson,
        selected_choice=selected,
        is_correct=correct,
        time_spent_ms=time_spent_ms,
        tts_plays=tts_plays,
        repeats=repeats,
    )

    return JsonResponse({"ok": True, "is_correct": correct})
