"""Entrega: manda o resultado da execução para o n8n, que envia o e-mail e guarda o histórico.

O n8n Cloud não enxerga o PC, então é o pipeline que empurra (POST no webhook).
URL e chave ficam em segredos.json (fora do git). Sem esse arquivo, a entrega é pulada.
Falha de rede nunca derruba o pipeline: o relatório HTML local já foi gerado.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict

import requests

import config

log = logging.getLogger(__name__)


def montar_corpo(status: str, fatos: dict | None, resumo: dict | None, testes: list,
                 segundos: float, arquivos_novos: int, chave: str) -> dict:
    """Corpo do POST. Só vai o que o e-mail usa: fatos públicos, resumo e testes.

    >>> from pipeline.qualidade import Resultado
    >>> c = montar_corpo("bloqueado", None, None, [Resultado("pl_negativo", "aviso", 3, None, False)], 81.94, 0, "k")
    >>> c["status"], c["segundos"], c["testes"][0]["teste"], c["fatos"]
    ('bloqueado', 81.9, 'pl_negativo', {})
    """
    return {
        "chave": chave,
        "status": status,
        "fatos": fatos or {},
        "resumo": {"frases": (resumo or {}).get("frases", []), "origem": (resumo or {}).get("origem", "")},
        "testes": [{k: v for k, v in asdict(t).items() if k != "proporcao"} for t in testes],
        "segundos": round(segundos, 1),
        "arquivos_novos": arquivos_novos,
    }


def enviar(status: str, fatos: dict | None, resumo: dict | None, testes: list,
           segundos: float, arquivos_novos: int) -> bool:
    if not config.SEGREDOS.exists():
        log.info("segredos.json não existe: entrega pelo n8n pulada")
        return False
    segredos = json.loads(config.SEGREDOS.read_text(encoding="utf-8"))
    corpo = montar_corpo(status, fatos, resumo, testes, segundos, arquivos_novos, segredos["n8n_chave"])
    try:
        r = requests.post(segredos["n8n_webhook_url"], json=corpo, timeout=config.TIMEOUT_HTTP)
        r.raise_for_status()
        log.info("n8n recebeu (%s): %s", status, r.text[:200])
        return True
    except requests.RequestException as erro:
        log.warning("não consegui avisar o n8n (%s); o relatório local continua em saida/", erro)
        return False
