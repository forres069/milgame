"""milgame URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from logicore_django_react.urls import react_reload_and_static_urls, react_html_template_urls
from main import views # required
from logicore_django_react_pages.views import all_api_urls
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    *i18n_patterns(path('admin/', admin.site.urls), prefix_default_language=False),
    *all_api_urls(),
    *i18n_patterns(re_path(r"api/.*", views.Error404ApiView.as_view()), prefix_default_language=False),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    
urlpatterns = react_reload_and_static_urls + urlpatterns + react_html_template_urls 
