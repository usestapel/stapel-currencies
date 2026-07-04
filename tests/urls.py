from django.urls import include, path

urlpatterns = [
    path("currencies/", include("stapel_currencies.urls")),
]
