from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.db import connection
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception as exc:  # pragma: no cover - only hit when DB is down
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("main.api_urls")),
    path("", include("main.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "main.views.errors.forbidden"
handler404 = "main.views.errors.not_found"
handler500 = "main.views.errors.server_error"
