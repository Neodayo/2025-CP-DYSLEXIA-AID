# views.py - ORIGINAL COMMENTS PRESERVED + NEW DATA COLLECTION
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
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

# NEW: Import the EvaluationData model
from .models import EvaluationData
import numpy as np  # NEW: For data export functionality



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

    # ❌ Don't redirect to login again (causes loop)
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
    questions_bank = {
        "Phonological dyslexia": [
            {
                "id": 1,
                "text": "Say the word 'cat' aloud and record your pronunciation.",
                "interaction": "speech_recognition",
                "expected": "cat",
                "hint": "Speak clearly into your microphone"
            },
            {
                "id": 2, 
                "text": "Break the word 'sun' into individual sounds (phonemes).",
                "interaction": "speech_recognition",
                "expected": "s u n",
                "hint": "Say each sound separately: s - u - n"
            },
            {
                "id": 3,
                "text": "Which word rhymes with 'bat'? Choose one.",
                "interaction": "multiple_choice",
                "options": ["cat", "bed", "book", "run"],
                "expected": "cat",
                "hint": "Think of words that sound similar at the end"
            },
            {
                "id": 4,
                "text": "What is the first sound you hear in 'fish'?",
                "interaction": "multiple_choice",
                "options": ["f", "sh", "i", "h"],
                "expected": "f",
                "hint": "Focus on the beginning sound"
            },
            {
                "id": 5,
                "text": "Blend these sounds together: /b/ /a/ /t/",
                "interaction": "speech_recognition",
                "expected": "bat",
                "hint": "Say the sounds quickly together: b-a-t"
            }
        ],
        "Surface dyslexia": [
            {
                "id": 1,
                "text": "Read this word aloud: 'yacht'",
                "interaction": "speech_recognition",
                "expected": "yacht",
                "hint": "Try to recognize the whole word"
            },
            {
                "id": 2,
                "text": "Which spelling is correct?",
                "interaction": "multiple_choice",
                "options": ["friend", "frend"],
                "expected": "friend",
                "hint": "Think about common spelling patterns"
            },
            {
                "id": 3,
                "text": "Read this sight word: 'the'",
                "interaction": "speech_recognition",
                "expected": "the",
                "hint": "Say it naturally"
            },
            {
                "id": 4,
                "text": "Which word is spelled correctly?",
                "interaction": "multiple_choice",
                "options": ["knight", "nite"],
                "expected": "knight",
                "hint": "Consider standard English spelling"
            },
            {
                "id": 5,
                "text": "Does this sentence make sense? 'The cat sat on the mat.'",
                "interaction": "multiple_choice",
                "options": ["Yes", "No"],
                "expected": "Yes",
                "hint": "Think about word meaning in context"
            }
        ],
        "Visual dyslexia": [
            {
                "id": 1,
                "text": "Which letter is different? b d p q",
                "interaction": "multiple_choice",
                "options": ["b", "d", "p", "q"],
                "expected": "q",
                "hint": "Look carefully at each letter shape"
            },
            {
                "id": 2,
                "text": "Do these words look the same? 'was' and 'saw'",
                "interaction": "multiple_choice",
                "options": ["Yes", "No"],
                "expected": "No",
                "hint": "Look at the letter order"
            },
            {
                "id": 3,
                "text": "Find the matching shapes: circle circle square triangle",
                "interaction": "multiple_choice",
                "options": ["1st and 2nd", "2nd and 3rd", "3rd and 4th", "All different"],
                "expected": "1st and 2nd",
                "hint": "Look for identical shapes"
            },
            {
                "id": 4,
                "text": "Which word has no reversed letters?",
                "interaction": "multiple_choice",
                "options": ["bog", "dog", "qog", "pog"],
                "expected": "dog",
                "hint": "Look for normally oriented letters"
            },
            {
                "id": 5,
                "text": "Which number looks normal?",
                "interaction": "multiple_choice",
                "options": ["2", "5", "Ɛ", "7"],
                "expected": "7",
                "hint": "Think about normal number shapes"
            }
        ],
        "Rapid naming deficit": [
            {
                "id": 1,
                "text": "Name these colors: red yellow blue green",
                "interaction": "speech_recognition",
                "expected": ["red", "yellow", "blue", "green"],
                "timed": True,
                "time_limit": 8,
                "hint": "Say the color names in order"
            },
            {
                "id": 2,
                "text": "Say the days of the week starting from Monday",
                "interaction": "speech_recognition",
                "expected": "monday tuesday wednesday thursday friday saturday sunday",
                "timed": True,
                "time_limit": 10,
                "hint": "Go as fast as you can while being clear"
            },
            {
                "id": 3,
                "text": "Name these shapes: star heart diamond club",
                "interaction": "speech_recognition",
                "expected": ["star", "heart", "diamond", "club"],
                "timed": True,
                "time_limit": 6,
                "hint": "Say the shape names in order"
            },
            {
                "id": 4,
                "text": "Count from 1 to 10",
                "interaction": "speech_recognition",
                "expected": "one two three four five six seven eight nine ten",
                "timed": True,
                "time_limit": 8,
                "hint": "Say the numbers in order quickly"
            },
            {
                "id": 5,
                "text": "Name these animals: dog cat mouse rabbit",
                "interaction": "speech_recognition",
                "expected": ["dog", "cat", "mouse", "rabbit"],
                "timed": True,
                "time_limit": 6,
                "hint": "Say the animal names rapidly"
            }
        ]
    }

    questions = questions_bank.get(dyslexia_type, [])
    
    if request.method == "POST":
        # NEW: Process the collected interaction data
        tts_usage = json.loads(request.POST.get('tts_usage', '[]'))
        response_times = json.loads(request.POST.get('response_times', '{}'))
        start_time = float(request.POST.get('start_time', time.time()))
        completion_time = time.time() - start_time
        
        # Process the evaluation results
        responses = {}
        score = 0
        total_questions = len(questions)
        
        # NEW: Collect STT response data for ML training
        stt_responses_data = {}
        
        # Collect responses and calculate score
        for question in questions:
            q_id = question['id']
            response = request.POST.get(f'q{q_id}', '').strip().lower()
            responses[q_id] = response
            
            # NEW: Capture detailed STT response data
            stt_responses_data[str(q_id)] = {
                'response': response,
                'expected': question.get('expected', ''),
                'question_type': question['interaction'],
                'processing_time': response_times.get(str(q_id), 0),
                'used_tts': q_id in tts_usage  # Track if TTS was used for this question
            }
            
            # Enhanced scoring logic
            if response and question.get('expected'):
                expected = question['expected']
                
                # Handle different question types
                if question.get('timed', False):
                    # For timed exercises, check if they attempted it
                    if response and response != 'no_response':
                        score += 1
                
                elif question['id'] == 4 and dyslexia_type == "Rapid naming deficit":
                    # "Count from 1 to 10" - check if they said most numbers
                    numbers = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
                    said_numbers = [num for num in numbers if num in response]
                    if len(said_numbers) >= 8:  # At least 8 out of 10 numbers
                        score += 1
                
                elif question['id'] == 2 and dyslexia_type == "Rapid naming deficit":
                    # "Days of the week" - check if they said most days
                    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    said_days = [day for day in days if day in response]
                    if len(said_days) >= 5:  # At least 5 out of 7 days
                        score += 1
                
                elif isinstance(expected, list):
                    # Check if response matches any expected value
                    if any(exp.lower() in response or response in exp.lower() for exp in expected):
                        score += 1
                
                else:
                    # Exact match or contains check for speech responses
                    expected_str = str(expected).lower()
                    if (response == expected_str or 
                        expected_str in response or 
                        response in expected_str):
                        score += 1
        
        # NEW: Calculate STT accuracy for ML features
        stt_accuracy = (score / total_questions) * 100 if total_questions > 0 else 0
        
        # NEW: Create EvaluationData record for ANN training
        evaluation_data_record = EvaluationData(
            user=request.user,
            dyslexia_type=dyslexia_type,
            tts_usage_count=len(tts_usage),
            tts_questions_used=tts_usage,
            stt_responses=stt_responses_data,
            stt_accuracy=stt_accuracy,
            response_times=response_times,
            completion_time=completion_time,
            score=score,
            total_questions=total_questions,
            percentage=(score / total_questions) * 100 if total_questions > 0 else 0
        )
        
        # NEW: Add child profile for child users
        if request.user.role in ["CHILD", "INDEPENDENT"]:
            try:
                child_profile = ChildProfile.objects.get(child=request.user)
                evaluation_data_record.child_profile = child_profile
            except ChildProfile.DoesNotExist:
                pass
        else:
            child_id = request.session.get('current_child_id')
            if child_id:
                try:
                    child_profile = ChildProfile.objects.get(child_id=child_id)
                    evaluation_data_record.child_profile = child_profile
                except ChildProfile.DoesNotExist:
                    pass
        
        # NEW: Save the comprehensive evaluation data
        evaluation_data_record.save()
        
        # Store evaluation data in session (original functionality preserved)
        evaluation_data = {
            'dyslexia_type': dyslexia_type,
            'score': score,
            'total_questions': total_questions,
            'percentage': evaluation_data_record.percentage,
            'data_id': evaluation_data_record.id  # NEW: Store the data record ID
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
    
    # For GET requests, store start time for timing the evaluation
    request.session['evaluation_start_time'] = time.time()
    
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

# NEW: Data export for ANN training
@login_required
def export_training_data(request):
    """Export all evaluation data as CSV for ANN model training"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Admin access required")
    
    evaluations = EvaluationData.objects.all()
    
    data = []
    for eval in evaluations:
        row = {
            'user_id': eval.user.id,
            'dyslexia_type': eval.dyslexia_type,
            'age': getattr(eval.user, 'age', None),
            
            # TTS Features
            'tts_usage_count': eval.tts_usage_count,
            'tts_questions_used_count': len(eval.tts_questions_used),
            
            # STT Features
            'stt_accuracy': eval.stt_accuracy,
            'total_responses': len(eval.stt_responses),
            'empty_responses': sum(1 for r in eval.stt_responses.values() if not r.get('response')),
            
            # Timing Features
            'completion_time': eval.completion_time,
            'avg_response_time': np.mean(list(eval.response_times.values())) if eval.response_times else 0,
            
            # Performance Features
            'score': eval.score,
            'percentage': eval.percentage,
            
            # Derived Features
            'uses_tts_frequently': 1 if eval.tts_usage_count > 2 else 0,
            'slow_responder': 1 if eval.completion_time > 300 else 0,  # >5 minutes
        }
        
        # Add question-specific features
        for q_id, response_data in eval.stt_responses.items():
            row[f'q{q_id}_response_length'] = len(response_data.get('response', ''))
            row[f'q{q_id}_processing_time'] = response_data.get('processing_time', 0)
            row[f'q{q_id}_used_tts'] = 1 if response_data.get('used_tts', False) else 0
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Export to CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dyslexia_training_data.csv"'
    df.to_csv(response, index=False)
    
    return response

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