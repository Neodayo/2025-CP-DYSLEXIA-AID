from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("PARENT", "Parent"),
        ("CHILD", "Non-Parent"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="CHILD")

class ChildProfile(models.Model):
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="children")
    child = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="child_profile")

    def __str__(self):
        return f"{self.child.username} (Child of {self.parent.username})"

from django.db import models
from django.conf import settings

class ChildProfile(models.Model):
    child = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="profile"
    )
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="children_profiles"
    )
    dyslexia_type = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.child.username}'s Profile"
