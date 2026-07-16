"""v1 URL set for stapel-currencies (api-versioning.md §2, §6).

No global prefix here — the host project mounts the root ``urls.py``:

    path("currencies/", include("stapel_currencies.urls"))

Routes (relative to the mount): ``api/v1/`` (list), ``api/v1/<code>/``
(retrieve) — the version segment sits right after ``api/`` per canon.
"""
from django.urls import include, path
from stapel_core.django.api.routers import OptionalSlashRouter

from .views import CurrencyViewSet

router = OptionalSlashRouter()
router.register(r"api/v1", CurrencyViewSet, basename="currency")

urlpatterns = [
    path("", include(router.urls)),
]
