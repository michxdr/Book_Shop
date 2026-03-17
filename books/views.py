from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count, Avg

from .models import Book, Category
from .forms import BookForm


class BookListView(ListView):
    model = Book
    template_name = 'books/book_list.html'
    context_object_name = 'books'
    paginate_by = 6

    def get_queryset(self):
        qs = Book.objects.prefetch_related('categories')

        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(author__icontains=query))

        category_slug = self.request.GET.get('category', '')
        if category_slug:
            qs = qs.filter(categories__slug=category_slug)

        if self.request.GET.get('in_stock'):
            qs = qs.filter(stock__gt=0)

        sort_map = {
            'title':  'title',
            '-title': '-title',
            'price':  'price',
            '-price': '-price',
        }
        sort = self.request.GET.get('sort', 'title')
        return qs.order_by(sort_map.get(sort, 'title'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories']        = Category.objects.annotate(book_count=Count('books'))
        ctx['query']             = self.request.GET.get('q', '')
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['in_stock']          = self.request.GET.get('in_stock', '')
        ctx['sort']              = self.request.GET.get('sort', 'title')
        ctx['total']             = self.get_queryset().count()

        # Зберігаємо фільтри для посилань пагінації (без параметра page)
        get_copy = self.request.GET.copy()
        get_copy.pop('page', None)
        ctx['filter_params'] = get_copy.urlencode()

        return ctx


class BookDetailView(DetailView):
    model = Book
    template_name = 'books/book_detail.html'
    queryset = Book.objects.prefetch_related('categories')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['related'] = (
            Book.objects
            .filter(categories__in=self.object.categories.all())
            .exclude(pk=self.object.pk)
            .distinct()[:4]
        )
        return ctx


class BookCreateView(CreateView):
    model = Book
    form_class = BookForm
    template_name = 'books/book_form.html'
    success_url = reverse_lazy('books:book_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = 'Додати нову книгу'
        return ctx


class BookUpdateView(UpdateView):
    model = Book
    form_class = BookForm
    template_name = 'books/book_form.html'

    def get_success_url(self):
        return reverse_lazy('books:book_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f'Редагувати: {self.object.title}'
        return ctx


class BookDeleteView(DeleteView):
    model = Book
    template_name = 'books/book_confirm_delete.html'
    success_url = reverse_lazy('books:book_list')


class CategoryListView(ListView):
    model = Category
    template_name = 'books/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.annotate(
            book_count=Count('books'),
            avg_price=Avg('books__price'),
        ).order_by('name')
