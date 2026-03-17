from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name='Назва')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='Slug')

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Автоматично генеруємо slug з назви
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Book(models.Model):
    title       = models.CharField(max_length=300, verbose_name='Назва книги')
    author      = models.CharField(max_length=200, verbose_name='Автор')
    price       = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Ціна (грн)')
    description = models.TextField(blank=True, verbose_name='Опис')
    stock       = models.PositiveIntegerField(default=0, verbose_name='На складі')
    categories  = models.ManyToManyField(
        Category,
        blank=True,
        related_name='books',
        verbose_name='Категорії'
    )
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    updated_at  = models.DateTimeField(auto_now=True,     verbose_name='Оновлено')

    class Meta:
        verbose_name = 'Книга'
        verbose_name_plural = 'Книги'
        ordering = ['title']

    def __str__(self):
        return f'{self.title} — {self.author}'

    @property
    def is_available(self):
        return self.stock > 0