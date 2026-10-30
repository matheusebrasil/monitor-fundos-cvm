"""Roda os modelos SQL em ordem (01_, 02_, ...). Cada arquivo recria sua tabela do zero."""
from __future__ import annotations

import logging
import sqlite3
import time

import config

log = logging.getLogger(__name__)


def rodar_modelos(con: sqlite3.Connection) -> dict[str, float]:
    tempos = {}
    for arquivo in sorted(config.SQL_MODELOS.glob("*.sql")):
        inicio = time.perf_counter()
        with con:
            con.executescript(arquivo.read_text(encoding="utf-8"))
        tempos[arquivo.stem] = round(time.perf_counter() - inicio, 2)
        log.info("modelo %s em %.2fs", arquivo.stem, tempos[arquivo.stem])
    return tempos
