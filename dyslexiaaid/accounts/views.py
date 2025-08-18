from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from .forms import ParentRegisterForm, ChildRegisterForm

def parent_register(request):
    if request.method == "POST":
        form = ParentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # auto-login
            return redirect("parent_dashboard")
    else:
        form = ParentRegisterForm()
    return render(request, "accounts/parent_register.html", {"form": form})

@login_required
def child_register(request):
    if request.user.role != "PARENT":
        return HttpResponseForbidden("Only parents can register children.")
    if request.method == "POST":
        form = ChildRegisterForm(request.POST)
        if form.is_valid():
            form.save(parent_user=request.user)
            return redirect("parent_dashboard")
    else:
        form = ChildRegisterForm()
    return render(request, "accounts/child_register.html", {"form": form})

@login_required
def parent_dashboard(request):
    if request.user.role != "PARENT":
        return redirect("login")
    children = request.user.children.select_related("child").all()
    return render(request, "accounts/parent_dashboard.html", {"children": children})



def home(request):
    if request.user.is_authenticated and request.user.role == "PARENT":
        return redirect("parent_dashboard")
    return render(request, "accounts/home.html")