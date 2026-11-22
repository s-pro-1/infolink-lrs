from django.conf import settings


def branding(request):
    return {
        "PLATFORM_NAME": settings.PLATFORM_NAME,
        "INSTITUTION_NAME": settings.INSTITUTION_NAME,
        "PRIMARY_COLOR": settings.PRIMARY_COLOR,
    }
