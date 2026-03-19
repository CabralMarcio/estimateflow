from django.urls import path
from . import views

app_name = "orcamentos"

urlpatterns = [
    path("", views.orcamento_list, name="list"),
    path("grupo/<int:original_id>/", views.grupo_detail, name="grupo_detail"),

    # HTMX
    path("htmx/<int:orcamento_id>/actions/", views.htmx_actions_panel, name="htmx_actions_panel"),
    path("htmx/<int:orcamento_id>/criar-revisao/", views.htmx_criar_revisao, name="htmx_criar_revisao"),
    path("htmx/<int:orcamento_id>/mudar-status/", views.htmx_mudar_status, name="htmx_mudar_status"),
]