from .base import *  # noqa: F401,F403

DEBUG = True

INSTALLED_APPS += ['debug_toolbar']  # noqa: F405

MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ['127.0.0.1']

LOGGING['handlers']['file'] = {  # noqa: F405
    'class': 'logging.FileHandler',
    'filename': BASE_DIR / 'logs' / 'development.log',  # noqa: F405
    'formatter': 'verbose',
}
for logger in LOGGING['loggers'].values():  # noqa: F405
    logger['handlers'] = ['console', 'file']
    logger['level'] = 'DEBUG'
