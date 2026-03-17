from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from .models import Book, Category


# ─────────────────────────────────────────
# Inline — книги всередині категорії
# ─────────────────────────────────────────
class BookInline(admin.TabularInline):
    model = Book.categories.through  # проміжна M2M таблиця
    extra = 1                         # 1 порожній рядок для додавання
    verbose_name = 'Книга'
    verbose_name_plural = 'Книги в категорії'


# ─────────────────────────────────────────
# Адмінка для Category
# ─────────────────────────────────────────
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display       = ('name', 'slug', 'book_count')
    prepopulated_fields = {'slug': ('name',)}  # slug заповнюється автоматично
    search_fields      = ('name',)
    inlines            = [BookInline]

    def book_count(self, obj):
        return obj.book_count
    book_count.short_description = 'Кількість книг'
    book_count.admin_order_field = 'book_count'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(book_count=Count('books'))


# ─────────────────────────────────────────
# Адмінка для Book
# ─────────────────────────────────────────
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display    = ('title', 'author', 'price', 'stock', 'availability_badge')
    list_filter     = ('categories', 'created_at')
    search_fields   = ('title', 'author', 'description')
    list_editable   = ('price', 'stock')
    filter_horizontal = ('categories',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page   = 25

    fieldsets = (
        ('Основна інформація', {
            'fields': ('title', 'author', 'description')
        }),
        ('Ціна та склад', {
            'fields': ('price', 'stock'),
        }),
        ('Категорії', {
            'fields': ('categories',),
        }),
        ('Дати', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),  # згортається
        }),
    )

    def availability_badge(self, obj):
        if obj.stock > 10:
            color, label = 'green', '✅ В наявності'
        elif obj.stock > 0:
            color, label = 'orange', '⚠️ Мало'
        else:
            color, label = 'red', '❌ Немає'
        return format_html(
            '<span style="color:{}; font-weight:bold">{}</span>',
            color, label
        )
    availability_badge.short_description = 'Наявність'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('categories')