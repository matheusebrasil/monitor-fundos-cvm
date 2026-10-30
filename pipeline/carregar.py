"""Carga na camada staging (dados crus, só com nome de coluna padronizado).

Informe diário: substitui a competência inteira dentro de uma transação (idempotente —
rodar duas vezes dá o mesmo resultado). Cadastro: recarga completa.
"""
from __future__ import annotations

import io
import logging
import sqlite3
import zipfile
from pathlib import Path

import pandas as pd

import config

log = logging.getLogger(__name__)

COLUNAS_INFORME = {
    "TP_FUNDO_CLASSE": "tipo", "CNPJ_FUNDO_CLASSE": "cnpj_classe", "ID_SUBCLASSE": "id_subclasse",
    "DT_COMPTC": "data", "VL_TOTAL": "vl_total", "VL_QUOTA": "vl_quota", "VL_PATRIM_LIQ": "pl",
    "CAPTC_DIA": "captacao", "RESG_DIA": "resgate", "NR_COTST": "cotistas",
}


def garantir_staging(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS stg_informe (
            competencia TEXT NOT NULL, tipo TEXT, cnpj_classe TEXT NOT NULL, id_subclasse TEXT,
            data TEXT NOT NULL, vl_total REAL, vl_quota REAL, pl REAL,
            captacao REAL, resgate REAL, cotistas INTEGER);
        CREATE INDEX IF NOT EXISTS ix_stg_informe_comp ON stg_informe (competencia);
    """)


def carregar_informe(con: sqlite3.Connection, zip_path: Path, competencia: str) -> int:
    garantir_staging(con)
    total = 0
    with zipfile.ZipFile(zip_path) as z:
        nome_csv = z.namelist()[0]
        with con:  # transação: ou troca a competência inteira, ou nada
            con.execute("DELETE FROM stg_informe WHERE competencia = ?", (competencia,))
            for lote in pd.read_csv(z.open(nome_csv), sep=";", dtype=str, encoding="latin-1",
                                    chunksize=config.TAMANHO_LOTE):
                lote = lote.rename(columns=COLUNAS_INFORME)[list(COLUNAS_INFORME.values())]
                lote["cnpj_classe"] = lote["cnpj_classe"].str.replace(r"\D", "", regex=True)
                lote.insert(0, "competencia", competencia)
                lote.to_sql("stg_informe", con, if_exists="append", index=False)
                total += len(lote)
    log.info("informe %s: %s linhas", competencia, f"{total:,}".replace(",", "."))
    return total


def carregar_cadastro(con: sqlite3.Connection, zip_path: Path) -> int:
    """registro_classe (classe de cotas) + registro_fundo (gestor/administrador)."""
    with zipfile.ZipFile(zip_path) as z:
        def ler(nome: str) -> pd.DataFrame:
            return pd.read_csv(io.TextIOWrapper(z.open(nome), encoding="latin-1"), sep=";", dtype=str)
        classe = ler("registro_classe.csv")
        fundo = ler("registro_fundo.csv")
    classe.columns = [c.lower() for c in classe.columns]
    fundo.columns = [c.lower() for c in fundo.columns]
    with con:
        classe.to_sql("stg_classe", con, if_exists="replace", index=False)
        fundo.to_sql("stg_fundo", con, if_exists="replace", index=False)
    log.info("cadastro: %d classes, %d fundos", len(classe), len(fundo))
    return len(classe)
