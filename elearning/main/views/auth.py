from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import LoginForm, ProfileForm, RegisterForm


class SignInView(LoginView):
    template_name = "auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Welcome to the platform, {user.first_name}!")
        return redirect("dashboard")
    return render(request, "auth/register.html", {"form": form})


@require_POST
def sign_out(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("home")


@login_required
def dashboard(request):
    """Role-aware landing after login."""
    if request.user.is_instructor:
        return redirect("instructor_dashboard")
    return redirect("my_learning")


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "auth/profile.html", {"form": form})
