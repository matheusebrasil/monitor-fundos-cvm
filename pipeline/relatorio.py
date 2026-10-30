"""Monta os fatos do mês (tudo em SQL) e o relatório HTML com gráficos embutidos."""
from __future__ import annotations

import base64
import html
import io
import sqlite3
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import config  # noqa: E402

BI = 1e9


def _comp_legivel(c: str) -> str:
    return f"{c[4:]}/{c[:4]}"


def ultima_competencia_completa(con: sqlite3.Connection) -> str:
    """Último mês já encerrado (o mês corrente ainda está recebendo informes e distorce a análise)."""
    return con.execute("""
        SELECT competencia FROM fato_diario
        WHERE competencia < strftime('%Y%m', 'now', 'localtime')
        GROUP BY competencia ORDER BY competencia DESC LIMIT 1""").fetchone()[0]


def montar_fatos(con: sqlite3.Connection) -> dict:
    comp = ultima_competencia_completa(con)
    tot = con.execute("""
        SELECT SUM(captacao_liquida), SUM(pl_fim_consolidado), SUM(classes), SUM(pl_fim)
        FROM mart_captacao_classificacao WHERE competencia = ?""", (comp,)).fetchone()
    por_classificacao = con.execute("""
        SELECT classificacao, ROUND(captacao_liquida / ?, 1), ROUND(pl_fim_consolidado / ?, 1)
        FROM mart_captacao_classificacao WHERE competencia = ? ORDER BY captacao_liquida DESC""",
                                    (BI, BI, comp)).fetchall()
    gestores = con.execute("""
        SELECT gestor, ROUND(captacao_liquida / ?, 2) FROM mart_gestor_mes
        WHERE competencia = ? AND gestor <> 'Sem cadastro' ORDER BY posicao_captacao LIMIT 5""",
                           (BI, comp)).fetchall()
    return {
        "mes_atual": {"competencia": _comp_legivel(comp), "captacao_liquida_bi": round(tot[0] / BI, 1),
                      "pl_fim_bi": round(tot[1] / BI, 1), "classes": int(tot[2]),
                      "pl_bruto_com_fundos_de_fundos_bi": round(tot[3] / BI, 1)},
        "classificacao_lider": {"nome": por_classificacao[0][0], "captacao_liquida_bi": por_classificacao[0][1]},
        "por_classificacao": [{"nome": n, "captacao_liquida_bi": c, "pl_fim_bi": p} for n, c, p in por_classificacao],
        "top5_gestoras_captacao_bi": [{"gestora": g, "captacao_liquida_bi": v} for g, v in gestores],
        "_competencia_bruta": comp,
    }


def _grafico_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def grafico_serie(con: sqlite3.Connection) -> str:
    linhas = con.execute("""
        SELECT competencia, classificacao, captacao_liquida / ? FROM mart_captacao_classificacao
        WHERE classificacao IN ('Renda Fixa', 'Multimercado', 'Ações') ORDER BY competencia""", (BI,)).fetchall()
    comps = sorted({c for c, _, _ in linhas})
    fig, ax = plt.subplots(figsize=(8, 3.6))
    largura = 0.26
    for i, nome in enumerate(["Renda Fixa", "Multimercado", "Ações"]):
        valores = [next((v for c, n, v in linhas if c == comp and n == nome), 0) for comp in comps]
        ax.bar([x + (i - 1) * largura for x in range(len(comps))], valores, largura, label=nome)
    ax.set_xticks(range(len(comps)), [_comp_legivel(c) for c in comps])
    ax.axhline(0, color="#555", linewidth=0.8)
    ax.set_ylabel("R$ bilhões")
    ax.set_title("Captação líquida por classificação")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    return _grafico_base64(fig)


def escrever_html(con: sqlite3.Connection, fatos: dict, resumo: dict, testes: list, tempos: dict) -> str:
    comp = fatos["_competencia_bruta"]
    esc = html.escape
    linhas_class = "".join(
        f"<tr><td>{esc(c['nome'])}</td><td>{c['captacao_liquida_bi']:+.1f}</td><td>{c['pl_fim_bi']:.1f}</td></tr>"
        for c in fatos["por_classificacao"])
    linhas_gest = "".join(
        f"<tr><td>{esc(g['gestora'])}</td><td>{g['captacao_liquida_bi']:+.2f}</td></tr>"
        for g in fatos["top5_gestoras_captacao_bi"])
    linhas_teste = "".join(
        f"<tr><td>{esc(t.teste)}</td><td>{t.severidade}</td><td>{t.violacoes}</td>"
        f"<td>{'✔' if t.passou else '✘'}</td></tr>" for t in testes)
    frases = "".join(f"<li>{esc(f)}</li>" for f in resumo["frases"])
    origem = "gerado por IA local e conferido número a número" if resumo["origem"] == "ia" else "texto por modelo fixo"
    corpo = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Monitor de Fundos CVM — {fatos['mes_atual']['competencia']}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:32px auto;padding:0 16px;color:#1d2330}}
h1{{font-size:24px}}h2{{font-size:18px;margin-top:28px}}table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #e3e6ec;padding:6px 8px;text-align:left}}.kpi{{display:flex;gap:16px}}
.kpi div{{flex:1;background:#f3f5f9;border-radius:8px;padding:12px}}.kpi b{{display:block;font-size:22px}}
small{{color:#667}}</style></head><body>
<h1>Monitor de Fundos CVM — {fatos['mes_atual']['competencia']}</h1>
<small>Fonte: dados abertos da CVM (informe diário e cadastro). Gerado em {datetime.now():%d/%m/%Y %H:%M}.</small>
<div class="kpi"><div>Captação líquida<b>R$ {fatos['mes_atual']['captacao_liquida_bi']:+.1f} bi</b></div>
<div>Patrimônio consolidado no fim do mês<b>R$ {fatos['mes_atual']['pl_fim_bi']:.1f} bi</b>
<small>sem fundos de fundos; bruto: R$ {fatos['mes_atual']['pl_bruto_com_fundos_de_fundos_bi']:.1f} bi</small></div>
<div>Classes com informe<b>{fatos['mes_atual']['classes']:,}</b></div></div>
<h2>Resumo do mês</h2><ul>{frases}</ul><small>{origem}</small>
<h2>Série recente</h2><img alt="Captação líquida" style="max-width:100%" src="data:image/png;base64,{grafico_serie(con)}">
<h2>Por classificação (R$ bilhões)</h2><table><tr><th>Classificação</th><th>Captação líquida</th><th>PL consolidado</th></tr>{linhas_class}</table>
<h2>Top 5 gestoras em captação líquida (R$ bilhões)</h2><table><tr><th>Gestora</th><th>Captação líquida</th></tr>{linhas_gest}</table>
<h2>Qualidade dos dados</h2><table><tr><th>Teste</th><th>Severidade</th><th>Violações</th><th></th></tr>{linhas_teste}</table>
<h2>Tempo de cada modelo SQL (s)</h2><p>{esc(', '.join(f'{k}: {v}' for k, v in tempos.items()))}</p>
</body></html>"""
    config.SAIDA.mkdir(parents=True, exist_ok=True)
    destino = config.SAIDA / f"relatorio-{comp}.html"
    destino.write_text(corpo, encoding="utf-8")
    return str(destino)
