"""Testes de qualidade escritos em SQL: cada consulta devolve as linhas que VIOLAM a regra.

Cabeçalho de cada arquivo:
  -- severidade: erro | aviso      (erro interrompe o pipeline antes do relatório)
  -- limite: 0.02                  (opcional: tolera até 2% de violações...)
  -- base: SELECT COUNT(...)       (...em relação a este denominador)
"""
from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass

import config

log = logging.getLogger(__name__)


@dataclass
class Resultado:
    teste: str
    severidade: str
    violacoes: int
    proporcao: float | None
    passou: bool


def _cabecalho(sql: str, chave: str) -> str | None:
    m = re.search(rf"^--\s*{chave}:\s*(.+)$", sql, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else None


def rodar_testes(con: sqlite3.Connection) -> list[Resultado]:
    resultados = []
    for arquivo in sorted(config.SQL_TESTES.glob("*.sql")):
        sql = arquivo.read_text(encoding="utf-8")
        severidade = (_cabecalho(sql, "severidade") or "erro").lower()
        limite = _cabecalho(sql, "limite")
        base_sql = _cabecalho(sql, "base")
        n = con.execute(f"SELECT COUNT(*) FROM ({sql.rstrip().rstrip(';')})").fetchone()[0]
        proporcao = None
        if limite and base_sql:
            base = con.execute(base_sql).fetchone()[0] or 1
            proporcao = n / base
            passou = proporcao <= float(limite)
        else:
            passou = n == 0
        r = Resultado(arquivo.stem, severidade, n, proporcao, passou)
        nivel = logging.INFO if passou else (logging.ERROR if severidade == "erro" else logging.WARNING)
        log.log(nivel, "teste %-28s %s (%d violações%s)", r.teste, "ok" if passou else "FALHOU", n,
                f", {proporcao:.2%}" if proporcao is not None else "")
        resultados.append(r)
    return resultados


def bloqueia(resultados: list[Resultado]) -> bool:
    return any(not r.passou and r.severidade == "erro" for r in resultados)
