from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid
from django.core.validators import FileExtensionValidator

class BaseModel(models.Model):
    created_datetime = models.DateTimeField(auto_now_add=True)
    modified_datetime = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Collection(BaseModel):
    name = models.CharField(max_length=1024, blank=True, null=True)

    def __str__(self):
        return f"{self.name}"


class Player(BaseModel):
    name = models.CharField(max_length=255, db_index=True)
    password = models.CharField(max_length=255)
    last_login_datetime = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('text', _('Text')),
        ('audio', _('Audio')),
        ('video', _('Video')),
        ('photo', _('Photo')),
    ]

    collection = models.ForeignKey("Collection", on_delete=models.SET_NULL, null=True, blank=True)
    text = models.CharField(max_length=2048, blank=True)
    order = models.PositiveIntegerField(default=0, blank=False, null=False)
    answer1 = models.CharField(max_length=2048, blank=True)
    answer2 = models.CharField(max_length=2048, blank=True)
    answer3 = models.CharField(max_length=2048, blank=True)
    answer4 = models.CharField(max_length=2048, blank=True)
    correct = models.IntegerField(choices=[(i + 1, f"#{i + 1}") for i in range(4)], blank=True)
    
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='text')
    audio_file = models.FileField(
        upload_to='audio_questions/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav'])]
    )
    video_file = models.FileField(
        upload_to='video_questions/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'webm'])]
    )
    photo_file = models.ImageField(
        upload_to='photo_questions/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Question #{self.order} ({self.get_question_type_display()})"

    def save(self, *args, **kwargs):
        old_type = self.__class__.objects.filter(pk=self.pk).values_list('question_type', flat=True).first() if self.pk else None

        if self.photo_file:
            new_type = 'photo'
        elif self.video_file:
            new_type = 'video'
        elif self.audio_file:
            new_type = 'audio'
        elif self.text:
            new_type = 'text'
        else:
            new_type = 'text'

        if old_type and old_type != new_type:
            if new_type == 'photo':
                self.audio_file = None
                self.video_file = None
            elif new_type == 'video':
                self.audio_file = None
                self.photo_file = None
            elif new_type == 'audio':
                self.video_file = None
                self.photo_file = None
            elif new_type == 'text':
                self.audio_file = None
                self.video_file = None
                self.photo_file = None

        self.question_type = new_type
        super().save(*args, **kwargs)



class Game(BaseModel):
    collection = models.ForeignKey("Collection", on_delete=models.CASCADE)
    player = models.ForeignKey("Player", on_delete=models.CASCADE)
    finished = models.BooleanField(default=False)

    def __str__(self):
        return self.collection.name


class QuestionAnswer(BaseModel):
    game = models.ForeignKey("Game", on_delete=models.CASCADE)
    question = models.ForeignKey("Question", on_delete=models.CASCADE)
    correct = models.BooleanField(default=False)