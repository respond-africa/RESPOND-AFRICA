from edc_consent import site_consents
from edc_consent.consent import Consent
from edc_constants.constants import FEMALE, MALE
from edc_protocol import Protocol

v1_consent = Consent(
    "respond_test_app.subjectconsent",
    version="1",
    start=Protocol().study_open_datetime,
    end=Protocol().study_close_datetime,
    age_min=18,
    age_is_adult=18,
    age_max=64,
    gender=[MALE, FEMALE],
)
site_consents.register(v1_consent)
