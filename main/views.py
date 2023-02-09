from logicore_django_react_pages.views import ApiView

class HomeView(ApiView):
    url_name = "home"
    url_path = "/"
    WRAPPER = "MainWrapper"
    TEMPLATE = "HomeView"
    title = "Home"

    def get_data(self, request, *args, **kwargs):
        return {"name": "World"}
