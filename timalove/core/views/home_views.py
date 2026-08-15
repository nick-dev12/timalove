from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from core.controllers import home_controller


def home(request: HttpRequest) -> HttpResponse:
    """Vue HTTP d'accueil — délègue la logique au controller."""
    context = home_controller.get_home_context()
    return render(request, "core/home.html", context)
