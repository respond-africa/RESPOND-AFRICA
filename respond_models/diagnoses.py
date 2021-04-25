from datetime import date, datetime
from typing import Dict, Iterable, Optional, Type

from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from edc_constants.constants import YES
from edc_visit_tracking.stubs import SubjectVisitModelStub

from .constants import RESPOND_DIAGNOSIS_LABELS
from .stubs import (
    ClinicalReviewBaselineModelStub,
    ClinicalReviewModelStub,
    InitialReviewModelStub,
)


class InitialReviewRequired(Exception):
    pass


class MultipleInitialReviewsExist(Exception):
    pass


class ClinicalReviewBaselineRequired(Exception):
    pass


class DiagnosesError(Exception):
    pass


class Diagnoses:
    """
    Tightly coupled to models
    """

    def __init__(
        self,
        subject_identifier: str = None,
        report_datetime: datetime = None,
        subject_visit: SubjectVisitModelStub = None,
        lte: Optional[bool] = None,
        limit_to_single_condition_prefix=None,
    ) -> None:
        self.condition_prefix = (
            limit_to_single_condition_prefix.lower()
            if limit_to_single_condition_prefix
            else None
        )
        if subject_visit:
            if subject_identifier or report_datetime:
                raise DiagnosesError(
                    "Ambiguous parameters provided. Expected either "
                    "`subject_visit` or `subject_identifier, report_datetime`. Not both."
                )
            self.report_datetime = subject_visit.report_datetime
            self.subject_identifier = subject_visit.appointment.subject_identifier
        else:
            self.report_datetime = report_datetime
            self.subject_identifier = subject_identifier
        self.lte = lte

        for prefix in self.diagnosis_labels:
            setattr(self, f"{prefix}_dx", self.get_dx(prefix))

    @property
    def diagnosis_labels(self):
        if self.condition_prefix:
            return {
                k.lower(): v
                for k, v in RESPOND_DIAGNOSIS_LABELS.items()
                if k == self.condition_prefix
            }
        return RESPOND_DIAGNOSIS_LABELS

    def get_dx_by_model(self, instance: InitialReviewModelStub) -> str:
        dx = None
        for prefix in self.diagnosis_labels:
            if instance.__class__.__name__.lower().startswith(prefix):
                dx = getattr(self, f"{prefix}_dx")
                break
        if not dx:
            models_classes = [
                self.get_initial_review_model_cls(prefix)
                for prefix in RESPOND_DIAGNOSIS_LABELS
            ]
            raise DiagnosesError(f"Invalid. Expected an instance of one of {models_classes}")
        return dx

    def get_dx_date(self, prefix: str) -> Optional[date]:
        """Returns a dx date from the initial review for the condition.

        Raises if initial review does not exist."""
        prefix = prefix.lower()
        if self.initial_reviews.get(prefix):
            return self.initial_reviews.get(prefix).get_best_dx_date()
        return None

    def get_dx(self, prefix: str) -> Optional[str]:
        """Returns YES if any diagnoses for this condition otherwise None.

        References clinical_review_baseline

        name is `dm`, `hiv` or `htn`.
        """
        diagnoses = [
            getattr(self.clinical_review_baseline, f"{prefix.lower()}_dx") == YES,
            *[(getattr(obj, f"{prefix.lower()}_dx") == YES) for obj in self.clinical_reviews],
        ]
        if any(diagnoses):
            return YES
        return None

    @property
    def clinical_review_baseline(self) -> ClinicalReviewBaselineModelStub:
        try:
            obj = self.clinical_review_baseline_model_cls.objects.get(
                subject_visit__subject_identifier=self.subject_identifier,
            )
        except ObjectDoesNotExist:
            raise ClinicalReviewBaselineRequired(
                "Please complete "
                f"{self.clinical_review_baseline_model_cls._meta.verbose_name}."
            )
        return obj

    def report_datetime_opts(
        self, prefix: str = None, lte: bool = None
    ) -> Dict[str, datetime]:
        opts = {}
        prefix = prefix.lower() or ""
        if self.report_datetime:
            if lte or self.lte:
                opts.update({f"{prefix.lower()}report_datetime__lte": self.report_datetime})
            else:
                opts.update({f"{prefix.lower()}report_datetime__lt": self.report_datetime})
        return opts

    @property
    def clinical_reviews(self) -> Iterable[ClinicalReviewModelStub]:
        return self.clinical_review_model_cls.objects.filter(
            subject_visit__subject_identifier=self.subject_identifier,
            **self.report_datetime_opts("subject_visit__"),
        )

    # @property
    # def previous_subject_visit(self) -> Optional[SubjectVisitModelStub]:
    #     if self.report_datetime:
    #         return (
    #             self.subject_visit_model_cls.objects.filter(
    #                 subject_identifier=self.subject_identifier,
    #                 **self.report_datetime_opts(),
    #             )
    #             .order_by("report_datetime")
    #             .first()
    #         )
    #     return None

    # @property
    # def baseline_subject_visit(self):
    #     return (
    #         self.subject_visit_model_cls.objects.filter(
    #             subject_identifier=self.subject_identifier,
    #         )
    #         .order_by("report_datetime")
    #         .first()
    #     )

    def get_initial_reviews(self) -> Dict[str, InitialReviewModelStub]:
        return self.initial_reviews

    @property
    def initial_reviews(self) -> Dict[str, InitialReviewModelStub]:
        """Returns a dict of initial review model instances
        for each diagnosis.

        If any initial review is expected but does not exist,
        an expection is raised.
        """
        initial_reviews = {}

        options = []
        for prefix, label in self.diagnosis_labels.items():
            options.append(
                (
                    prefix,
                    getattr(self, f"{prefix.lower()}_dx"),
                    self.get_initial_review_model_cls(prefix),
                    f"{label.title()} diagnosis",
                )
            )
        for name, diagnosis, initial_review_model_cls, description in options:
            if diagnosis:
                extra_msg = description.title()
                try:
                    obj = initial_review_model_cls.objects.get(
                        subject_visit__subject_identifier=self.subject_identifier,
                        **self.report_datetime_opts("subject_visit__", lte=True),
                    )
                except ObjectDoesNotExist:
                    subject_visit = self.initial_diagnosis_visit(name)
                    if subject_visit:
                        visit_label = (
                            f"{subject_visit.visit_code}."
                            f"{subject_visit.visit_code_sequence}"
                        )
                        extra_msg = f"{description} was reported on visit {visit_label}. "
                    raise InitialReviewRequired(
                        f"{extra_msg}. Complete the "
                        f"`{initial_review_model_cls._meta.verbose_name}` CRF first."
                    )
                except MultipleObjectsReturned:
                    qs = initial_review_model_cls.objects.filter(
                        subject_visit__subject_identifier=self.subject_identifier,
                        **self.report_datetime_opts("subject_visit__", lte=True),
                    ).order_by(
                        "subject_visit__visit_code",
                        "subject_visit__visit_code_sequence",
                    )
                    visits_str = ", ".join(
                        [
                            (
                                f"{obj.subject_visit.visit_code}."
                                f"{obj.subject_visit.visit_code_sequence}"
                            )
                            for obj in qs
                        ]
                    )
                    raise MultipleInitialReviewsExist(
                        f"More than one `{initial_review_model_cls._meta.verbose_name}` "
                        f"has been submitted. "
                        f"This needs to be corrected. Try removing all but the first "
                        f"`{initial_review_model_cls._meta.verbose_name}` "
                        "before continuing. "
                        f"`{initial_review_model_cls._meta.verbose_name}` "
                        "CRFs have been submitted "
                        f"for visits {visits_str}"
                    )

                else:
                    initial_reviews.update({name: obj})
        return initial_reviews

    @staticmethod
    def get_initial_review_model_cls(prefix: str) -> Type[InitialReviewModelStub]:
        return django_apps.get_model(f"{settings.SUBJECT_APP_LABEL}.{prefix}initialreview")

    @property
    def clinical_review_model_cls(self) -> Type[ClinicalReviewModelStub]:
        return django_apps.get_model(f"{settings.SUBJECT_APP_LABEL}.clinicalreview")

    @property
    def clinical_review_baseline_model_cls(self) -> Type[ClinicalReviewBaselineModelStub]:
        return django_apps.get_model(f"{settings.SUBJECT_APP_LABEL}.clinicalreviewbaseline")

    @property
    def subject_visit_model_cls(self) -> Type[SubjectVisitModelStub]:
        return django_apps.get_model(f"{settings.SUBJECT_APP_LABEL}.subjectvisit")

    def initial_diagnosis_visit(self, prefix) -> Optional[SubjectVisitModelStub]:
        try:
            clinical_review_baseline = self.clinical_review_baseline_model_cls.objects.get(
                subject_visit__subject_identifier=self.subject_identifier,
                **self.report_datetime_opts("subject_visit__", lte=True),
                **{f"{prefix.lower()}_dx": YES},
            )
        except ObjectDoesNotExist:
            subject_visit = None
        else:
            subject_visit = clinical_review_baseline.subject_visit
        if not subject_visit:
            try:
                clinical_review = self.clinical_review_model_cls.objects.get(
                    subject_visit__subject_identifier=self.subject_identifier,
                    **self.report_datetime_opts("subject_visit__", lte=True),
                    **{f"{prefix.lower()}_dx": YES},
                )
            except ObjectDoesNotExist:
                subject_visit = None
            else:
                subject_visit = clinical_review.subject_visit
        return subject_visit
