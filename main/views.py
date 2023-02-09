import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from logicore_django_react_pages.views import ApiView
from .framework import write_fields
from django.http import JsonResponse
from . import models


class Error404ApiView(ApiView):
    in_menu = False
    url_path = "/404"
    title = "Error: Page not found"
    WRAPPER = "MainWrapper"
    TEMPLATE = "PageNotFound"

    def get_data(self, request, *args, **kwargs):
        return {}


class HomeView(ApiView):
    url_name = "home"
    url_path = "/"
    WRAPPER = "MainWrapper"
    TEMPLATE = "HomeView"
    title = "Home"

    def get_data(self, request, *args, **kwargs):
        return {"items": list(models.Game.objects.values('name', 'uuid', 'start_datetime', 'end_datetime'))}

@method_decorator(csrf_exempt, name='dispatch')
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
                    {"type": "ForeignKeyListField", "k": "question", "fields": [
                        {"from_field": "id"},
                        {"from_field": "text"},
                        {"from_field": "answer1"},
                        {"from_field": "answer2"},
                        {"from_field": "answer3"},
                        {"from_field": "answer4"},
                        {"from_field": "correct"},
                        {"from_field": "order"},
                    ]},
                ],
            },
            models.Collection(),
            json.loads(request.body)
        )
        return JsonResponse({"id": obj.id})


class GameView(ApiView):
    url_name = "home"
    url_path = "/game/<uuid:uuid>/"
    WRAPPER = "MainWrapper"
    TEMPLATE = "HomeView"
    title = "Home"

    def get_data(self, request, *args, **kwargs):
        return {"items": list(models.Game.objects.values('name', 'uuid', 'start_datetime', 'end_datetime'))}

@method_decorator(csrf_exempt, name='dispatch')
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
                    {"type": "ForeignKeyListField", "k": "question", "fields": [
                        {"from_field": "id"},
                        {"from_field": "text"},
                        {"from_field": "answer1"},
                        {"from_field": "answer2"},
                        {"from_field": "answer3"},
                        {"from_field": "answer4"},
                        {"from_field": "correct"},
                        {"from_field": "order"},
                    ]},
                ],
            },
            models.Collection(),
            json.loads(request.body)
        )
        return JsonResponse({"id": obj.id})
