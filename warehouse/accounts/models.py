from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    ROLE_STAFF = 'staff'
    ROLE_MANAGER = 'manager'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_STAFF, _('Працівник складу')),
        (ROLE_MANAGER, _('Менеджер')),
        (ROLE_ADMIN, _('Адміністратор')),
    ]

    role = models.CharField(
        _('Роль'),
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STAFF,
    )
    department = models.CharField(
        _('Відділ'),
        max_length=100,
        blank=True,
    )
    phone = models.CharField(
        _('Телефон'),
        max_length=20,
        blank=True,
    )

    class Meta:
        verbose_name = _('Користувач')
        verbose_name_plural = _('Користувачі')

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_manager(self):
        return self.role in (self.ROLE_MANAGER, self.ROLE_ADMIN)
