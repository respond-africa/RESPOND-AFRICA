from django.db import models
from edc_clinic.choices import GLUCOSE_UNITS
from edc_constants.choices import YES_NO, YES_NO_NA
from edc_constants.constants import NOT_APPLICABLE
from edc_lab.choices import GLUCOSE_UNITS_NA, RESULT_QUANTIFIER_NA
from edc_model.models import date_not_future


class GlucoseModelMixin(models.Model):
    glucose_date = models.DateField(
        validators=[date_not_future],
        null=True,
        blank=True,
    )

    glucose_fasted = models.CharField(
        verbose_name="Has the participant fasted?",
        max_length=15,
        choices=YES_NO_NA,
        default=NOT_APPLICABLE,
    )

    glucose = models.DecimalField(
        verbose_name="Glucose result",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    glucose_quantifier = models.CharField(
        max_length=10,
        choices=RESULT_QUANTIFIER_NA,
        default=NOT_APPLICABLE,
    )

    glucose_units = models.CharField(
        verbose_name="Units (glucose)",
        max_length=15,
        choices=GLUCOSE_UNITS_NA,
        default=NOT_APPLICABLE,
    )

    class Meta:
        abstract = True
