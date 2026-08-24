"""Canonical-prefix URLconf for contract emission (contract-pipeline.md §2).

The host mounts currencies at ``path("currencies/",
include("stapel_currencies.urls"))``, which yields the canonical versioned
surface ``/currencies/api/v1/...`` (api-versioning.md §2 — the version
segment is part of the contract). This URLconf reproduces that mount
exactly, so drf-spectacular emits ``/currencies/api/v1/...`` paths (and
matching ``currencies_api_v1_*`` operationIds) and ``generate_flow_docs``
resolves flow endpoints to the same.
"""
from django.urls import include, path

urlpatterns = [
    path("currencies/", include("stapel_currencies.urls")),
]
