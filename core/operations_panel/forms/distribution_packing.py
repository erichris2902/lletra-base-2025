from core.operations_panel.models.distribution_packing import DistributionPacking
from core.system.forms import BaseModelForm


class DistributionPackingForm(BaseModelForm):
    class Meta:
        model = DistributionPacking
        fields = ['delivery_shop', 'distribution', 'weight', 'amount']


class DistributionPacking2Form(BaseModelForm):
    class Meta:
        model = DistributionPacking
        fields = [
            'delivery_shop',
            "cajas_ab",
            'weight_ab_cajas',
            'bolsas_ab',
            'weight_ab_bolsas',
            'cajas_cvz',
            'weight_cvz_cajas',
            'bolsas_cvz',
            'weight_cvz_bolsas',
        ]
