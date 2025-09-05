from django.contrib import admin
from .models import Lesson, Attempt

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "dyslexia_type", "level")
    search_fields = ("title", "content_text")
    list_filter = ("dyslexia_type", "level")

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("child", "lesson", "selected_choice", "is_correct", "created_at")
    list_filter = ("is_correct", "lesson__dyslexia_type")
