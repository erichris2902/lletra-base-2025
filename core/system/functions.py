from typing import Type, Optional

import requests
import unicodedata
from django.db.models import Model
from django.shortcuts import redirect
from django.urls import reverse_lazy
from fuzzywuzzy import process, fuzz

from core.system.enums import SystemEnum

def get_file_path(bot_token, file_id):
    url = f"https://api.telegram.org/bot{bot_token}/getFile"
    response = requests.get(url, params={"file_id": file_id})
    response.raise_for_status()
    return response.json()["result"]["file_path"]

def normalize_string(value):
    if not isinstance(value, str):
        print("Invalid value:", value)
        return ''

    return ''.join(
        c for c in unicodedata.normalize('NFKD', value)
        if not unicodedata.combining(c)
    ).upper()

def paragraph_replace_text(paragraph, regex, replace_str):
    """Return `paragraph` after replacing all matches for `regex` with `replace_str`.

    `regex` is a compiled regular expression prepared with `re.compile(pattern)`
    according to the Python library documentation for the `re` module.
    """
    # --- a paragraph may contain more than one match, loop until all are replaced ---
    while True:
        text = paragraph.text
        match = regex.search(text)
        if not match:
            break

        # --- when there's a match, we need to modify run.text for each run that
        # --- contains any part of the match-string.
        runs = iter(paragraph.runs)
        start, end = match.start(), match.end()

        # --- Skip over any leading runs that do not contain the match ---
        for run in runs:
            run_len = len(run.text)
            if start < run_len:
                break
            start, end = start - run_len, end - run_len

        # --- Match starts somewhere in the current run. Replace match-str prefix
        # --- occurring in this run with entire replacement str.
        run_text = run.text
        run_len = len(run_text)
        run.text = "%s%s%s" % (run_text[:start], replace_str, run_text[end:])
        end -= run_len  # --- note this is run-len before replacement ---

        # --- Remove any suffix of match word that occurs in following runs. Note that
        # --- such a suffix will always begin at the first character of the run. Also
        # --- note a suffix can span one or more entire following runs.
        for run in runs:  # --- next and remaining runs, uses same iterator ---
            if end <= 0:
                break
            run_text = run.text
            run_len = len(run_text)
            run.text = run_text[end:]
            end -= run_len

    # --- optionally get rid of any "spanned" runs that are now empty. This
    # --- could potentially delete things like inline pictures, so use your judgement.
    # for run in paragraph.runs:
    #     if run.text == "":
    #         r = run._r
    #         r.getparent().remove(r)

    return paragraph


def dispatch_user(system):
    if system == SystemEnum.SYSTEM:
        return True, reverse_lazy('system_panel:dashboard')
    elif system == SystemEnum.OPERACIONES:
        return True, reverse_lazy('system_panel:dashboard')
    elif system == SystemEnum.SALE:
        return True, reverse_lazy('system_panel:dashboard')
    elif system == SystemEnum.ADMINISTRACION:
        return True, reverse_lazy('system_panel:dashboard')
    elif system == SystemEnum.RH:
        return True, reverse_lazy('system_panel:dashboard')
    elif system == SystemEnum.COMERCIAL:
        return True, reverse_lazy('system_panel:dashboard')
    elif system == SystemEnum.ATTENDANCE:
        return True, reverse_lazy('system_panel:capture_attendance')
    elif system == SystemEnum.SUPPLIER:
        return True, reverse_lazy('supplier_panel:dashboard')
    elif system == SystemEnum.NONE:
        return True, reverse_lazy('admin_panel:logout')
    return False, ""


def extract_best_coincidence_from_field_in_model(
        model: Type[Model],
        field: str,
        search_text: str,
        threshold: Optional[int] = 60
) -> Optional[Model]:
    """
    Realiza una búsqueda difusa del valor más cercano en el campo especificado de un modelo Django.

    Args:
        model (Type[Model]): Modelo de Django (e.g., DeliveryLocation).
        field (str): Nombre del campo a comparar (debe ser texto).
        search_text (str): Texto que se quiere buscar aproximadamente.
        threshold (Optional[int]): Umbral mínimo de similitud (0 a 100). Si se especifica, solo devuelve resultados por encima del umbral.

    Returns:
        Optional[Model]: La instancia del modelo más parecida, o None si no hay coincidencias válidas.
    """
    instances = list(model.objects.all())
    if not instances:
        return None

    # Obtener los valores del campo dinámicamente
    field_values = [getattr(obj, field, '') for obj in instances]

    # Buscar la mejor coincidencia
    result = process.extractOne(
        search_text,
        field_values,
        scorer=fuzz.token_sort_ratio
    )

    if result:
        best_match, score = result[:2]
        print(f"🧠 Mejor coincidencia: '{best_match}' con score {score} de {search_text}")

        # Si se requiere score mínimo
        if threshold is not None and score < threshold:
            return None

        # Buscar el objeto original que coincida
        for obj in instances:
            if getattr(obj, field, '') == best_match:
                return obj

    return None
