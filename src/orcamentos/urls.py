from django.urls import path
from . import views

app_name = "orcamentos"

urlpatterns = [
    path("", views.orcamento_list, name="list"),
]