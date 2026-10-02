import sys
import json
from typing import Dict, Any, List

import requests
from django.core.management.base import BaseCommand, CommandError

DEFAULT_URL = "https://sgadesa.azurewebsites.net/Api/AsturianoReception"
DEFAULT_TIMEOUT = 30


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--url', dest='url', help='URL destino (opcional)')
        parser.add_argument('--file', dest='file', help='Ruta de archivo JSON con el payload')
        parser.add_argument('--data', dest='data', help='JSON literal en la línea de comandos')
        parser.add_argument('--stdin', action='store_true', help='Leer JSON desde stdin')
        parser.add_argument('--header', dest='headers', action='append', help="Encabezado extra en formato 'Clave: Valor' (repetible)")
        parser.add_argument('--timeout', dest='timeout', type=int, default=DEFAULT_TIMEOUT, help='Timeout en segundos')
        parser.add_argument('--dry-run', action='store_true', help='Solo valida/muestra; no envía solicitud')
        parser.add_argument('--echo', action='store_true', help='Imprime el payload que se enviará')

    def handle(self, *args, **options):
        url = options.get('url') or DEFAULT_URL
        timeout = options.get('timeout') or DEFAULT_TIMEOUT

        payload = {"asturiano_identifier_key":'EMB-20260915-000053'}
        headers = self._parse_headers(options.get('headers'))
        headers.setdefault('Content-Type', 'application/json; charset=utf-8')
        headers.setdefault('Accept', 'application/json, */*;q=0.8')

        if options.get('echo') or options.get('dry_run'):
            self.stdout.write(self.style.NOTICE('Solicitud preparada:'))
            self.stdout.write(f"POST {url}")
            if headers:
                self.stdout.write('Headers: ' + json.dumps(headers, ensure_ascii=False))
            if payload is not None:
                self.stdout.write('Payload:')
                self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                self.stdout.write('Sin cuerpo (payload=None)')
            if options.get('dry_run'):
                self.stdout.write(self.style.SUCCESS('Dry-run OK (no se realizó la petición).'))
                return

        try:
            # Usar json=payload para enviar como application/json si hay payload; si no, sin cuerpo
            if payload is None:
                resp = requests.post(url, headers=headers, timeout=timeout)
            else:
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            raise CommandError(f'Fallo al conectar o enviar la solicitud: {e}')

        # Mostrar resultado
        self.stdout.write(self.style.NOTICE(f'HTTP {resp.status_code}'))
        content_type = resp.headers.get('Content-Type', '')
        text = resp.text
        try:
            if 'application/json' in content_type.lower():
                parsed = resp.json()
                pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
                self.stdout.write(pretty)
            else:
                # Intentar JSON aunque no traiga header correcto
                parsed = json.loads(text)
                pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
                self.stdout.write(pretty)
        except Exception:
            # Imprime texto crudo
            if text:
                self.stdout.write(text)

        # Levanta error si status es 4xx/5xx
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise CommandError(f'Error HTTP: {e}')

        self.stdout.write(self.style.SUCCESS('Solicitud POST enviada exitosamente.'))

    # ---------------------------- helpers ----------------------------
    def _read_optional_payload(self, options) -> Any:
        has_file = bool(options.get('file'))
        has_data = bool(options.get('data'))
        has_stdin = bool(options.get('stdin'))
        n = sum([has_file, has_data, has_stdin])
        if n == 0:
            return None
        if n > 1:
            raise CommandError('Indica solo una fuente de payload: --file, --data o --stdin')

        raw = None
        if has_file:
            path = options['file']
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw = f.read()
            except FileNotFoundError:
                raise CommandError(f'Archivo no encontrado: {path}')
        elif has_data:
            raw = options['data']
        else:
            raw = sys.stdin.read()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise CommandError(f'JSON inválido: {e}')
        return payload

    def _parse_headers(self, header_items: List[str] | None) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if not header_items:
            return headers
        for item in header_items:
            if not isinstance(item, str) or ':' not in item:
                raise CommandError("Cada --header debe tener formato 'Clave: Valor'")
            k, v = item.split(':', 1)
            headers[k.strip()] = v.strip()
        return headers
