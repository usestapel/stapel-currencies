"""DRF views for stapel-currencies."""
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets

from .models import Currency
from .serializers import CurrencySerializer


@extend_schema(tags=["Currencies and exchange rates"])
class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    """Public read-only currency catalog (list + retrieve by ISO code).

    Writes happen through the Django admin (staff), the management
    commands, or the rate-update task — never through this API.

    The serializer seam here is DRF's own: subclass, set
    ``serializer_class`` (or override ``get_serializer_class()``) and
    remount the URL in the host project.
    """

    queryset = Currency.objects.filter(is_active=True)
    serializer_class = CurrencySerializer
    permission_classes = [permissions.AllowAny]
    lookup_value_regex = "[A-Za-z]{3}"
