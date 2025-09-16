from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from .forms import ParentRegisterForm, ChildRegisterForm, IndependentRegisterForm, DyslexiaTypeForm, ChildProfileEditForm
from .forms import DyslexiaTypeForm
from .models import CustomUser, ChildProfile # <-- add this
from django.shortcuts import get_object_or_404
from django.contrib.auth import logout


def parent_register(request):
    if request.method == "POST":
        form = ParentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
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
            user.role = "INDEPENDENT"
            user.save()

            ChildProfile.objects.create(child=user, dyslexia_type=None)

            login(request, user)  # ✅ this logs in the independent user

            return redirect("dyslexia_type_selection", child_id=user.id)
    else:
        form = IndependentRegisterForm()
    return render(request, "accounts/independent_register.html", {"form": form})



@login_required
def login_redirect(request):
    user = request.user

    if user.role == "PARENT":
        return redirect("parent_dashboard")

    elif user.role == "CHILD":
        try:
            profile = ChildProfile.objects.get(child=user)
            return redirect("child_dashboard", child_id=profile.child.id)
        except ChildProfile.DoesNotExist:
            return HttpResponseForbidden("Child profile missing. Parent must create one.")

    elif user.role == "INDEPENDENT":
        profile, created = ChildProfile.objects.get_or_create(
            child=user,
            defaults={"dyslexia_type": None}
        )
        if profile.dyslexia_type:
            return redirect("child_dashboard", child_id=profile.child.id)
        else:
            return redirect("dyslexia_type_selection", child_id=profile.child.id)

    # ❌ Don’t redirect to login again (causes loop)
    return HttpResponseForbidden("Unknown role or access denied.")




@login_required
def parent_dashboard(request):
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can access this page.")
    children = ChildProfile.objects.filter(parent=request.user)
    return render(request, "accounts/parent_dashboard.html", {"children": children})

@login_required
def child_dashboard(request, child_id):
    profile = get_object_or_404(ChildProfile, child_id=child_id)

    # Access allowed if user is child/independent OR parent
    if request.user != profile.child and request.user != getattr(profile, 'parent', None):
        return HttpResponseForbidden("Not authorized.")

    modules_map = {
        "Phonological dyslexia": ["Phonics Training", "Sound Recognition"],
        "Surface dyslexia": ["Word Recognition", "Sight Words"],
        "Visual dyslexia": ["Visual Tracking", "Reading Exercises"],
        "Rapid naming deficit": ["Speed Reading", "Naming Drills"],
        "Developmental dyslexia": ["General Reading", "Adaptive Lessons"],
        "Acquired dyslexia": ["Memory Support", "Rehabilitation Exercises"],
    }

    modules = modules_map.get(profile.dyslexia_type, [])

    return render(
        request,
        "accounts/child_home.html",
        {"child_profile": profile, "modules": modules},
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
#for independent user to select dyslexia type

@login_required
def dyslexia_type_selection(request, child_id):
    profile = get_object_or_404(ChildProfile, child_id=child_id)

    # ✅ Only independent user can set their own type
    if request.user != profile.child:
        return HttpResponseForbidden("Not authorized.")

    if request.method == "POST":
        form = DyslexiaTypeForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("child_dashboard", child_id=profile.child.id)
    else:
        form = DyslexiaTypeForm(instance=profile)

    return render(request, "accounts/dyslexia_type_selection.html", {"form": form})


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

@login_required
def custom_logout(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")  # Always go back to login after logout
    return redirect("home")  # fallback for GET


@login_required
def edit_child_profile(request, child_id):
    child_user = get_object_or_404(CustomUser, id=child_id, role="CHILD")
    child_profile = get_object_or_404(ChildProfile, child=child_user)

    # Only parent of this child OR the child themselves can edit
    if request.user != child_user and request.user != getattr(child_profile, 'parent', None):
        return HttpResponseForbidden("Not authorized.")

    if request.method == "POST":
        form = ChildProfileEditForm(request.POST, instance=child_profile, child_instance=child_user)
        if form.is_valid():
            form.save()
            return redirect("child_profile", child_id=child_user.id)
    else:
        form = ChildProfileEditForm(instance=child_profile, child_instance=child_user)

    return render(request, "accounts/edit_child_profile.html", {
        "form": form,
        "child_profile": child_profile
    })

def about_us(request):
    return render(request, "accounts/about_page.html")