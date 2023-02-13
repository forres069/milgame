import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q
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
            "fields": {"type": "Fields", "fields": [
                {"type": "TextField", "k": "name", "label": _("name").capitalize()},
                {"type": "TextField", "k": "password", "label": _("password").capitalize(), "subtype": "password"},
            ]},
            "submitButtonWidget": "WelcomeSubmit",
        }

    def post(self, request, *args, **kwargs):
        if not self.player:
            data = json.loads(request.body)["data"]
            player, created = models.Player.objects.get_or_create(**data)
            request.session["PLAYER_ID"] = player.pk
        return JsonResponse({"navigate": "/", "notification": {"type": "success", "text": _("Logged in")}})


class HomeView(MainView):
    url_name = "home"
    url_path = "/"
    WRAPPER = "MainWrapper"
    TEMPLATE = "HomeView"
    title = "Home"

    def get_data(self, request, *args, **kwargs):
        if not self.player:
            return {"navigate": "/welcome/"}
        return {
            **super().get_data(request, *args, **kwargs),
            "items": list(models.Collection.objects.values("name", "pk"))
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


"""
class SimpleGameView(MainView):
    url_name = "home"
    url_path = "/simple-game/<:id>/"
    WRAPPER = "MainWrapper"
    TEMPLATE = None
    title = "Welcome to the game"

    def get_fields(self):
        return {
            "type": "Fields",
            "fields": [
                {"from_field": "name"},
            ],
        }

    def get_obj(self):
        game = models.Game.objects.filter(uuid=self.kwargs["uuid"]).first()
        return models.Player(
            game=game,
        )

    def get_data(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return {"navigate": "/welcome/"}
        # Cleanup
        if "GAME_STATE" in request.session:
            del request.session["GAME_STATE"]
        game = models.Game.objects.filter(uuid=self.kwargs["uuid"]).first()
        print("state", state)
        if not game:
            return {"template": "PageNotFound"}
        now = timezone.now()
        if game.start_datetime > now:
            return {
                "template": "GameWillStart",
                "name": game.name,
                "start_datetime": game.start_datetime,
            }
        if game.end_datetime < now:
            return {
                "template": "GameEnded",
                "name": game.name,
                "end_datetime": game.end_datetime,
            }
        # Game is normal
        player = models.Player.objects.filter(
            pk=state.get(str(game.uuid), None)
        ).first()
        if not player:
            return {
                "title": _("Please enter your name"),
                "template": "GenericForm",
                **read_fields(
                    self.get_fields(),
                    self.get_obj(),
                ),
                "submitButtonWidget": "GameSubmit",
            }
        answered_ids = player.questionanswer_set.values_list("question_id", flat=True)
        unanswered = (
            game.collection.question_set.filter(~Q(pk__in=answered_ids))
            .order_by("order")
            .values("pk", "text", "answer1", "answer2", "answer3", "answer4")
        )
        if unanswered:
            total = game.collection.question_set.count()
            return {
                "template": "Game",
                "player_name": player.name,
                "name": game.name,
                "end_datetime": game.end_datetime,
                "index": total - unanswered.count() + 1,
                "total": total,
                **unanswered.first(),
            }
        else:
            return {
                "template": "GameFinish",
                "player_name": player.name,
                "name": game.name,
                "end_datetime": game.end_datetime,
            }

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return HttpResponse("Unauthorized", status=401)
        lang = "/" + request.LANGUAGE_CODE if request.LANGUAGE_CODE != "en" else ""
        state = json.loads(request.session.get("GAME_STATE", "{}"))
        game = models.Game.objects.filter(uuid=self.kwargs["uuid"]).first()
        if not game:
            return {}
        now = timezone.now()
        if game.start_datetime > now:
            return {}
        if game.end_datetime < now:
            return {}
        # Game is normal
        player = models.Player.objects.filter(
            pk=state.get(str(game.uuid), None)
        ).first()
        if not player:
            player = write_fields(
                self.get_fields(), self.get_obj(), json.loads(request.body)["data"]
            )
            state[str(game.uuid)] = player.pk
            request.session["GAME_STATE"] = json.dumps(state)
        else:
            data = json.loads(request.body)["data"]
            print(data)
            answered_ids = player.questionanswer_set.values_list(
                "question_id", flat=True
            )
            unanswered = (
                game.collection.question_set.filter(~Q(pk__in=answered_ids))
                .filter(pk=data["questionId"])
                .values("pk", "correct")
                .first()
            )
            if unanswered:
                models.QuestionAnswer.objects.create(
                    player=player,
                    question_id=unanswered["pk"],
                    correct=unanswered["correct"] == data["answer"]
                )
        return JsonResponse({"navigate": f"{lang}/game/{game.uuid}/"})
"""


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
