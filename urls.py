"""Root URLconf for stapel-currencies — v1 canon mount (api-versioning.md §2, §6).

Canon: ``/<mod>/api/v1/...``. The host mounts ``include('stapel_currencies.urls')``
under ``currencies/``; the versioned URL set lives in ``urls_v1.py`` (the
``api/v1`` segment is the router prefix there).
"""
from django.urls import include, path

urlpatterns = [
    path('', include('stapel_currencies.urls_v1')),
]
