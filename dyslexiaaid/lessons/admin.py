from django.contrib import admin
from .models import DyslexiaType, Lesson, Attempt, Module


# DyslexiaType Admin
@admin.register(DyslexiaType)
class DyslexiaTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "get_dyslexia_types", "created_at")
    search_fields = ("name", "description")
    filter_horizontal = ("dyslexia_types",)  # allows easy multi-select
    ordering = ("name",)

    def get_dyslexia_types(self, obj):
        return ", ".join([dt.name for dt in obj.dyslexia_types.all()])
    get_dyslexia_types.short_description = "Dyslexia Types"


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "dyslexia_type", "level", "created_at")
    search_fields = ("title", "content_text", "prompt", "choice_a", "choice_b", "choice_c")
    list_filter = ("module", "dyslexia_type", "level")
    ordering = ("level", "title")

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("child", "lesson", "selected_choice", "is_correct", "created_at")
    list_filter = ("is_correct", "lesson__module", "lesson__dyslexia_type")
    ordering = ("-created_at",)
