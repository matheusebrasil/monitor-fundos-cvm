"""Extração incremental: só baixa o arquivo quando a CVM publicou versão nova.

A decisão usa o cabeçalho Last-Modified (HEAD, sem baixar nada) comparado com o que foi
registrado na tabela `controle_arquivos` na última carga bem-sucedida.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

import config

log = logging.getLogger(__name__)


@dataclass
class Arquivo:
    nome: str            # chave lógica, ex.: "informe_202608" ou "cadastro"
    url: str
    destino: Path


def competencias(meses: int, hoje: date | None = None) -> list[str]:
    """Últimas `meses` competências no formato AAAAMM, da mais antiga para a mais recente."""
    hoje = hoje or date.today()
    ano, mes = hoje.year, hoje.month
    saida = []
    for _ in range(meses):
        saida.append(f"{ano}{mes:02d}")
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return sorted(saida)


def arquivos_da_janela(meses: int) -> list[Arquivo]:
    lista = [Arquivo("cadastro", config.URL_CADASTRO, config.DADOS / "registro_fundo_classe.zip")]
    for comp in competencias(meses):
        lista.append(Arquivo(f"informe_{comp}", config.URL_INFORME.format(competencia=comp),
                             config.DADOS / f"inf_diario_fi_{comp}.zip"))
    return lista


def garantir_controle(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS controle_arquivos (
            nome TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            last_modified TEXT,
            bytes INTEGER,
            linhas_carregadas INTEGER,
            carregado_em TEXT
        )""")


def versao_remota(url: str) -> str | None:
    """Last-Modified do servidor; None se o arquivo ainda não existe (mês sem publicação)."""
    r = requests.head(url, timeout=config.TIMEOUT_HTTP, allow_redirects=True)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.headers.get("Last-Modified")


def precisa_atualizar(con: sqlite3.Connection, arq: Arquivo, remoto: str) -> bool:
    linha = con.execute("SELECT last_modified FROM controle_arquivos WHERE nome = ?", (arq.nome,)).fetchone()
    return linha is None or linha[0] != remoto or not arq.destino.exists()


def baixar(arq: Arquivo) -> int:
    """Baixa para .part e só renomeia no fim: um download interrompido nunca vira arquivo 'válido'."""
    arq.destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = arq.destino.with_suffix(arq.destino.suffix + ".part")
    total = 0
    with requests.get(arq.url, stream=True, timeout=config.TIMEOUT_HTTP) as r:
        r.raise_for_status()
        with open(parcial, "wb") as f:
            for bloco in r.iter_content(chunk_size=1 << 20):
                f.write(bloco)
                total += len(bloco)
    esperado = int(r.headers.get("Content-Length", total))
    if total != esperado:
        parcial.unlink(missing_ok=True)
        raise IOError(f"{arq.nome}: baixou {total} de {esperado} bytes")
    parcial.replace(arq.destino)
    return total


def planejar(con: sqlite3.Connection, meses: int) -> list[tuple[Arquivo, str]]:
    """Devolve só os arquivos novos ou alterados, com a versão remota de cada um."""
    garantir_controle(con)
    pendentes = []
    for arq in arquivos_da_janela(meses):
        remoto = versao_remota(arq.url)
        if remoto is None:
            log.info("%s ainda não publicado pela CVM", arq.nome)
            continue
        if precisa_atualizar(con, arq, remoto):
            pendentes.append((arq, remoto))
        else:
            log.info("%s sem mudança desde a última carga (%s)", arq.nome, remoto)
    return pendentes


def registrar(con: sqlite3.Connection, arq: Arquivo, remoto: str, tamanho: int, linhas: int) -> None:
    con.execute("""
        INSERT INTO controle_arquivos (nome, url, last_modified, bytes, linhas_carregadas, carregado_em)
        VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ON CONFLICT(nome) DO UPDATE SET last_modified = excluded.last_modified, bytes = excluded.bytes,
            linhas_carregadas = excluded.linhas_carregadas, carregado_em = excluded.carregado_em""",
                (arq.nome, arq.url, remoto, tamanho, linhas))
