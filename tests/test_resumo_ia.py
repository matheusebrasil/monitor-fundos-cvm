"""O verificador de fatos: frase com número que não está nos dados tem de ser descartada."""
import pytest

from pipeline import resumo_ia
from pipeline.resumo_ia import br, frase_confere, numeros_do_texto, numeros_permitidos

FATOS = {
    "mes_atual": {"competencia": "08/2026", "captacao_liquida_bi": 37.5, "pl_fim_bi": 9050.6, "classes": 24967},
    "classificacao_lider": {"nome": "Renda Fixa", "captacao_liquida_bi": -9.1},
}


@pytest.mark.parametrize("texto, esperado", [
    ("PL de 9.050,6 bilhões", [9050.6]),          # o caso que o verificador antigo recusava
    ("24.967 classes", [24967.0]),                 # ponto de milhar sem decimal
    ("captação de R$ 37.5 bi", [37.5]),            # ponto decimal
    ("-9,1 no multimercado", [-9.1]),              # negativo com vírgula
    ("sem número nenhum", []),
])
def test_numeros_do_texto(texto, esperado):
    assert numeros_do_texto(texto) == esperado


def test_br_formata_no_padrao_brasileiro():
    assert br(9050.8) == "9.050,8"
    assert br(24967, 0) == "24.967"


def test_numeros_permitidos_visita_todos_os_niveis():
    permitidos = numeros_permitidos(FATOS)
    assert {37.5, 9050.6, 24967.0, -9.1} <= permitidos


def test_frase_com_numeros_dos_fatos_passa():
    permitidos = numeros_permitidos(FATOS)
    assert frase_confere("O patrimônio fechou em R$ 9.050,6 bilhões em 24.967 classes.", permitidos)


def test_frase_com_numero_inventado_e_recusada():
    permitidos = numeros_permitidos(FATOS)
    assert not frase_confere("O patrimônio fechou em R$ 9.999,9 bilhões.", permitidos)


def test_tolerancia_de_arredondamento():
    permitidos = numeros_permitidos(FATOS)
    assert frase_confere("Captação de 37,5 bilhões.", permitidos)
    assert not frase_confere("Captação de 38,5 bilhões.", permitidos)


def test_gerar_descarta_frase_inventada_e_mantem_o_resto(monkeypatch):
    monkeypatch.setattr(resumo_ia, "pedir_ao_modelo", lambda fatos: [
        "Captação líquida de 37,5 bilhões.",
        "PL de 9.050,6 bilhões.",
        "Foram 24.967 classes.",
        "A captação foi de 123,4 bilhões.",  # inventada
    ])
    r = resumo_ia.gerar(FATOS)
    assert r["origem"] == "ia"
    assert len(r["frases"]) == 3
    assert r["descartadas"] == ["A captação foi de 123,4 bilhões."]


def test_gerar_volta_ao_resumo_fixo_quando_sobram_poucas_frases(monkeypatch):
    monkeypatch.setattr(resumo_ia, "pedir_ao_modelo", lambda fatos: ["Captação de 999 bilhões."])
    r = resumo_ia.gerar(FATOS)
    assert r["origem"] == "modelo fixo"
    assert len(r["frases"]) == 3


def test_gerar_volta_ao_resumo_fixo_quando_a_ia_esta_desligada(monkeypatch):
    def cair(fatos):
        raise ConnectionError("Ollama desligado")
    monkeypatch.setattr(resumo_ia, "pedir_ao_modelo", cair)
    r = resumo_ia.gerar(FATOS)
    assert r["origem"] == "modelo fixo"
    # O resumo fixo é montado só com números dos fatos, então ele mesmo passa no verificador.
    permitidos = numeros_permitidos(FATOS)
    assert all(frase_confere(f, permitidos) for f in r["frases"])
