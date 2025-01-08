from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Course, Enrollment, Lesson, Review, Category, Payment, Quiz, QuizQuestion, UserProgress, \
    UserQuizScore


# Custom User Admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_student', 'is_instructor')
    search_fields = ('username', 'email')
    ordering = ('username',)
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('is_student', 'is_instructor')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('is_student', 'is_instructor')}),
    )

@admin.register(UserQuizScore)
class UserQuizScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'quiz', 'score')

# Register all models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(Lesson)
admin.site.register(Review)
admin.site.register(Category)
admin.site.register(Payment)
admin.site.register(Quiz)
admin.site.register(QuizQuestion)
admin.site.register(UserProgress)
