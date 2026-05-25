from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class StockItem(models.Model):
    """Tracks warehouse stock for a single book (referenced by ID in ProjectA)."""

    book_id = models.PositiveIntegerField(
        _('ID книги (ProjectA)'),
        unique=True,
        db_index=True,
    )
    book_title = models.CharField(_('Назва книги'), max_length=255)
    book_isbn = models.CharField(_('ISBN'), max_length=20, blank=True)

    quantity = models.PositiveIntegerField(
        _('Кількість на складі'),
        default=0,
        validators=[MinValueValidator(0)],
    )
    reserved_quantity = models.PositiveIntegerField(
        _('Зарезервована кількість'),
        default=0,
        validators=[MinValueValidator(0)],
    )
    low_stock_threshold = models.PositiveIntegerField(
        _('Поріг низького запасу'),
        default=5,
    )
    location = models.CharField(
        _('Місце на складі'),
        max_length=50,
        blank=True,
        help_text=_('Наприклад: A1-23'),
    )
    unit_cost = models.DecimalField(
        _('Собівартість одиниці'),
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    last_synced_at = models.DateTimeField(
        _('Останній синхронізований'),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_('Створено'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Оновлено'), auto_now=True)

    class Meta:
        verbose_name = _('Позиція на складі')
        verbose_name_plural = _('Позиції на складі')
        ordering = ['book_title']
        permissions = [
            ('can_adjust_stock', 'Can manually adjust stock quantities'),
            ('can_view_analytics', 'Can view warehouse analytics'),
        ]

    def __str__(self):
        return f'{self.book_title} (qty: {self.available_quantity})'

    @property
    def available_quantity(self):
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self):
        return self.available_quantity <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.available_quantity == 0


class StockMovement(models.Model):
    """Audit log of every quantity change on a StockItem."""

    TYPE_RECEIPT = 'receipt'
    TYPE_SALE = 'sale'
    TYPE_RETURN = 'return'
    TYPE_ADJUSTMENT = 'adjustment'
    TYPE_RESERVATION = 'reservation'
    TYPE_RELEASE = 'release'
    TYPE_CHOICES = [
        (TYPE_RECEIPT, _('Надходження')),
        (TYPE_SALE, _('Продаж')),
        (TYPE_RETURN, _('Повернення')),
        (TYPE_ADJUSTMENT, _('Коригування')),
        (TYPE_RESERVATION, _('Резервування')),
        (TYPE_RELEASE, _('Звільнення резерву')),
    ]

    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name=_('Позиція'),
    )
    movement_type = models.CharField(
        _('Тип руху'),
        max_length=20,
        choices=TYPE_CHOICES,
    )
    quantity = models.IntegerField(
        _('Кількість'),
        help_text=_('Позитивне — надходження, негативне — видатки'),
    )
    reference_id = models.CharField(
        _('Референс (ID замовлення ProjectA)'),
        max_length=100,
        blank=True,
    )
    note = models.TextField(_('Примітка'), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name=_('Виконав'),
    )
    created_at = models.DateTimeField(_('Дата/час'), auto_now_add=True)

    class Meta:
        verbose_name = _('Рух запасів')
        verbose_name_plural = _('Рух запасів')
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.quantity >= 0 else ''
        return f'{self.stock_item.book_title}: {sign}{self.quantity} ({self.get_movement_type_display()})'


class WarehouseAlert(models.Model):
    """Alerts generated when stock falls below threshold."""

    ALERT_LOW_STOCK = 'low_stock'
    ALERT_OUT_OF_STOCK = 'out_of_stock'
    ALERT_OVERSTOCK = 'overstock'
    ALERT_CHOICES = [
        (ALERT_LOW_STOCK, _('Низький запас')),
        (ALERT_OUT_OF_STOCK, _('Відсутній на складі')),
        (ALERT_OVERSTOCK, _('Надлишковий запас')),
    ]

    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name=_('Позиція'),
    )
    alert_type = models.CharField(
        _('Тип сповіщення'),
        max_length=20,
        choices=ALERT_CHOICES,
    )
    message = models.TextField(_('Повідомлення'))
    is_resolved = models.BooleanField(_('Вирішено'), default=False)
    resolved_at = models.DateTimeField(_('Вирішено о'), null=True, blank=True)
    created_at = models.DateTimeField(_('Створено'), auto_now_add=True)

    class Meta:
        verbose_name = _('Попередження складу')
        verbose_name_plural = _('Попередження складу')
        ordering = ['-created_at']

    def __str__(self):
        status = '[RESOLVED]' if self.is_resolved else '[OPEN]'
        return f'{status} {self.stock_item.book_title}: {self.get_alert_type_display()}'
