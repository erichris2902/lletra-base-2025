from django.db import models
from packaging.utils import _

_PAYMENT_FORMS = [
    {'Name': 'Efectivo', 'Value': '01'},
    {'Name': 'Cheque nominativo', 'Value': '02'},
    {'Name': 'Transferencia electrónica de fondos', 'Value': '03'},
    {'Name': 'Tarjeta de crédito', 'Value': '04'},
    {'Name': 'Monedero electrónico', 'Value': '05'},
    {'Name': 'Dinero electrónico', 'Value': '06'},
    {'Name': 'Vales de despensa', 'Value': '08'},
    {'Name': 'Dación en pago', 'Value': '12'},
    {'Name': 'Pago por subrogación', 'Value': '13'},
    {'Name': 'Pago por consignación', 'Value': '14'},
    {'Name': 'Condonación', 'Value': '15'},
    {'Name': 'Compensación', 'Value': '17'},
    {'Name': 'Novación', 'Value': '23'},
    {'Name': 'Confusión', 'Value': '24'},
    {'Name': 'Remisión de deuda', 'Value': '25'},
    {'Name': 'Prescripción o caducidad', 'Value': '26'},
    {'Name': 'A satisfacción del acreedor', 'Value': '27'},
    {'Name': 'Tarjeta de débito', 'Value': '28'},
    {'Name': 'Tarjeta de servicios', 'Value': '29'},
    {'Name': 'Aplicación de anticipos', 'Value': '30'},
    {'Name': 'Intermediarios', 'Value': '31'},
    {'Name': 'Por definir', 'Value': '99'}
]
_CFDI_USE = [
    {'Natural': True, 'Moral': False, 'Name': 'Honorarios médicos, dentales y gastos hospitalarios.', 'Value': 'D01'},
    {'Natural': True, 'Moral': False, 'Name': 'Gastos médicos por incapacidad o discapacidad', 'Value': 'D02'},
    {'Natural': True, 'Moral': False, 'Name': 'Gastos funerales.', 'Value': 'D03'},
    {'Natural': True, 'Moral': False, 'Name': 'Donativos.', 'Value': 'D04'},
    {'Natural': True, 'Moral': False,
     'Name': 'Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación).', 'Value': 'D05'},
    {'Natural': True, 'Moral': False, 'Name': 'Aportaciones voluntarias al SAR.', 'Value': 'D06'},
    {'Natural': True, 'Moral': False, 'Name': 'Primas por seguros de gastos médicos.', 'Value': 'D07'},
    {'Natural': True, 'Moral': False, 'Name': 'Gastos de transportación escolar obligatoria.', 'Value': 'D08'},
    {'Natural': True, 'Moral': False,
     'Name': 'Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones.', 'Value': 'D09'},
    {'Natural': True, 'Moral': False, 'Name': 'Pagos por servicios educativos (colegiaturas)', 'Value': 'D10'},
    {'Natural': True, 'Moral': True, 'Name': 'Adquisición de mercancias', 'Value': 'G01'},
    {'Natural': True, 'Moral': True, 'Name': 'Devoluciones, descuentos o bonificaciones', 'Value': 'G02'},
    {'Natural': True, 'Moral': True, 'Name': 'Gastos en general', 'Value': 'G03'},
    {'Natural': True, 'Moral': True, 'Name': 'Construcciones', 'Value': 'I01'},
    {'Natural': True, 'Moral': True, 'Name': 'Mobilario y equipo de oficina por inversiones', 'Value': 'I02'},
    {'Natural': True, 'Moral': True, 'Name': 'Equipo de transporte', 'Value': 'I03'},
    {'Natural': True, 'Moral': True, 'Name': 'Equipo de computo y accesorios', 'Value': 'I04'},
    {'Natural': True, 'Moral': True, 'Name': 'Dados, troqueles, moldes, matrices y herramental', 'Value': 'I05'},
    {'Natural': True, 'Moral': True, 'Name': 'Comunicaciones telefónicas', 'Value': 'I06'},
    {'Natural': True, 'Moral': True, 'Name': 'Comunicaciones satelitales', 'Value': 'I07'},
    {'Natural': True, 'Moral': True, 'Name': 'Otra maquinaria y equipo', 'Value': 'I08'},
    {'Natural': True, 'Moral': True, 'Name': 'Por definir', 'Value': 'P01'}
]
_CFDI_TYPES = [
    {'NameId': 1, 'Name': 'Factura', 'Value': 'I'},
    {'NameId': 2, 'Name': 'Nota de Crédito', 'Value': 'E'},
    {'NameId': 14, 'Name': 'Complemento de pago', 'Value': 'P'},
    {'NameId': 3, 'Name': 'Translado', 'Value': 'T'},
    {'NameId': 3, 'Name': 'Nomina', 'Value': 'N'},
]

CFDI_USE = []
PAYMENT_FORMS = []
CFDI_TYPES = []

for cfdi_use in _CFDI_USE:
    CFDI_USE.append((cfdi_use['Value'], cfdi_use['Name']))

for payment_method in _PAYMENT_FORMS:
    PAYMENT_FORMS.append((payment_method['Value'], payment_method['Value'] + ": " + payment_method['Name']))

for catalog in _CFDI_TYPES:
    CFDI_TYPES.append((catalog['Value'], catalog['Value'] + ": " + catalog['Name']))

PAYMENT_METHOD_CHOICES = (('PUE', 'PUE'), ('PPD', 'PPD'))


class CFDIRelationType(models.TextChoices):
    NOTA_CREDITO = '01', _('01 - Nota de crédito de los documentos relacionados')
    NOTA_DEBITO = '02', _('02 - Nota de débito de los documentos relacionados')
    DEVOLUCION = '03', _('03 - Devolución de mercancía sobre facturas o traslados previos')
    SUSTITUCION = '04', _('04 - Sustitución de los CFDI previos')
    TRASLADO = '05', _('05 - Traslados de mercancias facturados previamente')
    FACTURA_TRASLADO = '06', _('06 - Factura generada por los traslados previos')
    ANTICIPO = '07', _('07 - CFDI por aplicación de anticipo')
    PARCIALIDADES = '08', _('08 - Factura generada por pagos en parcialidades')
    DIFERIDOS = '09', _('09 - Factura generada por pagos diferidos')


class TaxFactorType(models.TextChoices):
    TASA = 'Tasa', _('Tasa')
    CUOTA = 'Cuota', _('Cuota')
    EXCENTO = 'Exento', _('Exento')


class TaxType(models.TextChoices):
    IVA = 'IVA', _('IVA')
    ISR = 'ISR', _('ISR')
    IEPS = 'IEPS', _('IEPS')


class TaxRegime(models.TextChoices):
    RF01 = '601', _('601 - General de Ley Personas Morales')
    RF02 = '603', _('603 - Personas Morales con Fines no Lucrativos')
    RF03 = '605', _('605 - Sueldos y Salarios e Ingresos Asimilados a Salarios')
    RF04 = '606', _('606 - Arrendamiento')
    RF05 = '607', _('607 - Régimen de Enajenación o Adquisición de Bienes')
    RF06 = '608', _('608 - Demás ingresos')
    RF07 = '609', _('609 - Consolidación')
    RF08 = '611', _('611 - Ingresos por Dividendos (socios y accionistas)')
    RF09 = '612', _('612 - Personas Físicas con Actividades Empresariales y Profesionales')
    RF10 = '614', _('614 - Ingresos por intereses')
    RF11 = '615', _('615 - Régimen de los ingresos por obtención de premios')
    RF12 = '616', _('616 - Sin obligaciones fiscales')
    RF13 = '620', _('620 - Sociedades Cooperativas de Producción que optan por Diferir sus Ingresos')
    RF14 = '621', _('621 - Incorporación Fiscal')
    RF15 = '622', _('622 - Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras')
    RF16 = '623', _('623 - Opcional para Grupos de Sociedades')
    RF17 = '624', _('624 - Coordinados')
    RF17A = '625', _('625 - Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas')
    RF17B = '626', _('626 - Régimen Simplificado de Confianza')
    RF18 = '628', _('628 - Hidrocarburos')
    RF19 = '629', _('629 - De los Regímenes Fiscales Preferentes y de las Empresas Multinacionales')
    RF20 = '630', _('630 - Enajenación de acciones en bolsa de valores')


class VehicleConfig(models.TextChoices):
    VL = 'VL', _('VL: Light cargo vehicle')
    C2 = 'C2', _('C2: Unit truck (2 front wheels, 4 rear wheels)')
    C3 = 'C3', _('C3: Unit truck (2 front wheels, 6–8 rear wheels)')
    C2R2 = 'C2R2', _('C2R2: Truck-Trailer (6 truck wheels, 8 trailer wheels)')
    C3R2 = 'C3R2', _('C3R2: Truck-Trailer (10 truck wheels, 8 trailer wheels)')
    C2R3 = 'C2R3', _('C2R3: Truck-Trailer (6 truck wheels, 12 trailer wheels)')
    C3R3 = 'C3R3', _('C3R3: Truck-Trailer (10 truck wheels, 12 trailer wheels)')
    T2S1 = 'T2S1', _('T2S1: Articulated tractor (6+4)')
    T2S2 = 'T2S2', _('T2S2: Articulated tractor (6+8)')
    T2S3 = 'T2S3', _('T2S3: Articulated tractor (6+12)')
    T3S1 = 'T3S1', _('T3S1: Articulated tractor (10+4)')
    T3S2 = 'T3S2', _('T3S2: Articulated tractor (10+8)')
    T3S3 = 'T3S3', _('T3S3: Articulated tractor (10+12)')
    T2S1R2 = 'T2S1R2', _('T2S1R2: Tractor-Semitrailer-Trailer (6+4+8)')
    T2S2R2 = 'T2S2R2', _('T2S2R2: Tractor-Semitrailer-Trailer (6+8+8)')
    T2S1R3 = 'T2S1R3', _('T2S1R3: Tractor-Semitrailer-Trailer (6+4+12)')
    T3S1R2 = 'T3S1R2', _('T3S1R2: Tractor-Semitrailer-Trailer (10+4+8)')
    T3S1R3 = 'T3S1R3', _('T3S1R3: Tractor-Semitrailer-Trailer (10+4+12)')
    T3S2R2 = 'T3S2R2', _('T3S2R2: Tractor-Semitrailer-Trailer (10+8+8)')
    T3S2R3 = 'T3S2R3', _('T3S2R3: Tractor-Semitrailer-Trailer (10+8+12)')
    T3S2R4 = 'T3S2R4', _('T3S2R4: Tractor-Semitrailer-Trailer (10+8+16)')
    T2S2S2 = 'T2S2S2', _('T2S2S2: Tractor-Semitrailer-Semitrailer (6+8+8)')
    T3S2S2 = 'T3S2S2', _('T3S2S2: Tractor-Semitrailer-Semitrailer (10+8+8)')
    T3S3S2 = 'T3S3S2', _('T3S3S2: Tractor-Semitrailer-Semitrailer (10+12+8)')
    OTHER_EV = 'OTROEV', _('OTROEV: Voluminous specialized')
    OTHER_EGP = 'OTROEGP', _('OTROEGP: Heavy load specialized')
    OTHER_SG = 'OTROSG', _('OTROSG: Crane service')
    CTR001 = 'CTR001', _('CTR001: Caballete')
    CTR002 = 'CTR002', _('CTR002: Box')
    CTR003 = 'CTR003', _('CTR003: Open Box')
    CTR004 = 'CTR004', _('CTR004: Closed Box')
    CTR005 = 'CTR005', _('CTR005: Front Loader Collection Box')
    CTR006 = 'CTR006', _('CTR006: Refrigerated Box')
    CTR007 = 'CTR007', _('CTR007: Dry Box')
    CTR008 = 'CTR008', _('CTR008: Transfer Box')
    CTR009 = 'CTR009', _('CTR009: Low Bed')
    CTR010 = 'CTR010', _('CTR010: Container Chassis')
    CTR011 = 'CTR011', _('CTR011: Conventional Chassis')
    CTR012 = 'CTR012', _('CTR012: Special Equipment')
    CTR013 = 'CTR013', _('CTR013: Stakes')
    CTR014 = 'CTR014', _('CTR014: Madrina Gondola')
    CTR015 = 'CTR015', _('CTR015: Industrial Crane')
    CTR016 = 'CTR016', _('CTR016: Crane')
    CTR017 = 'CTR017', _('CTR017: Integral')
    CTR018 = 'CTR018', _('CTR018: Cage')
    CTR019 = 'CTR019', _('CTR019: Half Rails')
    CTR020 = 'CTR020', _('CTR020: Pallet or Cells')
    CTR021 = 'CTR021', _('CTR021: Platform')
    CTR022 = 'CTR022', _('CTR022: Platform with Crane')
    CTR023 = 'CTR023', _('CTR023: Curtain-sided Platform')
    CTR024 = 'CTR024', _('CTR024: Rails')
    CTR025 = 'CTR025', _('CTR025: Refrigerator')
    CTR026 = 'CTR026', _('CTR026: Mixer')
    CTR027 = 'CTR027', _('CTR027: Half Box')
    CTR028 = 'CTR028', _('CTR028: Tank')
    CTR029 = 'CTR029', _('CTR029: Hopper')
    CTR030 = 'CTR030', _('CTR030: Tractor')
    CTR031 = 'CTR031', _('CTR031: Dump Truck')
    CTR032 = 'CTR032', _('CTR032: Detachable Dump')


class CancelIssue(models.TextChoices):
    M01 = '01', _('01 - Comprobante emitido con errores con relación')
    M02 = '02', _('02 - Comprobante emitido con errores sin relación')
    M03 = '03', _('03 - No se llevó a cabo la operación')
    M04 = '04', _('04 - Operación nominativa relacionada en la factura global')