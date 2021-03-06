from datetime import date
from typing import Optional, Type

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from edc_visit_schedule.utils import is_baseline
from edc_visit_tracking.stubs import SubjectVisitModelStub

from respond_models.utils import (
    get_clinical_review_baseline_model_cls,
    get_clinical_review_model_cls,
    get_initial_review_model_cls,
    get_medication_model_cls,
    get_review_model_cls,
)


def model_exists_or_raise(
    subject_visit: SubjectVisitModelStub,
    model_cls: Type[models.Model],
    singleton: Optional[bool] = None,
) -> bool:
    singleton = False if singleton is None else singleton
    if singleton:
        opts = {"subject_visit__subject_identifier": subject_visit.subject_identifier}
    else:
        opts = {"subject_visit": subject_visit}
    try:
        model_cls.objects.get(**opts)
    except ObjectDoesNotExist:
        raise forms.ValidationError(
            f"Complete the `{model_cls._meta.verbose_name}` CRF first."
        )
    return True


def validate_total_days(form: forms.ModelForm, return_in_days: Optional[int] = None) -> None:
    return_in_days = return_in_days or form.cleaned_data.get("return_in_days")
    if (
        form.cleaned_data.get("clinic_days")
        and form.cleaned_data.get("club_days")
        and form.cleaned_data.get("purchased_days")
        and int(return_in_days or 0)
    ):
        total = (
            form.cleaned_data.get("clinic_days")
            or 0 + form.cleaned_data.get("club_days")
            or 0 + form.cleaned_data.get("purchased_days")
            or 0
        )
        if total != int(return_in_days or 0):
            raise forms.ValidationError(
                f"Patient to return for a drug refill in {return_in_days} days. "
                "Check that the total days match."
            )


def raise_if_both_ago_and_actual_date(dx_ago: str, dx_date: date) -> None:
    if dx_ago and dx_date:
        raise forms.ValidationError(
            {
                "dx_ago": (
                    "Date conflict. Do not provide a response "
                    "here if the exact data of diagnosis is available."
                )
            }
        )


def raise_if_clinical_review_does_not_exist(subject_visit: SubjectVisitModelStub) -> None:
    if is_baseline(subject_visit):
        model_exists_or_raise(
            subject_visit=subject_visit,
            model_cls=get_clinical_review_baseline_model_cls(),
        )
    else:
        model_exists_or_raise(
            subject_visit=subject_visit, model_cls=get_clinical_review_model_cls()
        )


def requires_clinical_review_at_baseline(subject_visit: SubjectVisitModelStub):
    try:
        get_clinical_review_baseline_model_cls().objects.get(
            subject_visit__subject_identifier=subject_visit.subject_identifier
        )
    except ObjectDoesNotExist:
        raise forms.ValidationError(
            "Please complete the "
            f"{get_clinical_review_baseline_model_cls()._meta.verbose_name} first."
        )


def raise_if_initial_review_does_not_exist(subject_visit, prefix):
    model_exists_or_raise(
        subject_visit=subject_visit,
        model_cls=get_initial_review_model_cls(prefix),
    )


def raise_if_review_does_not_exist(subject_visit, prefix):
    model_exists_or_raise(
        subject_visit=subject_visit,
        model_cls=get_review_model_cls(prefix),
    )


def medications_exists_or_raise(subject_visit: SubjectVisitModelStub) -> bool:
    if subject_visit:
        try:
            get_medication_model_cls().objects.get(subject_visit=subject_visit)
        except ObjectDoesNotExist:
            raise forms.ValidationError(
                f"Complete the `{get_medication_model_cls()._meta.verbose_name}` CRF first."
            )
    return True
