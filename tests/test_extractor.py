import pytest

from app.agents.extractor import ExtractionError, _solo_json


def test_recorta_el_json_de_una_respuesta_con_adornos():
    raw = 'Claro, aqui tienes:\n```json\n{"items": []}\n```'
    assert _solo_json(raw) == '{"items": []}'


def test_respeta_un_json_limpio():
    assert _solo_json('{"a": 1}') == '{"a": 1}'


def test_conserva_las_llaves_anidadas():
    raw = 'texto {"a": {"b": 1}} mas texto'
    assert _solo_json(raw) == '{"a": {"b": 1}}'


@pytest.mark.parametrize("raw", ["sin llaves", "} al reves {", ""])
def test_falla_cuando_no_hay_json(raw):
    with pytest.raises(ExtractionError):
        _solo_json(raw)
