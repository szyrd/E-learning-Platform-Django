from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..decorators import student_required
from ..forms import CheckoutForm, ReviewForm
from ..models import Course, Enrollment, Payment, Review
from ..services import EnrollmentError, enroll, get_enrollment


@student_required
def my_learning(request):
    enrollments = Enrollment.objects.filter(user=request.user).with_progress().select_related("course", "course__instructor", "course__category")
    in_progress = [e for e in enrollments if not e.is_completed]
    completed = [e for e in enrollments if e.is_completed]
    recommended = (
        Course.objects.published().with_stats().exclude(enrollments__user=request.user)
        .select_related("instructor", "category").order_by("-student_count")[:3]
    )
    return render(request, "student/my_learning.html", {
        "in_progress": in_progress,
        "completed": completed,
        "recommended": recommended,
        "tab": request.GET.get("tab", "progress"),
    })


@student_required
@require_POST
def enroll_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if not course.is_free:
        return redirect("checkout", slug=slug)
    try:
        enroll(request.user, course)
    except EnrollmentError as exc:
        messages.error(request, str(exc))
        return redirect(course)
    messages.success(request, f"You're enrolled in “{course.title}”. Happy learning!")
    return redirect("learn", slug=slug)


@student_required
def checkout(request, slug):
    course = get_object_or_404(Course.objects.select_related("instructor"), slug=slug)
    if get_enrollment(request.user, course):
        return redirect("learn", slug=slug)
    if course.is_free:
        return redirect(course)
    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            enroll(request.user, course, payment_method=form.cleaned_data["method"])
        except EnrollmentError as exc:
            messages.error(request, str(exc))
            return redirect(course)
        messages.success(request, f"Payment received. You now have full access to “{course.title}”.")
        return redirect("learn", slug=slug)
    return render(request, "student/checkout.html", {"course": course, "form": form})


@student_required
def submit_review(request, slug):
    course = get_object_or_404(Course, slug=slug)
    enrollment = get_enrollment(request.user, course)
    if not enrollment:
        messages.error(request, "Enroll in the course before leaving a review.")
        return redirect(course)
    review = Review.objects.filter(course=course, user=request.user).first()
    form = ReviewForm(request.POST or None, instance=review)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.course = course
        obj.user = request.user
        obj.save()
        messages.success(request, "Thanks for your review!")
        return redirect(f"{course.get_absolute_url()}#reviews")
    return render(request, "student/review_form.html", {"course": course, "form": form, "review": review})


@student_required
def payments(request):
    return render(request, "student/payments.html", {"payments": Payment.objects.filter(user=request.user).select_related("course")})
