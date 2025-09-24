from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from .forms import ParentRegisterForm, ChildRegisterForm, IndependentRegisterForm, DyslexiaTypeForm, ChildProfileEditForm
from .forms import DyslexiaTypeForm
from django.contrib import messages
import time 
from .models import CustomUser, ChildProfile # <-- add this
from django.shortcuts import get_object_or_404
import joblib
import pandas as pd
import os



# Load ML model (do this once when server starts)
ml_model = joblib.load("ml/dyslexia_model.pkl")

def parent_register(request):
    if request.method == "POST":
        form = ParentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("parent_dashboard")
    else:
        form = ParentRegisterForm()
    return render(request, "registration/parent_register.html", {"form": form})

@login_required
def delete_child(request, child_id):
    """Delete a child user and their profile"""
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can delete children.")
    
    # Get the child user and verify they belong to this parent
    child_user = get_object_or_404(CustomUser, id=child_id, role="CHILD")
    child_profile = get_object_or_404(ChildProfile, child=child_user, parent=request.user)
    
    if request.method == "POST":
        # Delete the child user and their profile
        child_user.delete()  # This will also delete the ChildProfile due to CASCADE
        messages.success(request, f"Successfully deleted {child_user.username}'s account.")
        return redirect("parent_dashboard")
    
    # For GET requests, show confirmation page
    return render(request, "accounts/delete_child_confirm.html", {
        "child_user": child_user,
        "child_profile": child_profile
    })

@login_required
def switch_to_child(request, child_id):
    """Switch from parent to child account"""
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can switch to child accounts.")
    
    # Get the child user
    child_user = get_object_or_404(CustomUser, id=child_id, role='CHILD')
    
    # Verify this child belongs to the parent
    try:
        child_profile = ChildProfile.objects.get(child=child_user, parent=request.user)
    except ChildProfile.DoesNotExist:
        return HttpResponseForbidden("You can only switch to your own children.")
    
    # Store original parent in session
    request.session['original_user_id'] = request.user.id
    request.session['is_impersonating'] = True
    
    # Log in as child (this changes the actual authenticated user)
    login(request, child_user)
    
    # Redirect to child's dashboard
    return redirect('child_dashboard', child_id=child_id)

@login_required
def child_register(request):
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can register children.")

    if request.method == "POST":
        form = ChildRegisterForm(request.POST)
        if form.is_valid():
            # Save child linked to parent
            child_user = form.save(parent_user=request.user)

            # ✅ Redirect straight to dyslexia type selection page
            return redirect("dyslexia_type_selection", child_id=child_user.id)
    else:
        form = ChildRegisterForm()

    return render(request, "registration/child_register.html", {"form": form})


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
    return render(request, "registration/independent_register.html", {"form": form})



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

def child_dashboard(request, child_id):
    profile = get_object_or_404(ChildProfile, child_id=child_id)

    if request.user != profile.child and request.user != profile.parent:
        return HttpResponseForbidden("Not authorized.")

    # ✅ Check if evaluation was completed (using session storage)
    evaluation_completed = request.session.pop('evaluation_completed', False)
    dyslexia_type_evaluated = request.session.pop('dyslexia_type_evaluated', '')

    # ✅ Use the assigned dyslexia type (post-diagnosed)
    assigned_type = profile.dyslexia_type  

    # ✅ Optional: ML suggestion (for reference only)
    suggested_type = None
    try:
        features = get_user_features(profile.child.id)
        suggested_type = ml_model.predict([features])[0]
    except Exception as e:
        print("ML suggestion error:", e)

    # ✅ Modules mapping
    modules_map = {
        "Phonological": [
            {"id": 1, "name": "Phonics Training", "description": "Improve sound recognition.", "progress": 0},
            {"id": 2, "name": "Sound Recognition", "description": "Practice breaking down words.", "progress": 0},
        ],
        "Surface": [
            {"id": 3, "name": "Sight Words", "description": "Recognize whole words quickly.", "progress": 0},
        ],
        "Visual": [
            {"id": 4, "name": "Visual Tracking", "description": "Train smooth eye movements.", "progress": 0},
        ],
        "Rapid Naming": [
            {"id": 5, "name": "Naming Drills", "description": "Practice quick recall.", "progress": 0},
        ],
        "Developmental": [
            {"id": 6, "name": "General Reading", "description": "Adaptive reading lessons.", "progress": 0},
        ],
        "Acquired": [
            {"id": 7, "name": "Memory Support", "description": "Rehabilitation-based reading.", "progress": 0},
        ],
    }

    modules = modules_map.get(assigned_type, [])
    lessons = [{"title": m["name"], "completed": False} for m in modules]

    progress_data = {
        "points": 0,
        "completed": 0,
        "total": len(modules),
        "percentage": 0,
    }

    return render(request, "accounts/base_child.html", {
        "child_profile": profile,
        "assigned_type": assigned_type,
        "suggested_type": suggested_type,  # optional
        "progress_data": progress_data,
        "modules": modules,
        "lessons": lessons,
        "evaluation_completed": evaluation_completed,  # NEW: Add evaluation status
        "dyslexia_type_evaluated": dyslexia_type_evaluated,  # NEW: Add evaluated type
    })

def landing_page(request):
    if request.user.is_authenticated and request.user.role == "PARENT":
        return redirect("parent_dashboard")
    return render(request, "accounts/landing_page.html")

@login_required
def introduction(request, child_id):
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can access this page.")

    child_profile = get_object_or_404(ChildProfile, child_id=child_id)
    if request.method == "POST":
        return redirect("type_selection", child_id=child_profile.child.id)

    return render(request, "accounts/introduction.html", {"child_profile": child_profile})



@login_required
def dyslexia_type_selection(request, child_id):
    profile = get_object_or_404(ChildProfile, child_id=child_id)

    # Store the child ID in session for later use in evaluation
    request.session['current_child_id'] = child_id

    # Parent, child, or independent can assign
    if request.user != profile.child and request.user != getattr(profile, 'parent', None):
        return HttpResponseForbidden("Not authorized.")

    dyslexia_types = [
        "Developmental dyslexia",
        "Acquired dyslexia",
        "Phonological dyslexia",
        "Surface dyslexia",
        "Rapid naming deficit",
        "Visual dyslexia",
    ]

    if request.method == "POST":
        selected_type = request.POST.get("dyslexia_type")
        if selected_type in dyslexia_types:
            profile.dyslexia_type = selected_type
            profile.save()
            return redirect("evaluation_test", dyslexia_type=selected_type)

    return render(request, "accounts/dyslexia_type_selection.html", {
        "child_profile": profile,
        "dyslexia_types": dyslexia_types
    })

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
    return render(request, "lessons/child_modules.html", {
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


def get_user_features(user_id):
    """
    Fetch user-specific features.
    For now, load a placeholder CSV. Later link with your DB or uploaded data.
    """
    # Example placeholder: each user gets same mock data
    df = pd.DataFrame([{
        "n_fix_trial": 120,
        "mean_fix_dur_trial": 220,
        "n_sacc_trial": 85,
        "n_regress_trial": 15
    }])
    return df[["n_fix_trial", "mean_fix_dur_trial", "n_sacc_trial", "n_regress_trial"]].iloc[0].tolist()

# --------------------------------------------------Evaluation Area ---------------------------------------------------

def evaluation_test(request, dyslexia_type):
    # Question bank
    questions_bank = {
        "Phonological dyslexia": [
            "Which word rhymes with 'cat'? (bat, dog, sun)",
            "Break the word 'sunset' into syllables.",
            "Identify the first sound in 'phone'.",
            "Which of these words start with the same sound as 'dog'? (desk, cat, fish)",
            "How many sounds are in the word 'ship'?",
        ],
        "Surface dyslexia": [
            "What word is this? (sight word: 'the')",
            "Which of these words looks correct? (frend / friend)",
            "Read this word without sounding it out: 'yacht'.",
            "Which of these is a real word? (knight / nite)",
            "Identify the irregular word: (said, bed, red)",
        ],
        "Visual dyslexia": [
            "Which direction is the letter 'b' facing?",
            "Do you see a difference between 'was' and 'saw'?",
            "Identify the odd one out: (p q d b).",
            "Trace this word visually: 'elephant'.",
            "Which number is reversed? (3, Ɛ, 5)",
        ],
        "Rapid naming deficit": [
            "Say the names of these pictures quickly (dog, sun, car, ball).",
            "Which is faster: saying the alphabet or numbers?",
            "Read this color as fast as you can: 'red'.",
            "Name 5 fruits as quickly as possible.",
            "Identify this letter instantly: 'M'.",
        ],
        "Developmental dyslexia": [
            "Read the word: 'basket'.",
            "Sound out this word: 'computer'.", 
            "What does the sentence mean: 'The dog chased the cat'?",
            "Which word is easiest to read: (pen, apple, elephant)?",
            "Arrange the letters to form a word: 'HAT'.",
        ],
        "Acquired dyslexia": [
            "Read this word aloud: 'doctor'.",
            "Match this picture 🐱 with the correct word (cat, dog, bat).",
            "Which of these words is easier for you? (book / bicycle)",
            "Read this short sentence: 'I am happy'.",
            "Point to the correct word: (tree, free, three).",
        ],
    }

    # Grab the correct set of questions for the chosen type
    questions = questions_bank.get(dyslexia_type, [])

# Handle form submission
    if request.method == "POST":
        # Store evaluation completion in session
        request.session['evaluation_completed'] = True
        request.session['dyslexia_type_evaluated'] = dyslexia_type
        request.session['evaluation_timestamp'] = str(time.time())
        
        # Get the correct child ID
        try:
            # If the current user is a child/independent, use their own ID
            if request.user.role in ["CHILD", "INDEPENDENT"]:
                child_id = request.user.id
            else:
                # If the current user is a parent, get the child ID from session
                child_id = request.session.get('current_child_id')
                if not child_id:
                    # Fallback: try to find the first child of the parent
                    child_profile = ChildProfile.objects.filter(parent=request.user).first()
                    if child_profile:
                        child_id = child_profile.child.id
                    else:
                        # If no children found, redirect to parent dashboard
                        return redirect("parent_dashboard")
        except:
            # If all else fails, redirect to login redirect page
            return redirect("login_redirect")
        
        # Redirect to child dashboard
        return redirect("child_dashboard", child_id=child_id)

    # Handle GET request (display form)
    context = {
        "dyslexia_type": dyslexia_type,
        "questions": questions,
    }
    return render(request, "evaluation/static_evaluation.html", context)