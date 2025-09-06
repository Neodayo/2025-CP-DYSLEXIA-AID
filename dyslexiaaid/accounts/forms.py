from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, ChildProfile , DYSLEXIA_CHOICES

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

class IndependentRegisterForm(UserCreationForm):

    dyslexia_type = forms.ChoiceField(
        choices=DYSLEXIA_CHOICES,
        required=True,
        label="Select Dyslexia Type"
    )
    class Meta:
        model = CustomUser
        fields = ("username", "email", "password1", "password2")



class DyslexiaTypeForm(forms.ModelForm):
    class Meta:
        model = ChildProfile
        fields = ['dyslexia_type']
        widgets = {
            'dyslexia_type': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'dyslexia_type': 'Select Dyslexia Type',
        }

        