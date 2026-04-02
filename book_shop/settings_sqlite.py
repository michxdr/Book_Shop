# Temporary settings for SQLite data export
# Used only by migrate_sqlite_to_postgres.sh
from book_shop.settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
