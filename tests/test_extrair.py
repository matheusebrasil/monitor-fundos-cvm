"""Janela de meses e carga incremental: só baixa o que é novo ou mudou."""
from datetime import date

from pipeline import extrair
from pipeline.extrair import Arquivo, competencias, garantir_controle, precisa_atualizar, registrar


def test_competencias_em_ordem_crescente():
    assert competencias(3, hoje=date(2026, 9, 15)) == ["202607", "202608", "202609"]


def test_competencias_atravessam_a_virada_do_ano():
    assert competencias(3, hoje=date(2026, 1, 10)) == ["202511", "202512", "202601"]


def test_arquivo_novo_precisa_baixar(con, tmp_path):
    garantir_controle(con)
    arq = Arquivo("informe_202608", "http://x", tmp_path / "a.zip")
    assert precisa_atualizar(con, arq, "Mon, 01 Sep 2026")


def test_arquivo_ja_carregado_e_igual_nao_baixa_de_novo(con, tmp_path):
    garantir_controle(con)
    destino = tmp_path / "a.zip"
    destino.write_bytes(b"zip")
    arq = Arquivo("informe_202608", "http://x", destino)
    registrar(con, arq, "Mon, 01 Sep 2026", 3, 100)
    assert not precisa_atualizar(con, arq, "Mon, 01 Sep 2026")


def test_arquivo_alterado_na_cvm_baixa_de_novo(con, tmp_path):
    garantir_controle(con)
    destino = tmp_path / "a.zip"
    destino.write_bytes(b"zip")
    arq = Arquivo("informe_202608", "http://x", destino)
    registrar(con, arq, "Mon, 01 Sep 2026", 3, 100)
    assert precisa_atualizar(con, arq, "Tue, 02 Sep 2026")


def test_arquivo_apagado_do_disco_baixa_de_novo(con, tmp_path):
    garantir_controle(con)
    arq = Arquivo("informe_202608", "http://x", tmp_path / "sumiu.zip")  # nunca criado
    registrar(con, arq, "Mon, 01 Sep 2026", 3, 100)
    assert precisa_atualizar(con, arq, "Mon, 01 Sep 2026")


def test_planejar_ignora_mes_ainda_nao_publicado(con, monkeypatch):
    monkeypatch.setattr(extrair, "arquivos_da_janela", lambda meses: [Arquivo("informe_209912", "http://x", extrair.config.DADOS / "x.zip")])
    monkeypatch.setattr(extrair, "versao_remota", lambda url: None)  # a CVM devolveu 404
    assert extrair.planejar(con, 1) == []
