from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django import forms
import json
from django.contrib.auth import get_user_model

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("PARENT", "Parent"),
        ("CHILD", "Child"),
        ("INDEPENDENT", "Independent"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="CHILD")

    def __str__(self):
        return f"{self.username} ({self.role})"


DYSLEXIA_CHOICES = [
    ("General", "General"),
    ("Phonological", "Phonological"),
    ("Visual", "Visual"),
    ("Surface", "Surface"),
    ("Rapid Naming", "Rapid Naming"),
    ("Double Deficit", "Double Deficit"),
    ("Other", "Other"),
]


class ChildProfile(models.Model):
    child = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="children_profiles",
        null=True, blank=True  # ✅ Independent users don’t need a parent
    )
    dyslexia_type = models.CharField(
        max_length=50,
        choices=DYSLEXIA_CHOICES,
        null=True, blank=True   # ✅ allow empty until chosen
    )

    def __str__(self):
        if self.parent:
            return f"{self.child.username} (Child of {self.parent.username})"
        return f"{self.child.username} (Independent)"


class DyslexiaTypeForm(forms.ModelForm):
    class Meta:
        model = ChildProfile
        fields = ["dyslexia_type"]
        
        CustomUser = get_user_model()

class EvaluationData(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    child_profile = models.ForeignKey('ChildProfile', on_delete=models.CASCADE, null=True, blank=True)
    dyslexia_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)


    
    # TTS Interaction Data
    tts_usage_count = models.IntegerField(default=0)
    tts_questions_used = models.JSONField(default=list)
    
    # STT Response Data
    stt_responses = models.JSONField(default=dict)
    stt_accuracy = models.FloatField(default=0.0)
    
    # Timing and Performance Metrics
    response_times = models.JSONField(default=dict)
    completion_time = models.FloatField(default=0.0)
    
    # Evaluation Results
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    
    # Additional ML Features
    speech_fluency_metrics = models.JSONField(default=dict)
    error_patterns = models.JSONField(default=list)

    def __str__(self):
        return f"{self.user.username} - {self.dyslexia_type} - {self.timestamp}"

    class Meta:
        db_table = 'evaluation_data'