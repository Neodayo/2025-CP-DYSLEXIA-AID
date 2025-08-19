from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from .forms import ParentRegisterForm, ChildRegisterForm
from .models import ChildProfile  # <-- add this
from django.shortcuts import get_object_or_404

def parent_register(request):
    if request.method == "POST":
        form = ParentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # auto-login
            return redirect("parent_dashboard")
    else:
        form = ParentRegisterForm()
    return render(request, "accounts/parent_register.html", {"form": form})

@login_required
def child_register(request):
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can register children.")
    if request.method == "POST":
        form = ChildRegisterForm(request.POST)
        if form.is_valid():
            form.save(parent_user=request.user)
            return redirect("parent_dashboard")
    else:
        form = ChildRegisterForm()
    return render(request, "accounts/child_register.html", {"form": form})

@login_required
def parent_dashboard(request):
    if request.user.role != "PARENT":
        return redirect("login")
    
    children = ChildProfile.objects.filter(parent=request.user)
    return render(request, "accounts/parent_dashboard.html", {"children": children})

@login_required
def child_dashboard(request, child_id):
    child_profile = get_object_or_404(ChildProfile, child_id=child_id)

    if request.user != child_profile.parent and request.user != child_profile.child:
        return HttpResponseForbidden("Not authorized.")

    # Example: modules activated depending on dyslexia type
    modules_map = {
        "Phonological dyslexia": ["Phonics Training", "Sound Recognition"],
        "Surface dyslexia": ["Word Recognition", "Sight Words"],
        "Visual dyslexia": ["Visual Tracking", "Reading Exercises"],
        "Rapid naming deficit": ["Speed Reading", "Naming Drills"],
        "Developmental dyslexia": ["General Reading", "Adaptive Lessons"],
        "Acquired dyslexia": ["Memory Support", "Rehabilitation Exercises"],
    }

    modules = modules_map.get(child_profile.dyslexia_type, [])

    return render(
        request,
        "accounts/child_dashboard.html",
        {
            "child_profile": child_profile,
            "modules": modules,
        },
    )





def home(request):
    if request.user.is_authenticated and request.user.role == "PARENT":
        return redirect("parent_dashboard")
    return render(request, "accounts/home.html")

@login_required
def introduction(request, child_id):
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can access this page.")

    child_profile = get_object_or_404(ChildProfile, child_id=child_id)
    if request.method == "POST":
        return redirect("type_selection", child_id=child_profile.child.id)

    return render(request, "accounts/introduction.html", {"child_profile": child_profile})


@login_required
def type_selection(request, child_id):
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can assign dyslexia type.")

    child_profile = get_object_or_404(ChildProfile, child_id=child_id)

    dyslexia_types = [
        "Developmental dyslexia",
        "Acquired dyslexia",
        "Phonological dyslexia",
        "Surface dyslexia",
        "Rapid naming deficit",
        "Visual dyslexia",
    ]

    if request.method == "POST":
        dyslexia_type = request.POST.get("dyslexia_type")
        child_profile.dyslexia_type = dyslexia_type
        child_profile.save()
        # ✅ After choosing → go to child dashboard
        return redirect("child_dashboard", child_id=child_profile.child.id)

    return render(
        request,
        "accounts/type_selection.html",
        {"child_profile": child_profile, "dyslexia_types": dyslexia_types},
    )
