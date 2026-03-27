import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import RegisterForm, LoginForm, ProfileForm
from .models import CustomUser

logger = logging.getLogger('accounts')


class RegisterView(CreateView):
    model = CustomUser
    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('books:book_list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('books:book_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        login(self.request, user)
        logger.info('Новий користувач зареєстрований: %s', user.username)
        messages.success(self.request, f'Ласкаво просимо, {user.username}!')
        return response


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'accounts/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('books:book_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        logger.info('Користувач увійшов: %s', form.get_user().username)
        messages.success(self.request, 'Ви успішно увійшли!')
        return super().form_valid(form)


def logout_view(request):
    if request.user.is_authenticated:
        logger.info('Користувач вийшов: %s', request.user.username)
        messages.info(request, 'Ви вийшли з системи.')
    logout(request)
    return redirect('accounts:login')


class ProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Профіль оновлено.')
        return super().form_valid(form)
