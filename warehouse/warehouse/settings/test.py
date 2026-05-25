from .base import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

LOCALE_PATHS = []
LANGUAGE_CODE = 'en-us'

# Disable throttling in tests
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
}

# Mock inter-service URL for tests
BOOK_SHOP_API_URL = 'http://testserver-bookshop'
BOOK_SHOP_API_TOKEN = 'test-token'
WEBHOOK_SECRET = 'test-webhook-secret'
