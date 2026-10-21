from django.conf import settings

from .models import Category


def site(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "nav_categories": Category.objects.all()[:12],
    }
