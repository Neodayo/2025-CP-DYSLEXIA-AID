from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect,  get_object_or_404
from django.http import HttpResponseForbidden
from .forms import ParentRegisterForm, ChildRegisterForm, IndependentRegisterForm, DyslexiaTypeForm, ChildProfileEditForm
from .forms import DyslexiaTypeForm
from django.contrib import messages
import time 
from .models import CustomUser, ChildProfile
import joblib
import pandas as pd
import os
from django.utils import timezone
import speech_recognition as sr
import json
from django.http import JsonResponse




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
def switch_to_child(request, child_id=0):
    # If child_id is 0, check for POST data
    if child_id == 0:
        child_id = request.POST.get('child_id')
        if not child_id:
            messages.error(request, "No child selected.")
            return redirect('parent_dashboard')
    
    # Rest of your existing code...
    if request.user.role != 'PARENT':
        messages.error(request, "Only parents can switch to child accounts.")
        return redirect('parent_dashboard')
    
    child_profile = get_object_or_404(ChildProfile, id=child_id, parent=request.user)
    child_user = child_profile.child
    
    # Store parent session data
    request.session['original_parent'] = {
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email
    }
    request.session['child_login_time'] = timezone.now().isoformat()
    request.session['is_impersonating'] = True
    
    # Log in the child user
    login(request, child_user)
    
    messages.success(request, f"Now logged in as {child_user.username}")
    return redirect('child_dashboard')



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



def is_parent(user):
    """Check if user has PARENT role"""
    return user.is_authenticated and user.role == 'PARENT'

@login_required
@user_passes_test(is_parent, login_url='/access-denied/')
def parent_dashboard(request):
    """Parent dashboard view - only accessible to PARENT role users"""
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can access this page.")
    
    children_profiles = ChildProfile.objects.filter(parent=request.user)
    
    return render(request, "accounts/parent_dashboard.html", {"children": children_profiles})

@login_required
@user_passes_test(is_parent, login_url='/access-denied/')
def switch_to_child(request, child_id):
    """Switch to child account - only accessible to parents"""
    if request.method == 'POST':
        try:
            child_profile = ChildProfile.objects.get(child__id=child_id, parent=request.user)
            request.session['child_user_id'] = child_id
            messages.success(request, f"Switched to {child_profile.child.username}'s account")
            return redirect('child_dashboard', child_id=child_id)
        except ChildProfile.DoesNotExist:
            messages.error(request, "Invalid child account")
            return redirect('parent_dashboard')
    return redirect('parent_dashboard')

@login_required
@user_passes_test(is_parent, login_url='/access-denied/')
def delete_child(request, child_id):
    """Delete child account - only accessible to parents"""
    if request.method == 'POST':
        try:
            child_profile = ChildProfile.objects.get(child__id=child_id, parent=request.user)
            child_user = child_profile.child
            username = child_user.username
            child_profile.delete()
            child_user.delete()
            messages.success(request, f"Child account {username} deleted successfully")
        except ChildProfile.DoesNotExist:
            messages.error(request, "Invalid child account")
    
    return redirect('parent_dashboard')









def child_dashboard(request, child_id):
    profile = get_object_or_404(ChildProfile, child_id=child_id)

    if request.user != profile.child and request.user != profile.parent:
        return HttpResponseForbidden("Not authorized.")

    # ✅ Check if evaluation was completed (using session storage)
    evaluation_completed = request.session.pop('evaluation_completed', False)
    dyslexia_type_evaluated = request.session.pop('dyslexia_type_evaluated', '')
    
    # ✅ GET REAL EVALUATION RESULTS FROM SESSION
    evaluation_data = request.session.get('current_evaluation', {})
    score = evaluation_data.get('score', 0)
    total_questions = evaluation_data.get('total_questions', 5)
    percentage = evaluation_data.get('percentage', 0)

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

    # ✅ UPDATED: Use real evaluation results for the modal
    progress_data = {
        "points": 0,
        "completed": score,           # 👈 Real evaluation score
        "total": total_questions,     # 👈 Real total questions
        "percentage": percentage,     # 👈 Real percentage
    }

    return render(request, "accounts/base_child.html", {
        "user": profile.child,
        "child_profile": profile,
        "assigned_type": assigned_type,
        "suggested_type": suggested_type,
        "progress_data": progress_data,
        "modules": modules,
        "lessons": lessons,
        "evaluation_completed": evaluation_completed,
        "dyslexia_type_evaluated": dyslexia_type_evaluated,
        "actual_user": request.user,
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

@login_required

def evaluation_test(request, dyslexia_type):
    # Enhanced question bank with type-specific interactions
    questions_bank = {
        "Phonological dyslexia": [
            {
                "id": 1,
                "text": "Say the word 'cat' aloud and record your pronunciation.",
                "interaction": "speech_recognition",  # Fixed: was "speech_recognition"
                "expected": "cat",
                "hint": "Speak clearly into your microphone"
            },
            {
                "id": 2, 
                "text": "Break the word 'sunset' into individual sounds (phonemes).",
                "interaction": "speech_recognition",  # Changed from "phoneme_segmentation"
                "expected": "s-u-n-s-e-t",
                "hint": "Say each sound separately"
            },
            {
                "id": 3,
                "text": "Which word rhymes with 'bat'? Speak your answer.",
                "interaction": "speech_recognition",  # Changed from "rhyme_recognition"
                "expected": ["cat", "hat", "mat", "rat", "sat"],
                "hint": "Think of words that sound similar at the end"
            },
            {
                "id": 4,
                "text": "Identify the first sound in 'phone'. Record your answer.",
                "interaction": "speech_recognition",  # Changed from "phoneme_identification"
                "expected": "f",
                "hint": "Focus on the beginning sound"
            },
            {
                "id": 5,
                "text": "Blend these sounds together: /s/ /u/ /n/",
                "interaction": "speech_recognition",  # Changed from "sound_blending"
                "expected": "sun",
                "hint": "Say the sounds quickly together"
            }
        ],
        "Surface dyslexia": [
            {
                "id": 1,
                "text": "Read this irregular word aloud: 'yacht'",
                "interaction": "speech_recognition",  # Changed from "word_recognition"
                "expected": "yacht",
                "hint": "Try to recognize the whole word"
            },
            {
                "id": 2,
                "text": "Which spelling is correct? 'friend' or 'frend'?",
                "interaction": "spelling_recognition",
                "expected": "friend",
                "hint": "Think about common spelling patterns"
            },
            {
                "id": 3,
                "text": "Read this sight word quickly: 'the'",
                "interaction": "speech_recognition",  # Changed from "rapid_naming"
                "expected": "the",
                "hint": "Say it as fast as you can"
            },
            {
                "id": 4,
                "text": "Identify the real word: 'knight' or 'nite'?",
                "interaction": "word_authenticity",
                "expected": "knight",
                "hint": "Consider standard English spelling"
            },
            {
                "id": 5,
                "text": "Read this sentence: 'The said was red' - does it make sense?",
                "interaction": "speech_recognition",  # Changed from "context_understanding"
                "expected": "no",
                "hint": "Think about word meaning in context"
            }
        ],
        "Visual dyslexia": [
            {
                "id": 1,
                "text": "Which direction is the letter 'b' facing? Left or right?",
                "interaction": "multiple_choice",  # Changed from "letter_orientation"
                "options": ["Left", "Right"],
                "expected": "right",
                "hint": "Visualize the letter shape"
            },
            {
                "id": 2,
                "text": "Do 'was' and 'saw' look the same or different?",
                "interaction": "multiple_choice",  # Changed from "word_reversal"
                "options": ["Same", "Different"],
                "expected": "different",
                "hint": "Look at the letter order"
            },
            {
                "id": 3,
                "text": "Trace the shape of the word 'elephant' with your finger on screen.",
                "interaction": "visual_tracking",
                "expected": "completed",
                "hint": "Follow the word smoothly"
            },
            {
                "id": 4,
                "text": "Find the letter 'p' among these: q d b p",
                "interaction": "multiple_choice",  # Changed from "visual_search"
                "options": ["1st", "2nd", "3rd", "4th"],
                "expected": "4th",
                "hint": "Scan carefully left to right"
            },
            {
                "id": 5,
                "text": "Which number looks reversed? 3, Ɛ, 5, 8",
                "interaction": "multiple_choice",  # Changed from "number_reversal"
                "options": ["3", "Ɛ", "5", "8"],
                "expected": "Ɛ",
                "hint": "Think about normal number shapes"
            }
        ],
        "Rapid naming deficit": [
            {
                "id": 1,
                "text": "Name these pictures as fast as you can: 🐱 🚗 🌞 🏀",
                "interaction": "rapid_picture_naming",
                "expected": ["cat", "car", "sun", "ball"],
                "timed": True,
                "time_limit": 5,
                "hint": "Say the names quickly without pausing"
            },
            {
                "id": 2,
                "text": "Say the alphabet from A to Z as fast as you can.",
                "interaction": "speech_recognition",  # Changed from "alphabet_naming"
                "expected": "a b c d e f g h i j k l m n o p q r s t u v w x y z",
                "timed": True,
                "time_limit": 10,
                "hint": "Go as fast as you can while being clear"
            },
            {
                "id": 3,
                "text": "Read these colors quickly: RED BLUE GREEN YELLOW",
                "interaction": "color_naming",
                "expected": ["red", "blue", "green", "yellow"],
                "timed": True,
                "time_limit": 4,
                "hint": "Say the color names rapidly"
            },
            {
                "id": 4,
                "text": "Name 5 animals in 3 seconds.",
                "interaction": "speech_recognition",  # Changed from "category_naming"
                "expected": "any_5_animals",
                "timed": True,
                "time_limit": 3,
                "hint": "Think of common animals quickly"
            },
            {
                "id": 5,
                "text": "Read these numbers: 5 8 2 9 1",
                "interaction": "speech_recognition",  # Changed from "number_naming"
                "expected": ["five", "eight", "two", "nine", "one"],
                "timed": True,
                "time_limit": 3,
                "hint": "Say the numbers in order quickly"
            }
        ]
    }

    # Get the question set for this dyslexia type
    questions = questions_bank.get(dyslexia_type, [])
    
    # Debug: Print questions to console
    print(f"Questions for {dyslexia_type}: {questions}")
    
    if request.method == "POST":
        # Process the evaluation results
        responses = {}
        score = 0
        total_questions = len(questions)
        
        # Collect responses and calculate preliminary score
        for question in questions:
            q_id = question['id']
            response = request.POST.get(f'q{q_id}')
            responses[q_id] = response
            
            # Basic scoring logic
            if response and question.get('expected'):
                if isinstance(question['expected'], list):
                    if response.lower() in [str(x).lower() for x in question['expected']]:
                        score += 1
                else:
                    if response.lower() == str(question['expected']).lower():
                        score += 1
        
        # Store evaluation data
        evaluation_data = {
            'dyslexia_type': dyslexia_type,
            'score': score,
            'total_questions': total_questions,
            'percentage': (score / total_questions) * 100 if total_questions > 0 else 0,
            'responses': responses,
            'timestamp': time.time(),
            'user_id': request.user.id
        }
        
        # Store in session
        request.session['current_evaluation'] = evaluation_data
        request.session['evaluation_completed'] = True
        request.session['dyslexia_type_evaluated'] = dyslexia_type
        
        # Get child ID for redirection
        if request.user.role in ["CHILD", "INDEPENDENT"]:
            child_id = request.user.id
        else:
            child_id = request.session.get('current_child_id')
            if not child_id:
                child_profile = ChildProfile.objects.filter(parent=request.user).first()
                if child_profile:
                    child_id = child_profile.child.id
        
        return redirect("child_dashboard", child_id=child_id)
    
    context = {
        "dyslexia_type": dyslexia_type,
        "questions": questions,
    }
    return render(request, "evaluation/static_evaluation.html", context)

# Speech recognition API endpoint
@login_required
def speech_to_text_api(request):
    if request.method == "POST" and request.FILES.get('audio'):
        recognizer = sr.Recognizer()
        audio_file = request.FILES['audio']
        
        try:
            # Save temporary audio file
            with open('temp_audio.wav', 'wb') as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)
            
            # Convert speech to text
            with sr.AudioFile('temp_audio.wav') as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                
            return JsonResponse({'success': True, 'text': text})
            
        except sr.UnknownValueError:
            return JsonResponse({'success': False, 'error': 'Could not understand audio'})
        except sr.RequestError as e:
            return JsonResponse({'success': False, 'error': f'Speech recognition error: {e}'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# Evaluation results page (placeholder for Gemma integration)
@login_required
def evaluation_results(request, child_id):
    evaluation_data = request.session.get('current_evaluation', {})
    child_profile = get_object_or_404(ChildProfile, child_id=child_id)
    
    # Placeholder for Gemma integration - will analyze responses and provide detailed feedback
    severity_levels = {
        80: "Mild",
        60: "Moderate", 
        40: "Significant",
        0: "Severe"
    }
    
    percentage = evaluation_data.get('percentage', 0)
    severity = "Mild"
    for threshold, level in severity_levels.items():
        if percentage >= threshold:
            severity = level
            break
    
    context = {
        'child_profile': child_profile,
        'evaluation_data': evaluation_data,
        'severity': severity,
        'percentage': percentage,
        'dyslexia_type': evaluation_data.get('dyslexia_type', 'Unknown')
    }
    
    return render(request, "evaluation/results.html", context)







