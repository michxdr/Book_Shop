from django import forms
from .models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'price', 'description', 'stock', 'categories']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'categories':  forms.CheckboxSelectMultiple(),
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'author':      forms.TextInput(attrs={'class': 'form-control'}),
            'price':       forms.NumberInput(attrs={'class': 'form-control'}),
            'stock':       forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title':       'Назва книги',
            'author':      'Автор',
            'price':       'Ціна (грн)',
            'description': 'Опис',
            'stock':       'Кількість на складі',
            'categories':  'Категорії',
        }
