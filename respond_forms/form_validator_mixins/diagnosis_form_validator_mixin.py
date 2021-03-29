from django import forms
from edc_constants.constants import YES
from edc_form_validators import FormValidator

from respond_models.diagnoses import (
    Diagnoses,
    InitialReviewRequired,
    MultipleInitialReviewsExist,
)


class DiagnosisFormValidatorMixin(FormValidator):
    def get_diagnoses(self) -> Diagnoses:
        diagnoses = Diagnoses(
            subject_identifier=self.subject_identifier,
            report_datetime=self.report_datetime,
        )
        try:
            diagnoses.get_initial_reviews()
        except InitialReviewRequired as e:
            raise forms.ValidationError(e)
        except MultipleInitialReviewsExist as e:
            raise forms.ValidationError(e)
        return diagnoses

    def applicable_if_not_diagnosed(
        self, diagnoses=None, field_dx=None, field_applicable=None, label=None
    ) -> bool:
        diagnoses = diagnoses or self.get_diagnoses()
        # htn
        return self.applicable_if_true(
            getattr(diagnoses, field_dx) != YES,
            field_applicable=field_applicable,
            applicable_msg=(
                f"Patient was not previously diagnosed with {label}. " "Expected YES or NO."
            ),
            not_applicable_msg=f"Patient was previously diagnosed with {label}.",
        )

    def applicable_if_diagnosed(
        self, diagnoses=None, field_dx=None, field_applicable=None, label=None
    ) -> bool:
        diagnoses = diagnoses or self.get_diagnoses()
        # htn
        return self.applicable_if_true(
            getattr(diagnoses, field_dx) == YES,
            field_applicable=field_applicable,
            applicable_msg=(
                f"Patient was previously diagnosed with {label}. " "Expected YES or NO."
            ),
            not_applicable_msg=f"Patient was not previously diagnosed with {label}.",
        )
