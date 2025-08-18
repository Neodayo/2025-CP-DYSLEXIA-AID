from django.urls import path
from . import views

urlpatterns = [
    # make thi direct to expected landingg pagee plss
    path("", views.home, name="home"),

    # Parent registration
    path("register/parent/", views.parent_register, name="parent_register"),

    # Child registration (only parent can access)
    path("register/child/", views.child_register, name="child_register"),

    # Parent dashboard
    path("dashboard/parent/", views.parent_dashboard, name="parent_dashboard"),
]
