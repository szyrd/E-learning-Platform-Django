import re
from urllib.parse import parse_qs, urlparse

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.filter
def stars(value, max_stars=5):
    """Render a 0-5 rating as Bootstrap icon stars."""
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0
    html = []
    for i in range(1, max_stars + 1):
        if value >= i:
            html.append('<i class="bi bi-star-fill"></i>')
        elif value >= i - 0.5:
            html.append('<i class="bi bi-star-half"></i>')
        else:
            html.append('<i class="bi bi-star"></i>')
    return mark_safe(f'<span class="stars" aria-label="{value} out of {max_stars}">{"".join(html)}</span>')


@register.filter
def duration(minutes):
    try:
        minutes = int(minutes or 0)
    except (TypeError, ValueError):
        return ""
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins} min"


_YT_PATTERNS = [
    re.compile(r"youtu\.be/(?P<id>[\w-]{11})"),
    re.compile(r"youtube\.com/(?:embed|shorts|live)/(?P<id>[\w-]{11})"),
]


def video_embed_url(url: str) -> tuple[str, str]:
    """Return (kind, src) where kind is 'iframe', 'video' or ''."""
    if not url:
        return "", ""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "youtube.com" in host and parsed.path == "/watch":
        vid = parse_qs(parsed.query).get("v", [""])[0]
        if vid:
            return "iframe", f"https://www.youtube-nocookie.com/embed/{vid}?rel=0"
    for pattern in _YT_PATTERNS:
        match = pattern.search(url)
        if match:
            return "iframe", f"https://www.youtube-nocookie.com/embed/{match.group('id')}?rel=0"
    if "vimeo.com" in host:
        vid = parsed.path.strip("/").split("/")[-1]
        if vid.isdigit():
            return "iframe", f"https://player.vimeo.com/video/{vid}"
    if parsed.path.lower().endswith((".mp4", ".webm", ".ogg", ".m3u8")):
        return "video", url
    return "iframe", url


@register.inclusion_tag("includes/video_player.html")
def video_player(url, title=""):
    kind, src = video_embed_url(url)
    return {"kind": kind, "src": src, "title": title}


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Rebuild the current query string with some params replaced (for filters/pagination)."""
    request = context["request"]
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"


@register.simple_tag
def active(request, *url_names, css="active"):
    match = getattr(request, "resolver_match", None)
    return css if match and match.url_name in url_names else ""
