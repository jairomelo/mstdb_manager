# pages/urls.py
from django.urls import path
from .views import home, LugarCreateView, LugarAutocomplete


urlpatterns = [
    path("", home, name="home"),
    path('Add/lugar/', LugarCreateView.as_view(), name='lugar-new'),
    path('lugar-autocomplete/', LugarAutocomplete.as_view(), name='lugar-autocomplete'),
]