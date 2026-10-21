from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Category, Course, Enrollment, Lesson, LessonCompletion, Payment, Question, Quiz, QuizAttempt, Review, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = DjangoUserAdmin.fieldsets + (("Profile", {"fields": ("role", "headline", "bio")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (("Profile", {"fields": ("email", "role")}),)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "color")
    prepopulated_fields = {"slug": ("name",)}


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ("order", "title", "video_url", "duration_minutes", "is_preview")


class QuizInline(admin.TabularInline):
    model = Quiz
    extra = 0
    fields = ("order", "title", "pass_mark")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "category", "level", "price", "is_published", "created_at")
    list_filter = ("is_published", "level", "category")
    search_fields = ("title", "subtitle", "description", "instructor__username")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [LessonInline, QuizInline]
    autocomplete_fields = ("instructor",)


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "pass_mark", "order")
    inlines = [QuestionInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "duration_minutes", "is_preview")
    list_filter = ("course",)


class LessonCompletionInline(admin.TabularInline):
    model = LessonCompletion
    extra = 0
    readonly_fields = ("lesson", "completed_at")
    can_delete = False


class QuizAttemptInline(admin.TabularInline):
    model = QuizAttempt
    extra = 0
    readonly_fields = ("quiz", "score", "correct", "total", "submitted_at")
    can_delete = False


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at", "completed_at")
    list_filter = ("course",)
    search_fields = ("user__username", "course__title")
    inlines = [LessonCompletionInline, QuizAttemptInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("course", "user", "rating", "created_at")
    list_filter = ("rating",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "course", "amount", "method", "status", "created_at")
    list_filter = ("status", "method")
    search_fields = ("reference", "user__username")
