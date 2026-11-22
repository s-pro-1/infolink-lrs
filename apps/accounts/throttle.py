"""Small cache-based login throttle: no extra dependency, good enough for v1."""
from django.core.cache import cache
from django.http import HttpResponse

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300


def _key(request):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    return f"login-fail:{ip}"


class LoginThrottleMixin:
    def post(self, request, *args, **kwargs):
        if cache.get(_key(request), 0) >= MAX_ATTEMPTS:
            return HttpResponse(
                "Too many failed sign-in attempts. Please wait a few minutes and try again.", status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        key = _key(self.request)
        cache.add(key, 0, WINDOW_SECONDS)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, WINDOW_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(_key(self.request))
        return super().form_valid(form)
