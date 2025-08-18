from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, ChildProfile

class ParentRegisterForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ["username", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "PARENT"
        if commit:
            user.save()
        return user


class ChildRegisterForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ["username", "email", "password1", "password2"]

    def save(self, parent_user=None, commit=True):
        user = super().save(commit=False)
        user.role = "CHILD"
        if commit:
            user.save()
            if parent_user and parent_user.role == "PARENT":
                ChildProfile.objects.create(parent=parent_user, child=user)
        return user
