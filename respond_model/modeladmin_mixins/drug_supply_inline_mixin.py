class DrugSupplyInlineMixin:
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj=None, **kwargs)
        formset.validate_min = True
        return formset

    extra = 1
    view_on_site = False

    fieldsets = (
        [
            "Drug Supply",
            {
                "description": (
                    "For each drug, please state for many days supply "
                    "did the participant receive from the pharmacy "
                    "and/or purchase themselves"
                ),
                "fields": ("drug", "clinic_days", "club_days", "purchased_days"),
            },
        ],
    )
