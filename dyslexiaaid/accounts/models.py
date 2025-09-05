from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("PARENT", "Parent"),
        ("CHILD", "Non-Parent"),
        ("INDEPENDENT", "Independent"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="CHILD")

class ChildProfile(models.Model):
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="children")
    child = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="child_profile")

    def __str__(self):
        return f"{self.child.username} (Child of {self.parent.username})"

from django.db import models
from django.conf import settings

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
        null=True, blank=True  # ✅ parent is optional now
    )
    dyslexia_type = models.CharField(max_length=50, choices=DYSLEXIA_CHOICES, default="General")

    def __str__(self):
        return f"{self.child.username}'s Profile"

