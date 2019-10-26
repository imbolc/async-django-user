from django.conf import settings
from django.http import JsonResponse
from django.urls import path
from django.contrib import admin
import django

import cfg

settings.configure(
    DEBUG=cfg.DEBUG,
    SECRET_KEY=cfg.SECRET_KEY,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": cfg.DB_NAME,
        }
    },
    ROOT_URLCONF=__name__,
    MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
    ],
    INSTALLED_APPS=[
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
    ],
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    # "django.template.context_processors.debug",
                    # "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ]
            },
        }
    ],
    STATIC_URL="/static/",
)


def index(request):
    session = request.session
    framework = "django"
    session[framework] = request.session.get(framework, 0) + 1
    return JsonResponse(
        {"framework": framework, "session": dict(request.session)}
    )


django.setup()
urlpatterns = [path("admin/", admin.site.urls), path("", index)]


if __name__ == "__main__":
    import sys
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
