from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Require an authenticated user whose role is one of ``roles``."""

    def decorator(view):
        @login_required
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied("This page is only available to %s accounts." % " or ".join(roles))
            return view(request, *args, **kwargs)

        return _wrapped

    return decorator


student_required = role_required("student")
instructor_required = role_required("instructor")
