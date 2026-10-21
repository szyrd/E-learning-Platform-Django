"""Render a completion certificate as a landscape A4 PDF (reportlab, no system deps)."""
from __future__ import annotations

import io

import qrcode
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

TEAL = colors.HexColor("#0f766e")
DEEP = colors.HexColor("#0b3d3a")
CORAL = colors.HexColor("#e8603c")
INK = colors.HexColor("#1b2430")
MUTED = colors.HexColor("#5f6b7a")
PAPER = colors.HexColor("#faf8f4")


def _fit_font_size(c, text, font, max_width, start=34, minimum=16):
    size = start
    while size > minimum and c.stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def build_certificate_pdf(certificate, verify_url: str, site_name: str = "LearnHub") -> bytes:
    enrollment = certificate.enrollment
    learner = enrollment.user.display_name
    course = enrollment.course
    instructor = course.instructor.display_name
    issued = timezone.localtime(certificate.issued_at).strftime("%B %d, %Y")

    buf = io.BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setTitle(f"Certificate of Completion - {course.title}")
    c.setAuthor(site_name)

    # background + frame
    c.setFillColor(PAPER); c.rect(0, 0, width, height, stroke=0, fill=1)
    c.setStrokeColor(TEAL); c.setLineWidth(6); c.rect(12 * mm, 12 * mm, width - 24 * mm, height - 24 * mm, stroke=1, fill=0)
    c.setStrokeColor(CORAL); c.setLineWidth(1.2); c.rect(16 * mm, 16 * mm, width - 32 * mm, height - 32 * mm, stroke=1, fill=0)
    # corner accent
    c.setFillColor(TEAL); c.rect(12 * mm, height - 12 * mm - 18 * mm, 70 * mm, 18 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 14); c.drawString(18 * mm, height - 24 * mm, site_name.upper())

    # heading
    c.setFillColor(MUTED); c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - 48 * mm, "C E R T I F I C A T E   O F   C O M P L E T I O N")
    c.setFillColor(INK); c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 62 * mm, "This certifies that")

    # learner name
    size = _fit_font_size(c, learner, "Times-BoldItalic", width - 80 * mm, start=40, minimum=20)
    c.setFillColor(DEEP); c.setFont("Times-BoldItalic", size)
    c.drawCentredString(width / 2, height - 80 * mm, learner)
    c.setStrokeColor(CORAL); c.setLineWidth(1.5)
    name_w = min(c.stringWidth(learner, "Times-BoldItalic", size) + 20 * mm, width - 80 * mm)
    c.line(width / 2 - name_w / 2, height - 84 * mm, width / 2 + name_w / 2, height - 84 * mm)

    # course
    c.setFillColor(INK); c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 97 * mm, "has successfully completed the online course")
    size = _fit_font_size(c, course.title, "Helvetica-Bold", width - 70 * mm, start=26, minimum=15)
    c.setFillColor(TEAL); c.setFont("Helvetica-Bold", size)
    c.drawCentredString(width / 2, height - 110 * mm, course.title)
    c.setFillColor(MUTED); c.setFont("Helvetica", 11)
    details = f"{course.lessons.count()} lessons · {course.quizzes.count()} graded quiz{'zes' if course.quizzes.count() != 1 else ''} · {course.get_level_display()}"
    c.drawCentredString(width / 2, height - 119 * mm, details)

    # signature block (left) and date (right)
    base_y = 42 * mm
    c.setStrokeColor(INK); c.setLineWidth(0.8)
    c.line(40 * mm, base_y, 115 * mm, base_y)
    c.setFillColor(INK); c.setFont("Times-Italic", 16); c.drawCentredString(77.5 * mm, base_y + 3 * mm, instructor)
    c.setFillColor(MUTED); c.setFont("Helvetica", 9); c.drawCentredString(77.5 * mm, base_y - 5 * mm, "INSTRUCTOR")
    c.line(width - 115 * mm, base_y, width - 40 * mm, base_y)
    c.setFillColor(INK); c.setFont("Helvetica", 12); c.drawCentredString(width - 77.5 * mm, base_y + 3 * mm, issued)
    c.setFillColor(MUTED); c.setFont("Helvetica", 9); c.drawCentredString(width - 77.5 * mm, base_y - 5 * mm, "DATE ISSUED")

    # QR + code (center bottom)
    qr = qrcode.QRCode(box_size=4, border=1); qr.add_data(verify_url); qr.make(fit=True)
    img = qr.make_image(fill_color="#0b3d3a", back_color="#faf8f4").convert("RGB")
    qr_size = 26 * mm
    c.drawImage(ImageReader(img), width / 2 - qr_size / 2, 24 * mm, qr_size, qr_size)
    c.setFillColor(INK); c.setFont("Courier-Bold", 10); c.drawCentredString(width / 2, 19.5 * mm, certificate.code)
    c.setFillColor(MUTED); c.setFont("Helvetica", 7.5); c.drawCentredString(width / 2, 15.5 * mm, f"Verify at {verify_url}")

    c.showPage(); c.save()
    return buf.getvalue()
