from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Course, Lesson, Payment, Question, Quiz, Review

User = get_user_model()


def _bootstrapify(form: forms.Form) -> None:
    """Add Bootstrap classes to every widget so templates can just render fields."""
    for name, field in form.fields.items():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxInput,)):
            widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            widget.attrs.setdefault("class", "form-select")
        elif isinstance(widget, forms.RadioSelect):
            pass
        else:
            widget.attrs.setdefault("class", "form-control")
        if field.required:
            widget.attrs.setdefault("required", "required")


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _bootstrapify(self)


# --------------------------------------------------------------------------- auth
class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.CharField(label="Username or email")

    def clean(self):
        # Allow logging in with an email address as well as a username.
        username = self.cleaned_data.get("username", "")
        if "@" in username:
            match = User.objects.filter(email__iexact=username).first()
            if match:
                self.cleaned_data["username"] = match.username
        return super().clean()


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=User.Role.choices, widget=forms.RadioSelect, initial=User.Role.STUDENT)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email", "role")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "headline", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}


# --------------------------------------------------------------------------- instructor
class CourseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            "title", "subtitle", "category", "level", "language", "price",
            "thumbnail", "description", "what_you_learn", "requirements", "is_published",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "what_you_learn": forms.Textarea(attrs={"rows": 4, "placeholder": "One outcome per line"}),
            "requirements": forms.Textarea(attrs={"rows": 3, "placeholder": "One prerequisite per line"}),
        }


class LessonForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ("title", "video_url", "duration_minutes", "content", "is_preview")
        widgets = {"content": forms.Textarea(attrs={"rows": 6})}


class QuizForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ("title", "description", "pass_mark")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class QuestionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Question
        fields = ("text", "option_a", "option_b", "option_c", "option_d", "correct_option", "explanation")
        widgets = {
            "text": forms.Textarea(attrs={"rows": 2}),
            "explanation": forms.Textarea(attrs={"rows": 2}),
        }


# --------------------------------------------------------------------------- student
class ReviewForm(BootstrapFormMixin, forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, f"{i} star{'s' if i > 1 else ''}") for i in range(5, 0, -1)],
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "placeholder": "What did you think of the course?"})}


class CheckoutForm(BootstrapFormMixin, forms.Form):
    """Mock checkout: validates shape only, never stores card data."""

    method = forms.ChoiceField(choices=Payment.Method.choices, widget=forms.RadioSelect, initial=Payment.Method.CARD)
    cardholder = forms.CharField(max_length=120, required=False)
    card_number = forms.CharField(max_length=19, required=False, widget=forms.TextInput(attrs={"placeholder": "4242 4242 4242 4242", "inputmode": "numeric"}))
    expiry = forms.CharField(max_length=5, required=False, widget=forms.TextInput(attrs={"placeholder": "MM/YY"}))
    cvc = forms.CharField(label="CVC", max_length=4, required=False, widget=forms.TextInput(attrs={"placeholder": "123", "inputmode": "numeric"}))

    def clean(self):
        data = super().clean()
        if data.get("method") == Payment.Method.CARD:
            digits = "".join(ch for ch in data.get("card_number", "") if ch.isdigit())
            if len(digits) < 12:
                self.add_error("card_number", "Enter a valid card number (use 4242 4242 4242 4242 for testing).")
            if not data.get("cardholder"):
                self.add_error("cardholder", "Cardholder name is required.")
            if len(data.get("expiry", "")) != 5:
                self.add_error("expiry", "Use MM/YY.")
            if not data.get("cvc", "").isdigit():
                self.add_error("cvc", "CVC must be numeric.")
        return data
