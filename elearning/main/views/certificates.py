from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify

from ..certificates import build_certificate_pdf
from ..models import Certificate


def _get(code):
    return get_object_or_404(Certificate.objects.select_related("enrollment__user", "enrollment__course__instructor", "enrollment__course__category"), code=code.upper())


def verify(request, code):
    cert = _get(code)
    return render(request, "certificates/verify.html", {
        "cert": cert,
        "course": cert.course,
        "learner": cert.user,
        "is_owner": request.user.is_authenticated and request.user.id == cert.user.id,
        "verify_url": request.build_absolute_uri(cert.get_absolute_url()),
    })


def download(request, code):
    cert = _get(code)
    pdf = build_certificate_pdf(cert, request.build_absolute_uri(cert.get_absolute_url()), settings.SITE_NAME)
    filename = f"certificate-{slugify(cert.course.title)}-{cert.code}.pdf"
    disposition = "inline" if request.GET.get("inline") else "attachment"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return resp
