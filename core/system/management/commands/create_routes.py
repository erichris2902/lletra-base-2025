from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from core.operations_panel.models import DeliveryLocation, Route

ROUTES_BY_REGION = {
  "REGION 1": {
    "ZONA B": ["T077","T048","T349","T030","T057","T071","T166","T265","T291","T304","T445","T537","T559","T574","T123","T144","T402","T520","T590","T108"],
    "ZONA C": ["T005","T116","T218","T248","T252","T426","T087","T279","T025","T143","T514","T086","T113","T165","T219","T115","T198","T196","T366","T399"],
    "ZONA D": ["T114","T134","T161","T184","T243","T251","T405","T417","T455","T111","T202","T205","T233","T356","T381","T388","T460","T282","T424","T014","T094"],
    "ZONA E": ["T034","T046","T103","T209","T236","T345","T404","T361","T130","T241","T074","T107","T122","T353","T357","T406","T222","T288","T609","T089","T229"],
    "ZONA F": ["T009","T012","T088","T091","T119","T234","T237","T553","T076","T027","T084","T129","T246","T008","T083","T155","T172","T338","T626","T092"],
    "ZONA K": ["T011","T017","T309","T489","T545","T555","T029","T101","T102","T105","T136","T255","T259","T476","T286","T372","T269","T244","T257","T055"],
    "ZONA J": ["T020","T039","T230","T554","T050","T062","T106","T146","T185","T190","T439","T145","T206","T261","T472","T284","T485","T201","T400","T401"]
  },
  "REGION 2": {
    "ZONA I": ["T002","T010","T013","T131","T069","T141","T110","T001","T118","T132","T007","T348","T006","T475","T016","T444","T147","T350","T215","T308"],
    "ZONA G": ["T487","T427","T126","T095","T096","T104","T121","T124","T127","T149","T150","T154","T492","T595","T125","T047","T019","T333","T506","T093"],
    "ZONA H": ["T142","T021","T075","T090","T226","T302","T065","T238","T398","T208","T374","T249","T596","T608","T488","T253","T535","T112","T567","T120"],
    "ZONA L": ["T344","T033","T182","T225","T266","T221","T459","T571","T556","T354","T164","T176","T550","T436","T036","T041","T042","T049","T287","T160"],
    "ZONA M": ["T028","T227","T510","T024","T026","T032","T085","T109","T235","T242","T563","T004","T521","T040","T023","T167","T181"],
    "ZONA N": ["T058","T064","T066","T073","T158","T347","T503","T451","T600","T627"],
    "ZONA 2": ["T283","T336","T377","T389","T447","T491","T509","T546","T592","T421","T448","T543","T557","T579","T622"],
    "ZONA A": ["T054","T204","T278","T352","T240","T003","T037","T052","T063","T194","T371","T486","T502","T059","T319","T575","T540","T573","T566","T156"]
  },
  "REGION 3": {
    "ZONA O": ["T137","T139","T153","T193","T203","T207","T262","T337","T346","T403","T461","T467","T468","T478","T483","T484","T511","T544","T591","T522","T504","T629"],
    "ZONA P": ["T018","T070","T082","T168","T526","T044","T174","T179","T220","T231","T247","T267","T523","T135","T195","T199","T263","T275","T342","T416","T603"],
    "ZONA Q": ["T060","T035","T053","T056","T097","T098","T157","T162","T197","T216","T224","T276","T306","T343","T393","T411","T505","T564","T187","T473"],
    "ZONA R": ["T079","T081","T270","T301","T369","T412","T474","T494","T499","T500","T379","T443","T612"],
    "ZONA S": ["T586","T232","T422","T180","T186","T324","T363","T428","T452","T454","T480","T507","T519","T530","T551","T569","T572","T419","T552","T594","T610"],
    "ZONA T": ["T431","T430","T432","T300","T395","T214","T322","T516","T517","T477","T534"],
    "ZONA U": ["T031","T043","T051","T067","T078","T099","T100","T152","T159","T163","T239","T256","T260","T307","T359","T541","T171","T450","T606"]
  }
}


class Command(BaseCommand):
    help = "Crea o actualiza rutas por Region-Zona y muestra resultados en consola"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula el proceso sin guardar cambios.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        not_found_by_zone = defaultdict(list)
        duplicates_by_zone = defaultdict(dict)
        skipped_zones = []
        created_count = 0
        updated_count = 0

        self.stdout.write(self.style.NOTICE("Iniciando proceso..."))

        with transaction.atomic():
            for region_name, zones in ROUTES_BY_REGION.items():
                for zone_name, store_codes in zones.items():
                    route_name = f"{region_name} - {zone_name}"

                    found_locations = []

                    for store_code in store_codes:
                        matches = DeliveryLocation.objects.filter(
                            rfc="AEM151124N36"
                        ).filter(
                            name__icontains=store_code
                        ).order_by("id")

                        count = matches.count()

                        if count == 0:
                            not_found_by_zone[f"{region_name} | {zone_name}"].append(store_code)
                            continue

                        if count > 1:
                            duplicates_by_zone[f"{region_name} | {zone_name}"][store_code] = list(
                                matches.values_list("id", "name")
                            )

                        found_locations.append(matches.first())

                    # quitar duplicados
                    unique_locations = []
                    seen = set()
                    for loc in found_locations:
                        if loc.id not in seen:
                            unique_locations.append(loc)
                            seen.add(loc.id)

                    if len(unique_locations) < 2:
                        skipped_zones.append((region_name, zone_name, len(unique_locations)))
                        self.stdout.write(
                            self.style.WARNING(
                                f"[SKIP] {route_name} → solo {len(unique_locations)} ubicaciones"
                            )
                        )
                        continue

                    cedis = DeliveryLocation.objects.get(
                        name="CEDIS ASTURIANO QRO"
                    )

                    initial = cedis
                    destination = cedis
                    stops = unique_locations

                    route, created = Route.objects.update_or_create(
                        name=route_name,
                        defaults={
                            "initial_location": initial,
                            "destination_location": destination,
                            "notes": f"Ruta autogenerada {region_name}-{zone_name}",
                        },
                    )

                    route.route_stops.set(stops)

                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f"[CREATED] {route_name}"))
                    else:
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"[UPDATED] {route_name}"))

            if dry_run:
                self.stdout.write(self.style.WARNING("Dry run → rollback"))
                transaction.set_rollback(True)

        # =============================
        # LOG EN CONSOLA
        # =============================
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.NOTICE("RESUMEN"))
        self.stdout.write(f"Rutas creadas: {created_count}")
        self.stdout.write(f"Rutas actualizadas: {updated_count}")

        # tiendas no encontradas
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("TIENDAS NO ENCONTRADAS"))
        if not not_found_by_zone:
            self.stdout.write("Todas fueron encontradas ✔")
        else:
            for zone, stores in sorted(not_found_by_zone.items()):
                self.stdout.write(f"\n{zone}:")
                for s in stores:
                    self.stdout.write(f"  - {s}")

        # duplicados
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("COINCIDENCIAS DUPLICADAS"))
        if not duplicates_by_zone:
            self.stdout.write("Sin duplicados ✔")
        else:
            for zone, data in duplicates_by_zone.items():
                self.stdout.write(f"\n{zone}:")
                for code, matches in data.items():
                    self.stdout.write(f"  - {code}:")
                    for mid, name in matches:
                        self.stdout.write(f"      * ID={mid} | {name}")

        # zonas omitidas
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("ZONAS OMITIDAS"))
        if not skipped_zones:
            self.stdout.write("Ninguna ✔")
        else:
            for region, zone, count in skipped_zones:
                self.stdout.write(
                    f"- {region} - {zone} (solo {count} ubicaciones válidas)"
                )

        self.stdout.write("\nProceso terminado ✔")