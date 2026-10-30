"""Configuração central do pipeline. Tudo que muda de ambiente fica aqui."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "dados"          # arquivos baixados e o banco (fora do git)
SAIDA = RAIZ / "saida"          # relatórios HTML gerados
LOGS = RAIZ / "logs"
SQL_MODELOS = RAIZ / "sql" / "modelos"
SQL_TESTES = RAIZ / "sql" / "testes"
BANCO = DADOS / "fundos.db"
SEGREDOS = RAIZ / "segredos.json"  # URL e chave do webhook do n8n (fora do git)

# Portal de dados abertos da CVM (fonte pública, atualizada diariamente)
URL_INFORME = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{competencia}.zip"
URL_CADASTRO = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"

MESES_PADRAO = 4                # quantas competências manter na janela de análise
TIMEOUT_HTTP = 120
TAMANHO_LOTE = 200_000          # linhas por lote na carga (controla memória)

# IA local (Ollama). Se o servidor não responder, o relatório sai com resumo por modelo fixo.
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODELO = "qwen3:8b"
