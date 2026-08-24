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

    def get_object(self):
        """Resolve the ISO code case-insensitively.

        ``lookup_value_regex`` admits ``usd`` but the primary key is stored
        upper-case, so an exact lookup answered 404 for a code the URL had
        already accepted. Normalise here rather than widening the regex or
        the query: the catalog is canonically upper-case and every other
        surface (comm, admin, the seed list) says so too.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        code = self.kwargs.get(lookup_url_kwarg)
        if isinstance(code, str):
            self.kwargs[lookup_url_kwarg] = code.upper()
        return super().get_object()
