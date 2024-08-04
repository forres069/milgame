import json
from django.contrib.postgres.aggregates import ArrayAgg
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q, Max
from django.utils.decorators import method_decorator
from logicore_django_react_pages.views import ApiView, JsonResponse
from .framework import read_fields, write_fields
from django.utils import timezone
from . import models
from django.utils.translation import gettext_lazy as _


class MainView(ApiView):
    def dispatch(self, request, *args, **kwargs):
        self.player = None
        player_id = request.session.get("PLAYER_ID", None)
        if player_id:
            self.player = models.Player.objects.filter(pk=int(player_id)).first()
        return super().dispatch(request, *args, **kwargs)

    def get_data(self, request, *args, **kwargs):
        return {"player_name": self.player.name if self.player else None}


class Error404ApiView(MainView):
    in_menu = False
    url_path = "/404"
    title = "Error: Page not found"
    WRAPPER = "MainWrapper"
    TEMPLATE = "PageNotFound"

    def get_data(self, request, *args, **kwargs):
        return {}


class WelcomeView(MainView):
    url_name = "home"
    url_path = "/welcome/"
    WRAPPER = "MainWrapper"
    TEMPLATE = "WelcomeView"
    title = "Home"

    def get_data(self, request, *args, **kwargs):
        return {
            **super().get_data(request, *args, **kwargs),
            "fields": {
                "type": "Fields",
                "fields": [
                    {"type": "TextField", "k": "name", "label": _("name").capitalize()},
                    {
                        "type": "TextField",
                        "k": "password",
                        "label": _("password").capitalize(),
                        "subtype": "password",
                    },
                ],
            },
            "submitButtonWidget": "WelcomeSubmit",
        }

    def post(self, request, *args, **kwargs):
        if not self.player:
            data = json.loads(request.body)["data"]
            player, created = models.Player.objects.get_or_create(**data)
            request.session["PLAYER_ID"] = player.pk
        return JsonResponse(
            {
                "navigate": "/",
                "notification": {"type": "success", "text": _("Logged in")},
            }
        )


class HomeView(MainView):
    url_name = "home"
    url_path = "/"
    WRAPPER = "MainWrapper"
    TEMPLATE = "HomeView"
    title = "Home"

    def get_data(self, request, *args, **kwargs):
        if not self.player:
            return {"navigate": "/welcome/"}

        games_started = dict(
            models.Game.objects.filter(player=self.player)
            .annotate(last_start=Max("created_datetime"))
            .values_list("collection_id", "last_start")
        )
        my_games = []
        other_games = []
        qs = models.Collection.objects.values(
            "name",
            "pk",
        )
        for item in qs:
            last_start = games_started.get(item["pk"])
            if last_start:
                my_games.append({**item, "last_start": last_start})
            else:
                other_games.append(item)
        return {
            **super().get_data(request, *args, **kwargs),
            "my_games": list(my_games),
            "other_games": list(other_games),
        }


class LogoutView(MainView):
    url_name = "home"
    url_path = "/logout/"
    WRAPPER = "MainWrapper"
    TEMPLATE = "HomeView"
    title = "Home"

    def get_data(self, request, *args, **kwargs):
        if request.session.get("PLAYER_ID", None):
            del request.session["PLAYER_ID"]
        return {"navigate": "/welcome/"}


class SimpleGameView(MainView):
    url_name = "home"
    url_path = "/simple-game/<int:id>/"
    WRAPPER = "MainWrapper"
    TEMPLATE = None
    title = "Welcome to the game"

    def get_data(self, request, *args, **kwargs):
        if not self.player:
            return {"navigate": "/welcome/"}
        
        if "GAME_STATE" in request.session:
            del request.session["GAME_STATE"]
        
        collection = models.Collection.objects.filter(id=self.kwargs["id"]).first()
        if not collection:
            return {"template": "PageNotFound"}
        
        try:
            game = models.Game.objects.get(
                player=self.player,
                collection=collection,
                finished=False,
            )
        except models.Game.DoesNotExist:
            game = models.Game.objects.create(
                player=self.player,
                collection=collection,
                finished=False,
            )

        answered_ids = game.questionanswer_set.values_list("question_id", flat=True)
        unanswered = (
            collection.question_set.filter(~Q(pk__in=answered_ids))
            .order_by("order")
        )
        
        if unanswered.exists():
            question = unanswered.first()
            total = collection.question_set.count()
            data = {
                "template": "Game",
                "player_name": self.player.name,
                "name": collection.name,
                "index": total - unanswered.count() + 1,
                "total": total,
                "pk": question.pk,
                "text": question.text,
                "answer1": question.answer1,
                "answer2": question.answer2,
                "answer3": question.answer3,
                "answer4": question.answer4,
                "question_type": question.question_type,
                "photo_file": request.build_absolute_uri(question.photo_file.url) if question.photo_file else None,
                "audio_file": request.build_absolute_uri(question.audio_file.url) if question.audio_file else None,
                "video_file": request.build_absolute_uri(question.video_file.url) if question.video_file else None,
            }
            
            return data
        else:
            return {
                "template": "GameResults",
                "player_name": self.player.name,
                "name": collection.name,
            }

    def post(self, request, *args, **kwargs):
        if not self.player:
            return HttpResponse("Unauthorized", status=401)
        lang = "/" + request.LANGUAGE_CODE if request.LANGUAGE_CODE != "en" else ""

        collection = models.Collection.objects.filter(id=self.kwargs["id"]).first()
        if not collection:
            return HttpResponse("Not found", status=404)
        try:
            game = models.Game.objects.get(
                player=self.player,
                collection=collection,
                finished=False,
            )
        except models.Game.DoesNotExist:
            return HttpResponse("Game wasn't started", status=400)
        # Game is normal
        data = json.loads(request.body)["data"]
        answered_ids = game.questionanswer_set.values_list("question_id", flat=True)
        unanswered = (
            collection.question_set.filter(~Q(pk__in=answered_ids), pk=data["questionId"])
            .order_by("order")
            .values("pk", "text", "answer1", "answer2", "answer3", "answer4", "correct")
            .first()
        )
        if unanswered:
            correct = unanswered["correct"] == data["answer"]
            models.QuestionAnswer.objects.create(
                game=game,
                question_id=unanswered["pk"],
                correct=correct,
            )
            return JsonResponse({
                "navigate_url": f"{lang}/simple-game/{collection.id}/",
                "action": "highlightCorrect",
                "correctAnswer": unanswered["correct"],
            })
        return JsonResponse({
            "navigate": f"{lang}/simple-game/{collection.id}/",
        })


@method_decorator(csrf_exempt, name="dispatch")
class LoadFromBibleView(ApiView):
    url_name = "load-from-bible"
    url_path = "/load-from-bible-0d66a7dd-a69d-4a8d-ae59-7b379ceb9c12/"

    def get_data(self, request, *args, **kwargs):
        return {}

    def post(self, request, *args, **kwargs):
        # curl -XPOST http://127.0.0.1:8000/api/load-from-bible-0d66a7dd-a69d-4a8d-ae59-7b379ceb9c12/ -d'{"name": "test1", "question": [{"order": 1, "text": "one", "answer1": "two", "answer2": "three", "answer3": "four", "answer4": "five", "correct": 3}]}'
        obj = write_fields(
            {
                "type": "Fields",
                "fields": [
                    {"from_field": "name"},
                    {
                        "type": "ForeignKeyListField",
                        "k": "question",
                        "fields": [
                            {"from_field": "id"},
                            {"from_field": "text"},
                            {"from_field": "answer1"},
                            {"from_field": "answer2"},
                            {"from_field": "answer3"},
                            {"from_field": "answer4"},
                            {"from_field": "correct"},
                            {"from_field": "order"},
                        ],
                    },
                ],
            },
            models.Collection(),
            json.loads(request.body),
        )
        return JsonResponse({"id": obj.id})