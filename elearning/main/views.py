from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
import json

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import models
from .forms import CourseForm, LessonForm, QuizForm
from .models import Course, Enrollment, Lesson, Quiz, QuizQuestion, Review, UserProgress, UserQuizScore
from django.utils import timezone
from django.db.models import Avg, F
from django.urls import reverse

from .serializers import CourseSerializer, LessonSerializer, ReviewSerializer


def redirect_to_login(request):
    return redirect('login')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect based on user role
            if user.is_instructor:
                return redirect('instructor_dashboard')  # Redirect to instructor page
            elif user.is_student:
                return redirect('student_dashboard')  # Redirect to student page
        else:
            # Invalid credentials
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')


User = get_user_model()  # This ensures you use the correct User model


def register_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        role = request.POST.get('role')  # Student or Instructor

        if password != confirm_password:
            return render(request, 'register.html', {'error': "Passwords don't match"})

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': "Username already exists"})

        # Create user and set role
        user = User.objects.create_user(username=username, email=email, password=password)
        if role == 'Student':
            user.is_student = True
        elif role == 'Instructor':
            user.is_instructor = True

        user.save()
        return redirect('login')  # Redirect to login page

    return render(request, 'register.html')


@login_required
def student_dashboard(request):
    courses = Course.objects.select_related('instructor').all()
    enrolled_courses = Enrollment.objects.filter(user=request.user).values_list('course_id', flat=True)
    if not request.user.is_student:  # Check for student role
        return redirect('login')
    return render(request, 'student_dashboard.html', {
        'courses': courses,
        'enrolled_courses': enrolled_courses
    })


@login_required
def instructor_dashboard(request):
    instructor_courses = Course.objects.filter(instructor=request.user)  # Fetch instructor's courses
    context = {
        'instructor': request.user,
        'courses': instructor_courses,
    }
    if not request.user.is_instructor:
        return redirect('login')  # Redirect if not instructor
    return render(request, 'instructor_dashboard.html', context)


def enroll(request, course_id):
    # Handle student enrollment logic
    if not request.user.is_authenticated or not request.user.is_student:
        return redirect('login')
    course = Course.objects.get(id=course_id)
    # Create Enrollment instance here
    return redirect('student_dashboard')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def create_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            return redirect('my_courses')  # Redirect to 'My Courses' after creation
    else:
        form = CourseForm()
    return render(request, 'create_course.html', {'form': form})


@login_required
def my_courses(request):
    courses = Course.objects.filter(instructor=request.user)
    return render(request, 'my_courses.html', {'courses': courses})


@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        # Check if the user is already enrolled in the course
        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return JsonResponse({'success': False, 'message': 'You are already enrolled in this course.'})

        # Handle free courses
        if course.price == 0:
            # Create an enrollment record
            enrollment = Enrollment.objects.create(student=request.user, course=course, status='ongoing')

            # Create a UserProgress record for tracking progress
            user_progress, created = UserProgress.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={
                    'completed_lessons': [],
                    'quiz_score': "0.00%",
                }
            )

            if created:
                print(f"UserProgress created for {request.user.username} in {course.title}")
            else:
                print(f"UserProgress already exists for {request.user.username} in {course.title}")

            return JsonResponse({'success': True, 'message': 'You have successfully enrolled in the course.'})

        # Handle paid courses: return price to show the payment modal
        return JsonResponse({
            'success': False,
            'show_payment_modal': True,
            'price': float(course.price)  # Convert Decimal to float for JSON serialization
        })

    # If the request is not POST, return an error message
    return JsonResponse({'success': False, 'message': 'Invalid request method. Only POST requests are allowed.'})




@login_required
def student_enrollments(request):
    """View all courses the student has enrolled in."""
    enrollments = Enrollment.objects.filter(user=request.user)
    return render(request, 'student_enrollments.html', {'enrollments': enrollments})


@login_required
def instructor_enrollments(request):
    """View all students enrolled in the instructor's courses."""
    enrollments = Enrollment.objects.filter(course__instructor=request.user)
    return render(request, 'instructor_enrollments.html', {'enrollments': enrollments})


@login_required
def course_page(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = Lesson.objects.filter(course=course)
    quizzes = Quiz.objects.filter(course=course)
    reviews = Review.objects.filter(course=course)
    is_instructor = course.instructor == request.user

    # Handle completed lessons
    completed_lesson_ids = []
    user_progress = UserProgress.objects.filter(user=request.user, course=course).first()
    if user_progress and user_progress.completed_lessons:
        completed_lesson_ids = (
            json.loads(user_progress.completed_lessons)
            if isinstance(user_progress.completed_lessons, str)
            else user_progress.completed_lessons
        )

    # Handle quiz scores
    quiz_scores = {}
    user_quiz_scores = UserQuizScore.objects.filter(user=request.user, course=course)
    quiz_scores = {score.quiz.id: score.score for score in user_quiz_scores}

    # Check if the student is eligible to submit a review
    all_lessons_completed = len(completed_lesson_ids) == lessons.count()
    all_quizzes_completed = all([score == 100 for score in quiz_scores.values()])
    show_review_form = not is_instructor and all_lessons_completed and all_quizzes_completed

    context = {
        "course": course,
        "lessons": lessons,
        "quizzes": quizzes,
        "reviews": reviews,
        "is_instructor": is_instructor,
        "quiz_scores": quiz_scores,
        "completed_lesson_ids": completed_lesson_ids,
        "show_review_form": show_review_form,
    }

    return render(request, "course_page.html", context)







@login_required
def add_lesson(request, course_id):
    if request.method == "POST":
        titles = request.POST.getlist("title[]")
        contents = request.POST.getlist("content[]")
        video_urls = request.POST.getlist("video_url[]")

        for title, content, video_url in zip(titles, contents, video_urls):
            Lesson.objects.create(
                course_id=course_id,
                title=title,
                content=content,
                video_url=video_url
            )

        return redirect("course_page", course_id=course_id)

    return render(request, "add_lesson.html")


@login_required
def add_quiz(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        if not title:
            return JsonResponse({'success': False, 'message': 'Quiz title is required.'})

        # Create a new quiz
        quiz = Quiz.objects.create(course=course, title=title, total_marks=100)  # Default total_marks as 0
        return redirect('add_quiz_questions', quiz_id=quiz.id)  # Redirect to Add Questions Page'
    return redirect('course_detail', course_id=course_id)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
def add_quiz_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if request.method == 'POST':
        # Loop through dynamic form fields
        question_count = 1
        while f'question_text_{question_count}' in request.POST:
            question_text = request.POST.get(f'question_text_{question_count}')
            option_a = request.POST.get(f'option_a_{question_count}')
            option_b = request.POST.get(f'option_b_{question_count}')
            option_c = request.POST.get(f'option_c_{question_count}')
            option_d = request.POST.get(f'option_d_{question_count}')
            correct_option = request.POST.get(f'correct_option_{question_count}')

            # Validate inputs and save
            if question_text and correct_option:
                QuizQuestion.objects.create(
                    quiz=quiz,
                    question_text=question_text,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_option=correct_option
                )
            question_count += 1

        messages.success(request, "Questions added successfully!")
        return redirect('quiz_detail', quiz_id=quiz.id)

    return render(request, 'add_quiz_questions.html', {'quiz': quiz})


@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()  # Use the related name 'questions'
    enumerated_questions = enumerate(questions, start=1)
    return render(request, 'quiz_detail.html', {'quiz': quiz, 'questions': enumerated_questions})


@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

    if request.method == "POST":
        correct_answers = 0
        total_questions = questions.count()

        for question in questions:
            selected_option = request.POST.get(str(question.id))
            if selected_option == question.correct_option:
                correct_answers += 1

        score = (correct_answers / total_questions) * 100
        return render(request, 'quiz_result.html', {'quiz': quiz, 'score': score})

    return render(request, 'start_quiz.html', {'quiz': quiz, 'questions': questions})


@login_required
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    user = request.user
    course = quiz.course

    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method. Only POST is allowed.")

    # Get all questions in the quiz
    total_questions = quiz.questions.count()
    correct_answers_count = 0

    # Iterate through all the quiz questions
    for question in quiz.questions.all():
        # Get the selected option for the question from the POST data
        selected_option = request.POST.get(str(question.id))  # Input name is question.id

        # Check if the selected option matches the correct option
        if selected_option and selected_option == question.correct_option:
            correct_answers_count += 1

    # Calculate the percentage score
    percentage_score = (correct_answers_count / total_questions) * 100 if total_questions > 0 else 0

    # Update or create the UserQuizScore entry for the user and quiz
    user_quiz_score, created = UserQuizScore.objects.update_or_create(
        user=user,
        quiz=quiz,
        defaults={
            'score': percentage_score,
            'course': course  # Ensure course is added
        }
    )

    # Redirect back to the course page after submitting the quiz
    return redirect('course_page', course_id=course.id)


@login_required
def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            return redirect('course_page', course_id=lesson.course.id)
    else:
        form = LessonForm(instance=lesson)
    return render(request, 'edit_lesson.html', {'form': form, 'lesson': lesson})


@login_required
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            return redirect('course_page', course_id=quiz.course.id)
    else:
        form = QuizForm(instance=quiz)
    return render(request, 'edit_quiz.html', {'form': form, 'quiz': quiz})


# Delete Lesson View
@login_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course
    lesson.delete()

    # Reorder lessons after deletion
    lessons = Lesson.objects.filter(course=course).order_by('id')
    for index, lesson in enumerate(lessons, start=1):
        lesson.order = index
        lesson.save()

    messages.success(request, f"Lesson '{lesson.title}' deleted successfully.")
    return redirect('course_page', course_id=course.id)


# Delete Quiz View
@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.delete()

    messages.success(request, f"Quiz '{quiz.title}' deleted successfully.")
    return redirect('course_page', course_id=quiz.course.id)


@login_required
def process_payment(request):
    if request.method == "POST":
        course_id = request.POST.get('course_id')
        payment_method = request.POST.get('payment_method')

        if not course_id:
            return JsonResponse({"success": False, "message": "Invalid course ID."}, status=400)

        try:
            course = Course.objects.get(id=course_id)
            if course.price > 0:  # Paid course
                # Process payment logic (mocked here)
                if payment_method not in ['credit_card', 'paypal', 'stripe']:
                    return JsonResponse({"success": False, "message": "Invalid payment method."})

                # Simulating successful payment
                payment_successful = True
                if payment_successful:
                    # Save enrollment details
                    Enrollment.objects.create(
                        user=request.user,
                        course=course,
                        enrollment_date=timezone.now(),
                        status="ongoing"
                    )
                    return redirect('course_page', course_id=course.id)
            else:  # Free course
                Enrollment.objects.create(
                    user=request.user,
                    course=course,
                    enrollment_date=timezone.now(),
                    status="ongoing"
                )
                return redirect('course_page', course_id=course.id)

        except Course.DoesNotExist:
            return JsonResponse({"success": False, "message": "Course not found."}, status=404)

    return JsonResponse({"success": False, "message": "Invalid request."}, status=400)

@login_required
def my_progression(request):
    user = request.user
    enrollments = Enrollment.objects.filter(user=user)
    lessons_data = []
    quizzes_data = []

    for enrollment in enrollments:
        course = enrollment.course

        # Handle UserProgress for completed lessons
        try:
            progress = UserProgress.objects.get(user=user, course=course)
            completed_lessons = json.loads(progress.completed_lessons) if isinstance(progress.completed_lessons, str) else progress.completed_lessons
        except UserProgress.DoesNotExist:
            completed_lessons = []

        total_lessons = Lesson.objects.filter(course=course).count()
        lessons_data.append({
            'course_title': course.title,
            'completed_lessons': f"{len(completed_lessons)}/{total_lessons}",
            'course_id': course.id,
        })

        # Handle quiz scores
        user_quiz_scores = UserQuizScore.objects.filter(user=user, course=course)
        for score in user_quiz_scores:
            quizzes_data.append({
                'course_title': course.title,
                'quiz_title': score.quiz.title,
                'quiz_score': f"{score.score:.2f}" if score.score else "Not attempted",
            })

    return render(request, 'student_progression.html', {
        'lessons_data': lessons_data,
        'quizzes_data': quizzes_data,
    })


@login_required
def play_lesson(request, lesson_id):
    if request.method == "POST":
        try:
            # Fetch the lesson and ensure it exists
            lesson = get_object_or_404(Lesson, id=lesson_id)

            # Get or create the user progress record
            user_progress, created = UserProgress.objects.get_or_create(
                user=request.user,
                course=lesson.course,
            )

            # Ensure completed_lessons is a list and add the lesson ID
            if lesson_id not in user_progress.completed_lessons:
                user_progress.completed_lessons.append(lesson_id)
                user_progress.save()

            # Return a success response with the video URL
            return JsonResponse({
                "status": "success",
                "completed": True,
                "lesson_id": lesson_id,
                "video_url": lesson.video_url,
            })

        except Lesson.DoesNotExist:
            # Handle case where the lesson doesn't exist
            return JsonResponse({"status": "error", "message": "Lesson not found."}, status=404)
        except Exception as e:
            # Handle any unexpected errors
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    # Handle invalid request methods
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)



@login_required
def submit_review(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")
        Review.objects.create(
            user=request.user,
            course=course,
            rating=rating,
            comment=comment,
            created_at=timezone.now(),
        )
        return redirect("course_page", course_id=course_id)
    return HttpResponseBadRequest("Invalid request")



class CourseListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)


class LessonListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        lessons = Lesson.objects.filter(course_id=course_id)
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data)

class ReviewListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        reviews = Review.objects.filter(course_id=course_id)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

