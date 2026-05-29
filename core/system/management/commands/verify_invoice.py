from collections import defaultdict

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.models import DeliveryLocation, Route

FACTURAPI_BASE_URL = "https://www.facturapi.io/v2"
API_KEY = settings.FACTURAPI_API_KEY

facturas = [
  {"factura":"21758","monto":22170.40},
  {"factura":"21803","monto":20221.60},
  {"factura":"21801","monto":25670.40},
  {"factura":"21804","monto":25821.60},
  {"factura":"21805","monto":22170.40},
  {"factura":"21802","monto":23357.60},
  {"factura":"21806","monto":15148.00},
  {"factura":"21810","monto":20188.00},
  {"factura":"21807","monto":13048.00},
  {"factura":"21808","monto":14067.20},
  {"factura":"21809","monto":28470.40},
  {"factura":"21812","monto":18088.00},
  {"factura":"21820","monto":15848.00},
  {"factura":"21813","monto":20871.20},
  {"factura":"21814","monto":25670.40},
  {"factura":"21817","monto":18541.60},
  {"factura":"21815","monto":25670.40},
  {"factura":"21816","monto":24057.60},
  {"factura":"21818","monto":25670.40},
  {"factura":"21819","monto":18771.20},
  {"factura":"21821","monto":22310.40},
  {"factura":"21851","monto":25670.40},
  {"factura":"21823","monto":20188.00},
  {"factura":"21852","monto":24970.40},
  {"factura":"21825","monto":25821.60},
  {"factura":"21826","monto":22170.40},
  {"factura":"21853","monto":22954.40},
  {"factura":"21858","monto":22321.60},
  {"factura":"21859","monto":27070.40},
  {"factura":"21854","monto":26521.60},
  {"factura":"21855","monto":25670.40},
  {"factura":"21857","monto":9072.00},
  {"factura":"21880","monto":15148.00},
  {"factura":"21902","monto":18967.20},
  {"factura":"21903","monto":15848.00},
  {"factura":"21881","monto":17791.20},
  {"factura":"21882","monto":25457.60},
  {"factura":"21883","monto":28470.40},
  {"factura":"21884","monto":18267.20},
  {"factura":"21885","monto":22562.40},
  {"factura":"21904","monto":23604.00},
  {"factura":"21886","monto":22170.40},
  {"factura":"21894","monto":22657.60},
  {"factura":"21895","monto":18121.60},
  {"factura":"21896","monto":19157.60},
  {"factura":"21899","monto":27070.40},
  {"factura":"21887","monto":9072.00},
  {"factura":"21888","monto":25670.40},
  {"factura":"21897","monto":24757.60},
  {"factura":"21889","monto":16262.40},
  {"factura":"21898","monto":17567.20},
  {"factura":"21890","monto":17057.60},
  {"factura":"21933","monto":20188.00},
  {"factura":"21926","monto":20188.00},
  {"factura":"21963","monto":19348.00},
  {"factura":"21932","monto":18088.00},
  {"factura":"21936","monto":17057.60},
  {"factura":"21927","monto":20221.60},
  {"factura":"21928","monto":15041.60},
  {"factura":"21929","monto":13048.00},
  {"factura":"21930","monto":20070.40},
  {"factura":"21906","monto":15904.00},
  {"factura":"21931","monto":26521.60},
  {"factura":"21907","monto":13048.00},
  {"factura":"21908","monto":22657.60},
  {"factura":"21939","monto":25670.40},
  {"factura":"21940","monto":20070.40},
  {"factura":"21941","monto":20070.40},
  {"factura":"21909","monto":30710.40},
  {"factura":"21910","monto":20221.60},
  {"factura":"21942","monto":17248.00},
  {"factura":"21943","monto":25121.60},
  {"factura":"21944","monto":23441.60},
  {"factura":"21913","monto":22170.40},
  {"factura":"21920","monto":22657.60},
  {"factura":"21964","monto":28470.40},
  {"factura":"21915","monto":18088.00},
  {"factura":"21916","monto":18362.40},
  {"factura":"21917","monto":15148.00},
  {"factura":"21918","monto":17567.20},
  {"factura":"21919","monto":20188.00}
]

uuids = [
  {
    "uuid": "B9148B15-02EE-4B2F-8046-E0B3B1D11426",
    "monto": 28470.4
  },
  {
    "uuid": "79254B5B-00EC-450B-B7CD-5216BF46E67E",
    "monto": 20188
  },
  {
    "uuid": "B64674F6-FE7A-4D9F-A45A-E3835B6B14E1",
    "monto": 17567.2
  },
  {
    "uuid": "8CBBC9FC-3A76-4F0A-AC0D-E43BC52E003F",
    "monto": 15148
  },
  {
    "uuid": "610943A7-042C-459D-A2C6-2597FB27000F",
    "monto": 18362.4
  },
  {
    "uuid": "397B3633-1173-4178-84B5-66B93FEE53C8",
    "monto": 18088
  },
  {
    "uuid": "6B5B1A49-E899-4DD3-802F-FB1A3ED58F28",
    "monto": 22657.6
  },
  {
    "uuid": "15540542-614C-4285-9DAB-90A5C610063A",
    "monto": 22170.4
  },
  {
    "uuid": "4C479C1E-78A3-454E-ACF5-D3881C2537A3",
    "monto": 23441.6
  },
  {
    "uuid": "5A00F16C-F2AE-49F5-927A-1CB45DCAD108",
    "monto": 25121.6
  },
  {
    "uuid": "CFB82309-4765-4248-A95F-5612EB13F5C1",
    "monto": 17248
  },
  {
    "uuid": "EB4811A6-1EDA-4E47-A0A6-9501BC52025B",
    "monto": 20221.6
  },
  {
    "uuid": "69C3D5DD-C156-443D-9C6A-74D09D661838",
    "monto": 30710.4
  },
  {
    "uuid": "0848E534-8688-4D5D-895A-45B4F23CABD0",
    "monto": 20070.4
  },
  {
    "uuid": "F3FCB772-FB4E-436F-9F87-B06E065B512E",
    "monto": 20070.4
  },
  {
    "uuid": "0264AA6A-4705-4F8A-AE12-CCA7835C1AA2",
    "monto": 25670.4
  },
  {
    "uuid": "3632B425-66B3-48E6-A606-818E5AB06ABE",
    "monto": 22657.6
  },
  {
    "uuid": "35611AE3-3264-4C1F-B608-D5C168BD4FAF",
    "monto": 13048
  },
  {
    "uuid": "14AAD78A-B8D8-447E-9E4C-6E0B2DF3DC48",
    "monto": 26521.6
  },
  {
    "uuid": "DE16B894-0380-4000-9D02-56B97C027DC1",
    "monto": 15904
  },
  {
    "uuid": "9C4DDB6F-41F5-494A-8D19-B73CFE80B3A5",
    "monto": 20070.4
  },
  {
    "uuid": "FF3645D0-EE14-4708-A293-39D466A61065",
    "monto": 13048
  },
  {
    "uuid": "2FB4753B-5540-4E32-A5E5-F000855C2636",
    "monto": 15041.6
  },
  {
    "uuid": "139B66A7-B692-4706-B84A-EE02C0B0A8D3",
    "monto": 20221.6
  },
  {
    "uuid": "4CEB4339-8360-4C1A-8DFA-A0ABC0FF66E0",
    "monto": 17057.6
  },
  {
    "uuid": "272B9596-7DF2-42E4-B712-E82A46DE622D",
    "monto": 18088
  },
  {
    "uuid": "27FAFB04-FDA8-46B4-BED5-FFE8A82C5DC4",
    "monto": 19348
  },
  {
    "uuid": "0E1D269F-2AB1-49ED-9D1C-E9AC9C00FC56",
    "monto": 20188
  },
  {
    "uuid": "95F5F4D8-6C87-49BD-8880-88C2CB67B14E",
    "monto": 20188
  },
  {
    "uuid": "2C24F0A2-070C-4800-B28B-18E57439A8DD",
    "monto": 17057.6
  },
  {
    "uuid": "022B6648-8A48-4825-90AA-62D061AB1B0C",
    "monto": 17567.2
  },
  {
    "uuid": "A3B59CE0-C2B2-4A2C-814D-2E3FE696A363",
    "monto": 16262.4
  },
  {
    "uuid": "36A825FC-B71E-431A-96F1-C335002C3ABD",
    "monto": 24757.6
  },
  {
    "uuid": "B998CAC3-B0A0-456E-8EEB-D3F403974C16",
    "monto": 25670.4
  },
  {
    "uuid": "A60C5A3D-6F6C-4DB1-9C8D-39F3ED31176C",
    "monto": 9072
  },
  {
    "uuid": "42B8ECC6-00A9-4897-BB02-2B8924AA3BAE",
    "monto": 27070.4
  },
  {
    "uuid": "4F9DAEA0-DDD2-48CD-8BF3-01708B24818A",
    "monto": 19157.6
  },
  {
    "uuid": "32CF1059-E217-4846-9416-5CF809ACCA27",
    "monto": 18121.6
  },
  {
    "uuid": "933BF2A3-31BA-42FC-9730-6E76028EF616",
    "monto": 22657.6
  },
  {
    "uuid": "3695B9D0-9D92-40D8-81CD-0181399D4E13",
    "monto": 22170.4
  },
  {
    "uuid": "00E3AE0F-C86B-4415-825A-1480714A0A02",
    "monto": 23604
  },
  {
    "uuid": "FE9A5D66-D51E-4CB2-A6E7-E263A88FB52A",
    "monto": 22562.4
  },
  {
    "uuid": "3CF6AB73-8641-4B80-BF6A-AA78EBB8770F",
    "monto": 18267.2
  },
  {
    "uuid": "636DB5DA-7674-4526-8AE9-8440AF34001C",
    "monto": 28470.4
  },
  {
    "uuid": "8E01410F-F8D5-4928-92D7-270A509DCB1C",
    "monto": 25457.6
  },
  {
    "uuid": "D021F467-6C31-4C7A-AC5D-E08C402633D0",
    "monto": 17791.2
  },
  {
    "uuid": "89254BBE-316C-4A2F-AA8E-7750C94FB111",
    "monto": 15848
  },
  {
    "uuid": "5C9D8B4B-ACC4-4791-9FC7-726C0A111667",
    "monto": 18967.2
  },
  {
    "uuid": "1840DFE9-0B76-4BAA-A32A-46CED1AE0EA6",
    "monto": 15148
  },
  {
    "uuid": "D457215A-7286-4752-BF0F-67BA5CE7AC6D",
    "monto": 9072
  },
  {
    "uuid": "B9D5B386-919C-48BA-9722-7224B2931265",
    "monto": 25670.4
  },
  {
    "uuid": "1838A107-321B-4E02-A4A6-6A756C286C3D",
    "monto": 26521.6
  },
  {
    "uuid": "9142FF49-2E3F-4EA2-B402-79FC44113A8A",
    "monto": 27070.4
  },
  {
    "uuid": "EB4240BD-57B4-4EF2-B929-7687FFCAD1BD",
    "monto": 22321.6
  },
  {
    "uuid": "EC3D940F-581B-418A-BF53-1026E78DED2E",
    "monto": 22954.4
  },
  {
    "uuid": "984F3DCE-84DD-446A-B946-DE5FC6A213B2",
    "monto": 22170.4
  },
  {
    "uuid": "124EE163-1BC1-4AFD-A6FE-FD497E1F1B40",
    "monto": 25821.6
  },
  {
    "uuid": "CEB4BC99-4F8B-445E-8096-FD8E223C17A8",
    "monto": 24970.4
  },
  {
    "uuid": "4A4388E8-70C0-4784-8420-957CB83D2940",
    "monto": 20188
  },
  {
    "uuid": "6ACF1859-CB3F-4E1C-BE68-40B5C2E41969",
    "monto": 25670.4
  },
  {
    "uuid": "F6BB84C0-24AE-4E2E-B00A-41000E6B8102",
    "monto": 22310.4
  },
  {
    "uuid": "75CE3FA8-13B0-42C7-9105-288909BF00C8",
    "monto": 18771.2
  },
  {
    "uuid": "FAFA4F40-887D-4F85-9F45-DDEF2B6EA68C",
    "monto": 25670.4
  },
  {
    "uuid": "0C1EC458-4B69-45F8-AB51-9191A28E46B7",
    "monto": 24057.6
  },
  {
    "uuid": "93EFA67B-FC27-471B-AEC7-ADEB83BB9BBE",
    "monto": 25670.4
  },
  {
    "uuid": "4FAA234A-67BB-4686-A5FF-A60E68F17B2C",
    "monto": 18541.6
  },
  {
    "uuid": "8276AA5C-9521-4B91-B3A7-28FEDA96F9BC",
    "monto": 25670.4
  },
  {
    "uuid": "49FEA56D-3F7D-46C0-AD7B-92411B6EE735",
    "monto": 20871.2
  },
  {
    "uuid": "FC1191D3-0BAC-41C3-81CB-94DB5EABA3B5",
    "monto": 15848
  },
  {
    "uuid": "1AE0A5DE-08DB-49B2-B872-36910A1FFD7F",
    "monto": 18088
  },
  {
    "uuid": "DE4FC4E4-F857-43A2-AECE-FA9C0BD0D88D",
    "monto": 28470.4
  },
  {
    "uuid": "85EA1D15-8693-4399-B1E9-FF5A5C4E4E87",
    "monto": 14067.2
  },
  {
    "uuid": "7188CF61-A5FC-4035-8E88-3F91CBF597AD",
    "monto": 13048
  },
  {
    "uuid": "F566B65E-6796-48E4-ABCA-3C07F6743A9C",
    "monto": 20188
  },
  {
    "uuid": "C0F64B56-4E4B-4883-9F6C-823E60F089CD",
    "monto": 15148
  },
  {
    "uuid": "33281E05-7EAA-4783-A98B-B6A372E308F0",
    "monto": 23357.6
  },
  {
    "uuid": "5488F214-2035-4BC6-87FA-15775AE36303",
    "monto": 22170.4
  },
  {
    "uuid": "5703BA88-59BC-4090-811A-649C7026D6A9",
    "monto": 25821.6
  },
  {
    "uuid": "00F6E53D-EAF4-4B6A-97D2-EEC2F1424842",
    "monto": 25670.4
  },
  {
    "uuid": "527656EB-3B13-41E1-8F20-6C8AECD5C341",
    "monto": 20221.6
  },
  {
    "uuid": "803DDA04-01D0-4925-963F-F77C1EB856E8",
    "monto": 22170.4
  }
]

class Command(BaseCommand):
    help = "Crea o actualiza rutas por Region-Zona y muestra resultados en consola"


    def handle(self, *args, **options):
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        })
        for invoice in facturas:
            _invoice = FacturapiInvoice.objects.get(folio_number=invoice["factura"])

            # Request a FacturAPI
            response = session.get(
                f"{FACTURAPI_BASE_URL}/invoices/{_invoice.facturapi_id}",
                timeout=60,
            )

            if response.status_code != 200:
                self.stdout.write(
                    self.style.ERROR(f"Error HTTP {response.status_code}: {response.text}")
                )
                return

            inv = response.json()

            ok = False
            for uuid in uuids:
                if uuid["uuid"] == _invoice.uuid:
                    if float(uuid["monto"]) == float(_invoice.total):
                        print("OK")
                        ok=True
                        continue

            if not ok:
                print("----------------------")
                print(_invoice.folio_number)
                print(_invoice.uuid)
                print(_invoice.total)

