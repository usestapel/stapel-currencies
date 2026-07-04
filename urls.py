"""URL patterns — no global prefix here, the host project mounts them:

    path("currencies/", include("stapel_currencies.urls"))

Routes (relative to the mount): ``api/`` (list), ``api/<code>/`` (retrieve).
"""
from django.urls import include, path
from stapel_core.django.api.routers import OptionalSlashRouter

from .views import CurrencyViewSet

router = OptionalSlashRouter()
router.register(r"api", CurrencyViewSet, basename="currency")

urlpatterns = [
    path("", include(router.urls)),
]
