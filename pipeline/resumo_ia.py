"""Resumo executivo escrito por um LLM local — com verificação de fatos.

O modelo recebe só os números já calculados em SQL e devolve JSON. Antes de entrar no
relatório, cada frase passa pelo verificador: todo número citado precisa existir nos fatos
(com tolerância de arredondamento). Frase com número inventado é descartada. Se sobrarem
menos de 3 frases (ou o Ollama estiver desligado), o relatório usa um resumo por modelo fixo.
"""
from __future__ import annotations

import json
import logging
import re

import requests

import config

log = logging.getLogger(__name__)

# Primeiro o formato brasileiro com ponto de milhar ("9.050,6", "24.967"); depois o decimal simples.
NUMERO = re.compile(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+(?:[.,]\d+)?")


def numeros_do_texto(texto: str) -> list[float]:
    """Lê números escritos em pt-BR ou com ponto decimal.

    >>> numeros_do_texto("PL de 9.050,6 bilhões em 24.967 classes")
    [9050.6, 24967.0]
    >>> numeros_do_texto("captação de R$ 37.5 bi e -9,1 no multimercado")
    [37.5, -9.1]
    """
    saida = []
    for bruto in NUMERO.findall(texto):
        if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?", bruto):
            bruto = bruto.replace(".", "")
        saida.append(float(bruto.replace(",", ".")))
    return saida


def numeros_permitidos(fatos: dict) -> set[float]:
    """Todos os números que aparecem nos fatos, em qualquer nível do dicionário."""
    achados: set[float] = set()

    def visitar(v):
        if isinstance(v, dict):
            for x in v.values():
                visitar(x)
        elif isinstance(v, list):
            for x in v:
                visitar(x)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            achados.add(round(float(v), 1))
        elif isinstance(v, str):
            for n in numeros_do_texto(v):
                achados.add(round(n, 1))
    visitar(fatos)
    return achados


def frase_confere(frase: str, permitidos: set[float]) -> bool:
    for n in numeros_do_texto(frase):
        if not any(abs(n - p) <= 0.051 or abs(abs(n) - abs(p)) <= 0.051 for p in permitidos):
            return False
    return True


def br(n: float, casas: int = 1) -> str:
    """Número no formato brasileiro.

    >>> br(9050.8), br(37.5), br(24967, 0)
    ('9.050,8', '37,5', '24.967')
    """
    texto = f"{n:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def resumo_fixo(fatos: dict) -> list[str]:
    m = fatos["mes_atual"]
    lider = fatos["classificacao_lider"]
    return [
        f"Captação líquida do mercado em {m['competencia']}: R$ {br(m['captacao_liquida_bi'])} bilhões.",
        f"Patrimônio total no fim do mês: R$ {br(m['pl_fim_bi'])} bilhões em {br(m['classes'], 0)} classes.",
        f"Maior captação por classificação: {lider['nome']} (R$ {br(lider['captacao_liquida_bi'])} bilhões).",
    ]


def pedir_ao_modelo(fatos: dict) -> list[str]:
    prompt = (
        "Você é analista de fundos. Escreva de 3 a 5 frases curtas em português sobre o mês, "
        "usando SOMENTE os números abaixo, exatamente como estão (em bilhões de reais). "
        "Não calcule números novos. Responda em JSON: {\"frases\": [\"...\"]}.\n\n"
        f"FATOS:\n{json.dumps(fatos, ensure_ascii=False, indent=1)}"
    )
    r = requests.post(config.OLLAMA_URL, timeout=300, json={
        "model": config.OLLAMA_MODELO, "prompt": prompt, "format": "json", "stream": False,
        "think": False, "options": {"temperature": 0.1},
    })
    r.raise_for_status()
    return json.loads(r.json()["response"]).get("frases", [])


def gerar(fatos: dict) -> dict:
    """Devolve {'frases': [...], 'origem': 'ia'|'modelo fixo', 'descartadas': [...]}."""
    try:
        frases = pedir_ao_modelo(fatos)
    except Exception as erro:  # Ollama desligado, timeout, JSON inválido
        log.warning("IA indisponível (%s); usando resumo fixo", erro)
        return {"frases": resumo_fixo(fatos), "origem": "modelo fixo", "descartadas": []}
    permitidos = numeros_permitidos(fatos)
    aprovadas = [f for f in frases if isinstance(f, str) and frase_confere(f, permitidos)]
    descartadas = [f for f in frases if f not in aprovadas]
    for f in descartadas:
        log.warning("frase descartada pelo verificador: %s", f)
    if len(aprovadas) < 3:
        return {"frases": resumo_fixo(fatos), "origem": "modelo fixo", "descartadas": descartadas}
    return {"frases": aprovadas, "origem": "ia", "descartadas": descartadas}
