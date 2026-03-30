from django.conf import settings


def login_security(request):
    captcha_enabled = bool(settings.LOGIN_RECAPTCHA_SITE_KEY and settings.LOGIN_RECAPTCHA_SECRET_KEY)
    return {
        "LOGIN_RECAPTCHA_SITE_KEY": settings.LOGIN_RECAPTCHA_SITE_KEY if captcha_enabled else "",
        "LOGIN_RECAPTCHA_ENABLED": captcha_enabled,
    }
