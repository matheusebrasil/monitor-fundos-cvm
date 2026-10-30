"""Peças comuns dos testes. Nada aqui usa rede nem o banco real: tudo roda em memória."""
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # permite `import config` e `import pipeline` rodando pytest de qualquer pasta

import config  # noqa: E402
from pipeline.carregar import garantir_staging  # noqa: E402


@pytest.fixture
def con():
    c = sqlite3.connect(":memory:")
    garantir_staging(c)
    yield c
    c.close()


def inserir_informe(con, linhas):
    """linhas: (competencia, cnpj, id_subclasse, data, quota, pl, captacao, resgate, cotistas)."""
    con.executemany(
        "INSERT INTO stg_informe (competencia, cnpj_classe, id_subclasse, data, vl_quota, pl, captacao, resgate, cotistas)"
        " VALUES (?,?,?,?,?,?,?,?,?)", linhas)


def rodar_modelo(con, nome):
    con.executescript((config.SQL_MODELOS / nome).read_text(encoding="utf-8"))
