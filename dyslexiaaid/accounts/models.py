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
