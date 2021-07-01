from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from edc_lab.choices import GLUCOSE_UNITS, RESULT_QUANTIFIER
from edc_lab.constants import EQ


class IfgModelMixin(models.Model):
    # IFG
    ifg_value = models.DecimalField(
        verbose_name=format_html("IFG level"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    ifg_quantifier = models.CharField(
        verbose_name=format_html("IFG quantifier"),
        max_length=10,
        choices=RESULT_QUANTIFIER,
        default=EQ,
    )

    ifg_units = models.CharField(
        verbose_name="IFG units",
        max_length=15,
        choices=GLUCOSE_UNITS,
        blank=True,
        null=True,
    )

    ifg_datetime = models.DateTimeField(
        verbose_name=mark_safe("<u>Time</u> IFG level measured"),
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True
