from django.db import models
from django.conf import settings

DYSLEXIA_TYPES = [
    ("Developmental", "Developmental"),
    ("Acquired", "Acquired"),
    ("Phonological", "Phonological"),
    ("Surface", "Surface"),
    ("Rapid naming deficit", "Rapid naming deficit"),
    ("Visual", "Visual"),
]

class Lesson(models.Model):
    title = models.CharField(max_length=200)
    # Core reading content (shown and read aloud by TTS)
    content_text = models.TextField()

    # Optional media (you can upload via admin later)
    image = models.ImageField(upload_to="lessons/images/", blank=True, null=True)

    # Tag lesson for adaptive filtering
    dyslexia_type = models.CharField(max_length=40, choices=DYSLEXIA_TYPES, default="Developmental")

    # Small, multiple-choice activity (keep it simple for now)
    prompt = models.CharField(max_length=255, blank=True, default="")
    choice_a = models.CharField(max_length=120, blank=True, default="")
    choice_b = models.CharField(max_length=120, blank=True, default="")
    choice_c = models.CharField(max_length=120, blank=True, default="")
    correct_choice = models.CharField(max_length=1, blank=True, default="")  # "A" | "B" | "C"

    # Difficulty could help future adaptivity
    level = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["level", "title"]

    def __str__(self):
        return self.title


class Attempt(models.Model):
    # store who answered (we’ll store the *user* id; if your child user is CustomUser this is fine)
    child = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_attempts")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="attempts")

    # what they answered and result
    selected_choice = models.CharField(max_length=1, blank=True, default="")
    is_correct = models.BooleanField(default=False)

    # lightweight telemetry for your future ML
    time_spent_ms = models.PositiveIntegerField(default=0)     # client can post how long they took
    tts_plays = models.PositiveIntegerField(default=0)         # client increments when pressing speaker
    repeats = models.PositiveIntegerField(default=0)           # repeat/try-again counts

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
