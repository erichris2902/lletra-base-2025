from core.operations_panel.models.distribution_packing import DistributionPacking
from core.system.forms import BaseModelForm


class DistributionPackingForm(BaseModelForm):
    class Meta:
        model = DistributionPacking
        fields = ['delivery_shop', 'distribution', 'weight', 'amount']

class DistributionPacking2Form(BaseModelForm):
    class Meta:
        model = DistributionPacking
        fields = ['delivery_shop',
                  "cajas_ab",
                  'bolsas_ab',
                  'weight_ab_bolsas',
                  'weight_ab_cajas',
                  'cajas_cvz',
                  'bolsas_cvz',
                  'weight_cvz_bolsas',
                  'weight_cvz_cajas',
                  ]