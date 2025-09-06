from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django import forms


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