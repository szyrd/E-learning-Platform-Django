"""Create a realistic demo catalogue. Safe to run repeatedly."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import Category, Course, Enrollment, Lesson, Question, Quiz, Review
from main.services import enroll, grade_quiz, mark_lesson_complete

User = get_user_model()

DEMO_PASSWORD = "learnhub123"

CATEGORIES = [
    ("Data Science", "bi-graph-up-arrow", "#0f766e", "Statistics, machine learning and analytics."),
    ("Computer Science", "bi-cpu", "#4f46e5", "Programming, algorithms and software engineering."),
    ("Business", "bi-briefcase", "#be185d", "Management, finance, marketing and entrepreneurship."),
    ("Design", "bi-palette", "#d97706", "UX, UI and visual communication."),
    ("Personal Development", "bi-lightbulb", "#059669", "Productivity, communication and career skills."),
    ("Languages", "bi-translate", "#e8603c", "Learn to speak, read and write a new language."),
]

INSTRUCTORS = [
    dict(username="ana.silva", first_name="Ana", last_name="Silva", email="ana@learnhub.test",
         headline="Lead Data Scientist · ex-Spotify", bio="Ana has spent a decade turning messy data into decisions and loves teaching the fundamentals with real datasets."),
    dict(username="marcus.lee", first_name="Marcus", last_name="Lee", email="marcus@learnhub.test",
         headline="Staff Software Engineer", bio="Marcus builds large-scale web systems and has mentored hundreds of engineers through their first production deploys."),
    dict(username="priya.nair", first_name="Priya", last_name="Nair", email="priya@learnhub.test",
         headline="Product Designer & Design Lead", bio="Priya designs products used by millions and teaches design thinking with hands-on critique."),
]

STUDENTS = [
    dict(username="student", first_name="Sam", last_name="Taylor", email="student@learnhub.test"),
    dict(username="jordan.kim", first_name="Jordan", last_name="Kim", email="jordan@learnhub.test"),
    dict(username="maria.garcia", first_name="Maria", last_name="Garcia", email="maria@learnhub.test"),
    dict(username="li.wei", first_name="Li", last_name="Wei", email="liwei@learnhub.test"),
]

YT = {
    "python": "https://www.youtube.com/watch?v=kqtD5dpn9C8",
    "pandas": "https://www.youtube.com/watch?v=vmEHCJofslg",
    "sql": "https://www.youtube.com/watch?v=HXV3zeQKqGY",
    "ml": "https://www.youtube.com/watch?v=ukzFI9rgwfU",
    "git": "https://www.youtube.com/watch?v=RGOj5yH7evk",
    "django": "https://www.youtube.com/watch?v=F5mRW0jo-U4",
    "ux": "https://www.youtube.com/watch?v=Ovj4hFxko7c",
    "figma": "https://www.youtube.com/watch?v=FTFaQWZBqQ8",
    "finance": "https://www.youtube.com/watch?v=WEDIj9JBTC8",
    "speaking": "https://www.youtube.com/watch?v=Unzc731iCUY",
    "spanish": "https://www.youtube.com/watch?v=kJQjXAVEWt0",
}

COURSES = [
    dict(
        instructor="ana.silva", category="Data Science", level="beginner", price="0.00",
        title="Python for Data Analysis",
        subtitle="Go from zero to confident data wrangling with pandas and matplotlib.",
        description="Learn the Python toolkit every analyst uses. You will load real datasets, clean them, explore them visually and communicate findings. No programming experience required; we start from the very first line of code.",
        what_you_learn="Write clean Python scripts and notebooks\nLoad, clean and reshape data with pandas\nBuild charts that tell a story with matplotlib\nAnswer business questions with group-bys and pivots",
        requirements="A laptop with Python 3 installed\nCuriosity about data",
        lessons=[
            ("Welcome & setting up your environment", YT["python"], 8, True),
            ("Python basics: variables, lists and loops", YT["python"], 24, False),
            ("Your first DataFrame", YT["pandas"], 19, False),
            ("Cleaning messy data", YT["pandas"], 27, False),
            ("Visualising trends with matplotlib", YT["pandas"], 22, False),
        ],
        quizzes=[("Python & pandas fundamentals", 70, [
            ("Which pandas object represents a 2-D table?", "Series", "DataFrame", "Array", "Index", "B", "A DataFrame is the two-dimensional, labelled structure; a Series is one-dimensional."),
            ("What does df.head() return?", "The last 5 rows", "Column names only", "The first 5 rows", "A summary of dtypes", "C", ""),
            ("Which method removes rows with missing values?", "df.fillna()", "df.dropna()", "df.drop()", "df.isna()", "B", ""),
            ("How do you select the column 'price'?", "df.price()", "df['price']", "df.get_column('price')", "df->price", "B", ""),
        ])],
    ),
    dict(
        instructor="ana.silva", category="Data Science", level="intermediate", price="49.00",
        title="Machine Learning Foundations",
        subtitle="Understand how models learn and ship your first predictive pipeline with scikit-learn.",
        description="A practical, maths-light introduction to supervised learning. You will build regression and classification models, learn to evaluate them honestly and avoid the classic beginner traps like leakage and overfitting.",
        what_you_learn="Frame a problem as regression or classification\nTrain and evaluate models with scikit-learn\nUse cross-validation and avoid overfitting\nExplain model results to non-technical stakeholders",
        requirements="Comfortable with Python and pandas\nHigh-school algebra",
        lessons=[
            ("What is machine learning, really?", YT["ml"], 14, True),
            ("Linear regression from scratch", YT["ml"], 31, False),
            ("Classification with logistic regression", YT["ml"], 28, False),
            ("Train / test splits and cross-validation", YT["ml"], 21, False),
            ("Decision trees and random forests", YT["ml"], 33, False),
            ("Capstone: predicting house prices", YT["ml"], 40, False),
        ],
        quizzes=[("Model evaluation", 70, [
            ("Why do we hold out a test set?", "To speed up training", "To estimate performance on unseen data", "To increase accuracy", "To reduce dataset size", "B", ""),
            ("Overfitting means the model…", "performs badly on both train and test", "performs well on train but badly on test", "has too few parameters", "trains too slowly", "B", ""),
            ("Which metric suits an imbalanced classification problem best?", "Accuracy", "Mean squared error", "F1 score", "R squared", "C", ""),
        ])],
    ),
    dict(
        instructor="marcus.lee", category="Computer Science", level="beginner", price="0.00",
        title="Git & GitHub for Beginners",
        subtitle="Version control explained visually, from first commit to pull requests.",
        description="Stop fearing the terminal. This short course demystifies Git with clear diagrams and real exercises so you can collaborate on any codebase with confidence.",
        what_you_learn="Track changes with commits and branches\nResolve merge conflicts calmly\nCollaborate through pull requests\nRecover from common mistakes",
        requirements="None",
        lessons=[
            ("Why version control?", YT["git"], 9, True),
            ("Commits, branches and the staging area", YT["git"], 22, False),
            ("Working with remotes and GitHub", YT["git"], 18, False),
            ("Pull requests and code review", YT["git"], 16, False),
        ],
        quizzes=[("Git essentials", 60, [
            ("Which command records staged changes?", "git push", "git commit", "git add", "git merge", "B", ""),
            ("What does git clone do?", "Deletes a repository", "Copies a remote repository locally", "Creates a branch", "Reverts a commit", "B", ""),
            ("A branch is…", "A copy of the whole project folder", "A movable pointer to a commit", "A GitHub-only feature", "A type of merge conflict", "B", ""),
        ])],
    ),
    dict(
        instructor="marcus.lee", category="Computer Science", level="intermediate", price="79.00",
        title="Full-Stack Web Development with Django",
        subtitle="Build, test and deploy a production-ready web application.",
        description="Go beyond tutorials. You will design data models, write views and templates, secure your app, add a REST API and deploy it with Docker. By the end you will have a portfolio project you are proud of.",
        what_you_learn="Model data and write migrations\nBuild server-rendered pages and REST endpoints\nAuthenticate users and protect views\nContainerise and deploy with Docker",
        requirements="Python basics\nHTML & CSS fundamentals",
        lessons=[
            ("Course overview and project tour", YT["django"], 11, True),
            ("Models, migrations and the admin", YT["django"], 35, False),
            ("Views, URLs and templates", YT["django"], 38, False),
            ("Forms and validation", YT["django"], 27, False),
            ("Authentication and permissions", YT["django"], 30, False),
            ("Building a REST API with DRF", YT["django"], 34, False),
            ("Docker and deployment", YT["django"], 29, False),
        ],
        quizzes=[
            ("Django fundamentals", 70, [
                ("Which file maps URLs to views?", "models.py", "urls.py", "views.py", "admin.py", "B", ""),
                ("Migrations are used to…", "serve static files", "evolve the database schema", "cache templates", "run tests", "B", ""),
                ("Which decorator restricts a view to logged-in users?", "@csrf_exempt", "@login_required", "@require_POST", "@cache_page", "B", ""),
            ]),
            ("APIs & deployment", 70, [
                ("A ModelSerializer…", "renders HTML", "maps model instances to JSON", "runs migrations", "stores sessions", "B", ""),
                ("docker compose up starts…", "a single container only", "all services in the compose file", "the Django shell", "unit tests", "B", ""),
            ]),
        ],
    ),
    dict(
        instructor="priya.nair", category="Design", level="beginner", price="39.00",
        title="UX Design Fundamentals",
        subtitle="Research, wireframe and test ideas like a professional product designer.",
        description="Learn the end-to-end UX process: understanding users, defining problems, sketching solutions and validating them with quick usability tests. Packed with templates you can reuse at work.",
        what_you_learn="Run lightweight user interviews\nTurn insights into problem statements\nSketch and wireframe flows quickly\nPlan and run a 5-user usability test",
        requirements="No design experience needed",
        lessons=[
            ("What UX designers actually do", YT["ux"], 12, True),
            ("User research without a budget", YT["ux"], 26, False),
            ("From insights to problem statements", YT["ux"], 18, False),
            ("Wireframing in Figma", YT["figma"], 32, False),
            ("Usability testing 101", YT["ux"], 24, False),
        ],
        quizzes=[("UX process check", 70, [
            ("A persona is…", "A real customer", "An archetype built from research", "A marketing slogan", "A UI component", "B", ""),
            ("How many users typically reveal most usability issues?", "1", "5", "50", "500", "B", "Nielsen's classic finding: ~5 users surface ~85% of problems."),
            ("Wireframes focus on…", "colour and typography", "structure and layout", "animation", "copywriting", "B", ""),
        ])],
    ),
    dict(
        instructor="priya.nair", category="Business", level="beginner", price="0.00",
        title="Personal Finance Essentials",
        subtitle="Budget, save and invest with a simple system you will actually stick to.",
        description="A jargon-free guide to money. Build a budget that works, understand debt and interest, and learn the basics of long-term investing.",
        what_you_learn="Create a monthly budget in 20 minutes\nUnderstand interest, credit and debt\nSet up an emergency fund\nGrasp index funds and compounding",
        requirements="None",
        lessons=[
            ("Money mindset", YT["finance"], 10, True),
            ("Budgeting that sticks", YT["finance"], 21, False),
            ("Debt, credit scores and interest", YT["finance"], 19, False),
            ("Investing basics", YT["finance"], 25, False),
        ],
        quizzes=[("Finance basics", 60, [
            ("Compound interest means…", "interest only on the principal", "interest on principal plus accumulated interest", "a fixed fee", "a tax", "B", ""),
            ("An emergency fund should cover roughly…", "1 week", "3-6 months of expenses", "10 years", "nothing, use credit", "B", ""),
        ])],
    ),
    dict(
        instructor="marcus.lee", category="Personal Development", level="beginner", price="19.00",
        title="Public Speaking with Confidence",
        subtitle="Structure talks, control nerves and own the room.",
        description="A practical course for anyone who presents: engineers, founders, students. Short lessons, concrete exercises and a repeatable framework for any talk.",
        what_you_learn="Structure a talk in 15 minutes\nManage nerves with proven techniques\nUse voice and body language deliberately\nHandle tough questions gracefully",
        requirements="None",
        lessons=[
            ("Why most talks fail", YT["speaking"], 9, True),
            ("The three-act structure", YT["speaking"], 17, False),
            ("Nerves, breathing and presence", YT["speaking"], 15, False),
            ("Q&A like a pro", YT["speaking"], 13, False),
        ],
        quizzes=[],
    ),
    dict(
        instructor="ana.silva", category="Languages", level="beginner", price="0.00",
        title="Spanish for Travellers",
        subtitle="The 200 phrases you need to order, ask directions and make friends.",
        description="A focused, practical Spanish course for your next trip. Learn by listening and repeating, with cultural notes along the way.",
        what_you_learn="Greet people and introduce yourself\nOrder food and drinks\nAsk for and understand directions\nHandle shops, hotels and transport",
        requirements="None",
        lessons=[
            ("Greetings and introductions", YT["spanish"], 12, True),
            ("At the restaurant", YT["spanish"], 16, False),
            ("Getting around the city", YT["spanish"], 14, False),
        ],
        quizzes=[("Phrase check", 60, [
            ("'Buenos días' means…", "Good night", "Good morning", "Goodbye", "Thank you", "B", ""),
            ("'La cuenta, por favor' asks for…", "the menu", "the bill", "a table", "water", "B", ""),
        ])],
    ),
]

REVIEWS = {
    "Python for Data Analysis": [("student", 5, "Perfect pace for a beginner. The messy-data lesson alone was worth it."), ("jordan.kim", 4, "Clear and practical. Would love a few more exercises."), ("maria.garcia", 5, "Ana explains things so well!")],
    "Git & GitHub for Beginners": [("li.wei", 5, "Finally understand branches. Short and to the point."), ("student", 4, "Great diagrams.")],
    "Full-Stack Web Development with Django": [("jordan.kim", 5, "Best Django course I've taken. The deployment chapter is gold."), ("li.wei", 4, "Dense but rewarding.")],
    "UX Design Fundamentals": [("maria.garcia", 5, "Loved the templates. Used them at work the next day.")],
    "Machine Learning Foundations": [("li.wei", 4, "Good intuition-first approach.")],
}


class Command(BaseCommand):
    help = "Seed demo categories, instructors, students, courses, lessons, quizzes and reviews."

    @transaction.atomic
    def handle(self, *args, **options):
        created_courses = 0
        categories = {}
        for name, icon, color, desc in CATEGORIES:
            categories[name], _ = Category.objects.update_or_create(name=name, defaults={"icon": icon, "color": color, "description": desc})

        users = {}
        for data in INSTRUCTORS:
            users[data["username"]] = self._user(**data, role=User.Role.INSTRUCTOR)
        for data in STUDENTS:
            users[data["username"]] = self._user(**data, role=User.Role.STUDENT)

        courses = {}
        for spec in COURSES:
            course, created = Course.objects.get_or_create(
                title=spec["title"],
                defaults=dict(
                    instructor=users[spec["instructor"]],
                    category=categories[spec["category"]],
                    level=spec["level"],
                    price=Decimal(spec["price"]),
                    subtitle=spec["subtitle"],
                    description=spec["description"],
                    what_you_learn=spec["what_you_learn"],
                    requirements=spec["requirements"],
                ),
            )
            courses[spec["title"]] = course
            if not created:
                continue
            created_courses += 1
            for order, (title, url, minutes, preview) in enumerate(spec["lessons"], start=1):
                Lesson.objects.create(course=course, title=title, video_url=url, duration_minutes=minutes, is_preview=preview, order=order,
                                      content=f"In this lesson we cover {title.lower()}.\n\nWatch the video first, then pause and try the exercise yourself before moving on. Take notes on anything that surprises you; we will revisit it in the quiz.")
            for order, (qtitle, pass_mark, questions) in enumerate(spec["quizzes"], start=1):
                quiz = Quiz.objects.create(course=course, title=qtitle, pass_mark=pass_mark, order=order)
                for qorder, (text, a, b, c, d, correct, expl) in enumerate(questions, start=1):
                    Question.objects.create(quiz=quiz, text=text, option_a=a, option_b=b, option_c=c, option_d=d, correct_option=correct, explanation=expl, order=qorder)

        if created_courses:
            self._enroll_and_progress(users, courses)
            for title, items in REVIEWS.items():
                for username, rating, comment in items:
                    enroll(users[username], courses[title], payment_method="card")
                    Review.objects.get_or_create(course=courses[title], user=users[username], defaults={"rating": rating, "comment": comment})

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {Course.objects.count()} courses, {User.objects.count()} users "
            f"({created_courses} new courses). Demo password for all accounts: {DEMO_PASSWORD}"
        ))

    # ------------------------------------------------------------------ helpers
    def _user(self, username, email, first_name, last_name, role, headline="", bio=""):
        user, created = User.objects.get_or_create(
            username=username,
            defaults=dict(email=email, first_name=first_name, last_name=last_name, role=role, headline=headline, bio=bio),
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _enroll_and_progress(self, users, courses):
        """Give the demo student some believable progress."""
        plan = {
            "student": [("Python for Data Analysis", 3, True), ("Git & GitHub for Beginners", 4, True), ("UX Design Fundamentals", 1, False)],
            "jordan.kim": [("Python for Data Analysis", 5, True), ("Full-Stack Web Development with Django", 2, False)],
            "maria.garcia": [("Python for Data Analysis", 5, True), ("UX Design Fundamentals", 5, True), ("Spanish for Travellers", 1, False)],
            "li.wei": [("Git & GitHub for Beginners", 4, True), ("Machine Learning Foundations", 3, False), ("Full-Stack Web Development with Django", 7, True)],
        }
        for username, items in plan.items():
            for title, lessons_done, do_quiz in items:
                course = courses[title]
                enrollment = enroll(users[username], course, payment_method="card")
                for lesson in course.lessons.all()[:lessons_done]:
                    mark_lesson_complete(enrollment, lesson)
                if do_quiz:
                    for quiz in course.quizzes.all():
                        answers = {str(q.id): q.correct_option for q in quiz.questions.all()}
                        # make one student imperfect for realism
                        if username == "jordan.kim" and answers:
                            first = next(iter(answers))
                            answers[first] = "A" if answers[first] != "A" else "C"
                        grade_quiz(enrollment, quiz, answers)
