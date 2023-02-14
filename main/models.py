import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


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


class Question(BaseModel):
    collection = models.ForeignKey("Collection", on_delete=models.SET_NULL, null=True, blank=True)
    text = models.CharField(max_length=2048)
    order = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False,
    )
    answer1 = models.CharField(max_length=2048)
    answer2 = models.CharField(max_length=2048)
    answer3 = models.CharField(max_length=2048)
    answer4 = models.CharField(max_length=2048)
    correct = models.IntegerField(choices=[(i + 1, f"#{i + 1}") for i in range(4)])

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Question #{self.order}"


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
