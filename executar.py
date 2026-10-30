"""Orquestrador: extrair → carregar → transformar → testar → resumir → relatório → n8n.

Uso:
  python executar.py                 # janela padrão (últimos 4 meses), incremental
  python executar.py --meses 6
  python executar.py --forcar        # recarrega tudo mesmo sem mudança na CVM

Códigos de saída: 0 ok · 1 teste de qualidade com severidade "erro" falhou · 2 erro inesperado.
Feito para rodar sem ninguém olhando (agendador do Windows ou GitHub Actions): tudo vai para o log.
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime

import config
from pipeline import avisar_n8n, carregar, extrair, qualidade, relatorio, resumo_ia, transformar


def configurar_log() -> None:
    config.LOGS.mkdir(parents=True, exist_ok=True)
    arquivo = config.LOGS / f"execucao-{datetime.now():%Y%m%d}.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                        handlers=[logging.FileHandler(arquivo, encoding="utf-8"), logging.StreamHandler()])


def executar(meses: int, forcar: bool) -> int:
    log = logging.getLogger("executar")
    inicio = time.perf_counter()
    config.DADOS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.BANCO)
    try:
        if forcar:
            con.execute("DROP TABLE IF EXISTS controle_arquivos")
        pendentes = extrair.planejar(con, meses)
        log.info("%d arquivo(s) novo(s) ou alterado(s) na CVM", len(pendentes))
        for arq, versao in pendentes:
            tamanho = extrair.baixar(arq)
            if arq.nome == "cadastro":
                linhas = carregar.carregar_cadastro(con, arq.destino)
            else:
                linhas = carregar.carregar_informe(con, arq.destino, arq.nome.split("_")[1])
            with con:
                extrair.registrar(con, arq, versao, tamanho, linhas)

        # competências fora da janela saem do staging (janela deslizante)
        janela = extrair.competencias(meses)
        carregar.garantir_staging(con)
        with con:
            con.execute(f"DELETE FROM stg_informe WHERE competencia NOT IN ({','.join('?' * len(janela))})", janela)

        tempos = transformar.rodar_modelos(con)
        testes = qualidade.rodar_testes(con)
        if qualidade.bloqueia(testes):
            log.error("teste de qualidade com severidade 'erro' falhou: relatório NÃO gerado")
            avisar_n8n.enviar("bloqueado", None, None, testes, time.perf_counter() - inicio, len(pendentes))
            return 1

        fatos = relatorio.montar_fatos(con)
        publicos = {k: v for k, v in fatos.items() if not k.startswith("_")}
        resumo = resumo_ia.gerar(publicos)
        destino = relatorio.escrever_html(con, fatos, resumo, testes, tempos)
        (config.SAIDA / f"fatos-{fatos['_competencia_bruta']}.json").write_text(
            json.dumps({"fatos": publicos, "resumo": resumo}, ensure_ascii=False, indent=1), encoding="utf-8")
        segundos = time.perf_counter() - inicio
        log.info("relatório: %s (resumo: %s) — pipeline em %.1fs", destino, resumo["origem"], segundos)
        avisar_n8n.enviar("ok", publicos, resumo, testes, segundos, len(pendentes))
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meses", type=int, default=config.MESES_PADRAO)
    ap.add_argument("--forcar", action="store_true")
    args = ap.parse_args()
    configurar_log()
    try:
        sys.exit(executar(args.meses, args.forcar))
    except Exception:
        logging.getLogger("executar").exception("falha inesperada")
        sys.exit(2)
