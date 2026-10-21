from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from ..models import Category, Course, Review
from ..services import course_outline, get_enrollment

SORT_OPTIONS = {
    "popular": "-student_count",
    "newest": "-created_at",
    "rating": "-avg_rating",
    "price_asc": "price",
    "price_desc": "-price",
}


def home(request):
    courses = Course.objects.published().with_stats().select_related("instructor", "category")
    featured = courses.order_by("-student_count", "-created_at")[:6]
    newest = courses.order_by("-created_at")[:3]
    categories = Category.objects.annotate(n=Count("courses", filter=Q(courses__is_published=True))).order_by("-n", "name")[:8]
    return render(request, "catalog/home.html", {
        "featured": featured,
        "newest": newest,
        "categories": categories,
        "stats": {
            "courses": courses.count(),
            "instructors": courses.values("instructor").distinct().count(),
            "students": Course.objects.aggregate(n=Count("enrollments__user", distinct=True))["n"],
        },
    })


def course_list(request):
    qs = Course.objects.published().with_stats().select_related("instructor", "category")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    level = request.GET.get("level", "")
    price = request.GET.get("price", "")
    sort = request.GET.get("sort", "popular")

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(subtitle__icontains=q) | Q(description__icontains=q) | Q(instructor__first_name__icontains=q) | Q(instructor__last_name__icontains=q))
    if category:
        qs = qs.filter(category__slug=category)
    if level in Course.Level.values:
        qs = qs.filter(level=level)
    if price == "free":
        qs = qs.filter(price__lte=0)
    elif price == "paid":
        qs = qs.filter(price__gt=0)
    qs = qs.order_by(SORT_OPTIONS.get(sort, "-student_count"), "-created_at")

    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get("page"))
    enrolled_ids = set()
    if request.user.is_authenticated:
        enrolled_ids = set(request.user.enrollments.values_list("course_id", flat=True))

    return render(request, "catalog/course_list.html", {
        "page": page,
        "q": q,
        "category": category,
        "level": level,
        "price": price,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        "levels": Course.Level.choices,
        "categories": Category.objects.all(),
        "enrolled_ids": enrolled_ids,
        "total": paginator.count,
    })


def course_detail(request, slug):
    course = get_object_or_404(Course.objects.with_stats().select_related("instructor", "category"), slug=slug)
    is_owner = request.user.is_authenticated and course.instructor_id == request.user.id
    if not course.is_published and not is_owner and not request.user.is_staff:
        from django.http import Http404
        raise Http404
    enrollment = get_enrollment(request.user, course)
    reviews = Review.objects.filter(course=course).select_related("user")
    counts = reviews.aggregate(**{f"s{star}": Count("id", filter=Q(rating=star)) for star in range(1, 6)})
    total_reviews = sum(counts.values())
    rating_breakdown = [
        {"star": star, "count": counts[f"s{star}"], "pct": round(counts[f"s{star}"] * 100 / total_reviews) if total_reviews else 0}
        for star in range(5, 0, -1)
    ]
    related = (
        Course.objects.published().with_stats().filter(category=course.category).exclude(pk=course.pk)[:3]
        if course.category else Course.objects.none()
    )
    return render(request, "catalog/course_detail.html", {
        "course": course,
        "enrollment": enrollment,
        "is_owner": is_owner,
        "outline": course_outline(course, enrollment),
        "reviews": reviews[:6],
        "rating_breakdown": rating_breakdown,
        "related": related,
        "instructor_course_count": course.instructor.courses_taught.filter(is_published=True).count(),
        "instructor_student_count": Course.objects.filter(instructor=course.instructor).aggregate(n=Count("enrollments"))["n"],
    })
