from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # Список та деталі
    path('',              views.BookListView.as_view(),   name='book_list'),
    path('<int:pk>/',     views.BookDetailView.as_view(), name='book_detail'),
    # CRUD
    path('create/',           views.BookCreateView.as_view(), name='book_create'),
    path('<int:pk>/update/',  views.BookUpdateView.as_view(), name='book_update'),
    path('<int:pk>/delete/',  views.BookDeleteView.as_view(), name='book_delete'),
    # Категорії
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
]
