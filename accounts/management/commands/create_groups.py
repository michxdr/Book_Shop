"""
Команда для створення груп з правами:
  - editors   : може додавати та редагувати книги/категорії
  - managers  : повний CRUD над книгами/категоріями

Використання:
    python manage.py create_groups
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from books.models import Book, Category


class Command(BaseCommand):
    help = 'Створює групи editors та managers з відповідними правами'

    def handle(self, *args, **options):
        book_ct = ContentType.objects.get_for_model(Book)
        cat_ct  = ContentType.objects.get_for_model(Category)

        # Всі права на книги та категорії
        all_perms = Permission.objects.filter(content_type__in=[book_ct, cat_ct])

        # Права лише на читання + додавання/зміна (без видалення)
        editor_perms = Permission.objects.filter(
            content_type__in=[book_ct, cat_ct],
            codename__in=[
                'add_book', 'change_book', 'view_book',
                'add_category', 'change_category', 'view_category',
            ],
        )

        editors, created = Group.objects.get_or_create(name='editors')
        editors.permissions.set(editor_perms)
        self.stdout.write(self.style.SUCCESS(
            f'{"Створено" if created else "Оновлено"} групу "editors"'
        ))

        managers, created = Group.objects.get_or_create(name='managers')
        managers.permissions.set(all_perms)
        self.stdout.write(self.style.SUCCESS(
            f'{"Створено" if created else "Оновлено"} групу "managers"'
        ))
