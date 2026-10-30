# Monitor de Fundos CVM

Pipeline de dados em **Python + SQL** que baixa os informes diários de fundos de investimento do
portal de dados abertos da CVM, trata, testa a qualidade e entrega um relatório mensal por e-mail
através do **n8n**.

```
CVM (dados abertos)                     PC (Python)                                n8n Cloud
inf_diario_fi_AAAAMM.zip  ──extrair──▶  staging SQLite ──5 modelos SQL──▶ marts
registro_fundo_classe.zip               └─ 7 testes de qualidade (portão)
                                        └─ resumo (IA local verificada ou modelo fixo)
                                        └─ relatório HTML ──POST webhook──▶  e-mail + histórico
```

## O que ele faz

| Etapa | Onde | Detalhe |
|---|---|---|
| Extrair | `pipeline/extrair.py` | Carga **incremental**: só baixa arquivo que mudou na CVM (compara `Last-Modified`). Janela deslizante de 4 meses. |
| Carregar | `pipeline/carregar.py` | ~2 milhões de linhas em lotes de 200 mil para o SQLite. |
| Transformar | `sql/modelos/` | Dimensão de classes, fato diário (sem duplicatas da origem), marts por classe, classificação e gestora. |
| Testar | `sql/testes/` | Cada teste é uma consulta que devolve as linhas que **violam** a regra. Severidade `erro` barra o relatório; `aviso` só aparece nele. |
| Resumir | `pipeline/resumo_ia.py` | LLM local (Ollama) escreve o resumo; cada número citado precisa existir nos fatos, senão a frase é descartada. |
| Entregar | `pipeline/avisar_n8n.py` + `n8n/` | POST no webhook do n8n, que confere a chave, manda o e-mail (relatório ou alerta de "barrado") e guarda o histórico da execução numa tabela. |

## O que os testes já pegaram nos dados reais

- **Linhas repetidas no próprio arquivo da CVM** (mesma classe, mesmo dia): o teste de unicidade barrou
  o primeiro relatório; o fato passou a deduplicar e o aviso mostra quantas vieram sujas.
- **Classes sem cadastro** no arquivo de registro: resolvido no modelo da dimensão (0% hoje).
- **Patrimônio contado em dobro** por fundos que investem em outros fundos: o PL consolidado de 08/2026
  é R$ 9,05 tri, contra R$ 13,97 tri somando tudo.
- **Patrimônio negativo** em algumas classes (fundo em dificuldade ou liquidação): dado real, fica como aviso.

## Rodar

```
python executar.py              # incremental, últimos 4 meses
python executar.py --meses 6
python executar.py --forcar     # recarrega tudo
```

Ou dê dois cliques em `_rodar.cmd`. Códigos de saída: 0 ok, 1 barrado pela qualidade, 2 erro inesperado.

Para a entrega pelo n8n, copie `segredos.exemplo.json` para `segredos.json` e preencha a URL do
webhook e a chave. Sem esse arquivo o pipeline roda igual e só pula a entrega. O fluxo do n8n é
gerado por `node n8n/build.mjs` a partir de `n8n/montar_email.js`.

## Tecnologias

Python 3.13 (requests, sqlite3), SQL (SQLite), n8n (Webhook, Code, Gmail, Data Table), Ollama (Qwen 3 8B, opcional).
