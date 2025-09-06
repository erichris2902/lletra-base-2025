from core.operations_panel.models.distribution_packing import DistributionPacking
from core.system.forms import BaseModelForm


class DistributionPackingForm(BaseModelForm):
    class Meta:
        model = DistributionPacking
        fields = ['delivery_shop', 'distribution', 'weight', 'amount']