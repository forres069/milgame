from logicore_django_react_pages.views import ApiView
from .framework import write_fields


class HomeView(ApiView):
    url_name = "home"
    url_path = "/"
    WRAPPER = "MainWrapper"
    TEMPLATE = "HomeView"
    title = "Home"

    def get_data(self, request, *args, **kwargs):
        return {"name": "World"}



class LoadFromBibleView(ApiView):
    url_name = "load-from-bible"
    url_path = "/load-from-bible-0d66a7dd-a69d-4a8d-ae59-7b379ceb9c12/"

    def get_data(self, request, *args, **kwargs):
        return {}

    def post(self, request, *args, **kwargs):
        return wri
