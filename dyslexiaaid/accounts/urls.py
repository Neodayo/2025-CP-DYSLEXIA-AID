from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # make thi direct to expected landingg pagee plss
    path("", views.landing_page, name="home"),

    # Parent registration
    path("register/parent/", views.parent_register, name="parent_register"),

    # Child registration (only parent can access)
    path("register/child/", views.child_register, name="child_register"),

    path("register/independent/", views.independent_register, name="independent_register"),

    # Parent dashboard
    path("dashboard/parent/", views.parent_dashboard, name="parent_dashboard"),
    path('delete-child/<int:child_id>/', views.delete_child, name='delete_child'), 
    path('switch-to-child/<int:child_id>/', views.switch_to_child, name='switch_to_child'), # for logging in child in parent dashboard


    #Child Dashboard
    path("dashboard/child/<int:child_id>/", views.child_dashboard, name="child_dashboard"),
    path("dashboard/child/<int:child_id>/", views.child_home, name="child_home"),
    path("dashboard/child/<int:child_id>/profile/", views.child_profile, name="child_profile"),
    path("dashboard/child/<int:child_id>/progress/", views.child_progress, name="child_progress"),

    # New: Introduction and Dyslexia Type Selection
    path("child/<int:child_id>/introduction/", views.introduction, name="introduction"),
    # path("child/<int:child_id>/type-selection/", views.type_selection, name="type_selection"),
    path("child/<int:child_id>/edit/", views.edit_child_profile, name="edit_child_profile"),

    path('type-selection/<int:child_id>/', views.dyslexia_type_selection, name='dyslexia_type_selection'),

    path('logout/', views.custom_logout, name='logout'),
    path('redirect-after-login/', views.login_redirect, name='login_redirect'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),

     path("about/", views.about_us, name="about_us"),

    path("select-type/<int:child_id>/", views.dyslexia_type_selection, name="dyslexia_type_selection"),
    path("test/<str:dyslexia_type>/", views.evaluation_test, name="evaluation_test"),
    # path("evaluation/result/<int:evaluation_id>/", views.evaluation_result, name="evaluation_result"),
]   
