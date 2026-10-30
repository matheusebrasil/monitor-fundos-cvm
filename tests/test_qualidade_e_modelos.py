"""O modelo do fato diário e o portão de qualidade, com dados de mentira em memória."""
import config
from pipeline import qualidade
from pipeline.qualidade import bloqueia, rodar_testes

from conftest import inserir_informe, rodar_modelo

#            competencia, cnpj,            subclasse, data,         quota, pl,      capt, resg, cotistas
BASE = [
    ("202608", "00.000.000/0001-00", None, "2026-08-03", 1.0, 1000.0, 50.0, 20.0, 10),
    ("202608", "00.000.000/0001-00", None, "2026-08-04", 1.0, 1030.0, 40.0, 10.0, 10),
]


def _fato(con):
    rodar_modelo(con, "02_fato_diario.sql")
    return con.execute("SELECT cnpj_classe, data, captacao_liquida FROM fato_diario ORDER BY data").fetchall()


def test_fato_calcula_captacao_liquida(con):
    inserir_informe(con, BASE)
    assert [l[2] for l in _fato(con)] == [30.0, 30.0]


def test_fato_remove_linha_identica_repetida_pela_cvm(con):
    """Achado real: a CVM repete a mesma linha inteira. O DISTINCT tira só essa cópia exata."""
    inserir_informe(con, BASE + [BASE[0]])
    assert len(_fato(con)) == 2


def test_fato_nao_conta_subclasse_em_dobro(con):
    """Linha de subclasse repete o patrimônio da classe; ficaria contado duas vezes."""
    # Valores diferentes da classe de propósito: se fossem iguais, o DISTINCT esconderia a falta do filtro.
    subclasse = ("202608", "00.000.000/0001-00", "SUB1", "2026-08-03", 1.0, 400.0, 10.0, 5.0, 4)
    inserir_informe(con, BASE + [subclasse])
    assert len(_fato(con)) == 2
    assert [l[2] for l in _fato(con)] == [30.0, 30.0]


def test_fato_trata_captacao_nula_como_zero(con):
    inserir_informe(con, [("202608", "00.000.000/0001-00", None, "2026-08-03", 1.0, 1000.0, None, None, 10)])
    assert _fato(con)[0][2] == 0.0


def _so_este_teste(monkeypatch, tmp_path, nome):
    """Aponta o portão de qualidade para uma pasta com apenas o teste SQL pedido."""
    pasta = tmp_path / "testes"
    pasta.mkdir()
    (pasta / nome).write_text((config.SQL_TESTES / nome).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(qualidade.config, "SQL_TESTES", pasta)


def test_portao_passa_com_dados_limpos(con, monkeypatch, tmp_path):
    inserir_informe(con, BASE)
    _fato(con)
    _so_este_teste(monkeypatch, tmp_path, "unicidade_fato.sql")
    resultados = rodar_testes(con)
    assert resultados[0].passou and not bloqueia(resultados)


def test_portao_barra_dois_valores_diferentes_no_mesmo_dia(con, monkeypatch, tmp_path):
    """Conflito de verdade (mesmo dia, valores diferentes) precisa de olho humano: o pipeline para."""
    conflito = ("202608", "00.000.000/0001-00", None, "2026-08-03", 1.0, 9999.0, 50.0, 20.0, 10)
    inserir_informe(con, BASE + [conflito])
    _fato(con)
    _so_este_teste(monkeypatch, tmp_path, "unicidade_fato.sql")
    resultados = rodar_testes(con)
    assert resultados[0].violacoes == 1
    assert bloqueia(resultados)


def test_aviso_nao_bloqueia_o_relatorio(con, monkeypatch, tmp_path):
    """Patrimônio negativo é dado real (fundo em dificuldade): severidade aviso, não erro."""
    inserir_informe(con, [("202608", "00.000.000/0001-00", None, "2026-08-03", 1.0, -500.0, 0.0, 0.0, 10)])
    _fato(con)
    _so_este_teste(monkeypatch, tmp_path, "pl_negativo.sql")
    resultados = rodar_testes(con)
    assert not resultados[0].passou
    assert resultados[0].severidade == "aviso"
    assert not bloqueia(resultados)
