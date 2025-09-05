from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from .forms import ParentRegisterForm, ChildRegisterForm, IndependentRegisterForm
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

def independent_register(request):
    if request.method == "POST":
        form = IndependentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = "independent"   # assign role
            user.save()

            # ✅ Create a ChildProfile automatically
            child_profile = ChildProfile.objects.create(
                child=user,
                dyslexia_type="General"  # default, can be updated later by user
            )

            # Redirect to child_dashboard with child_id
            return redirect("child_dashboard", child_id=child_profile.child.id)
    else:
        form = IndependentRegisterForm()

    return render(request, "accounts/independent_register.html", {"form": form})


def login_redirect(request):
    if request.user.is_authenticated:
        if request.user.role == "PARENT":
            return redirect("parent_dashboard")
        elif request.user.role in ["CHILD", "INDEPENDENT"]:
            try:
                child_profile = ChildProfile.objects.get(child=request.user)
                return redirect("child_dashboard", child_id=child_profile.child.id)
            except ChildProfile.DoesNotExist:
                return redirect("login")  # fallback if profile missing
    return redirect("login")


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
        "accounts/child_home.html",
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



@login_required
def child_home(request, child_id):
    child_profile = get_object_or_404(ChildProfile, child_id=child_id)
    progress = 50  # later calculate dynamically
    return render(request, "accounts/child_home.html", {
        "child_profile": child_profile,
        "progress": progress
    })

@login_required
def child_modules(request, child_id):
    child_profile = get_object_or_404(ChildProfile, child_id=child_id)
    # Fetch modules from DB (admin uploads) – placeholder for now
    all_modules = ["Phonics Training", "Sight Words", "Visual Tracking", "Speed Reading"]
    return render(request, "accounts/child_modules.html", {
        "child_profile": child_profile,
        "modules": all_modules
    })

@login_required
def child_profile(request, child_id):
    child_profile = get_object_or_404(ChildProfile, child_id=child_id)
    return render(request, "accounts/child_profile.html", {
        "child_profile": child_profile
    })

@login_required
def child_progress(request, child_id):
    child_profile = get_object_or_404(ChildProfile, child_id=child_id)
    # Placeholder progress data
    progress_data = {"completed": 3, "total": 5}
    return render(request, "accounts/child_progress.html", {
        "child_profile": child_profile,
        "progress_data": progress_data
    })
