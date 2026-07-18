import os
import time
import requests
import gspread
import pypdf
import json
from google.oauth2.service_account import Credentials
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

GOOGLE_SECRETS = os.environ.get("GOOGLE_CREDENTIALS_JSON")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GOOGLE_SECRETS or not GROQ_API_KEY:
    raise ValueError("Erro: As chaves secretas (Secrets) nao foram configuradas no GitHub.")

creds_dict = json.loads(GOOGLE_SECRETS)
escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_dict, scopes=escopos)
gc = gspread.authorize(creds)

NOME_DA_PLANILHA = "Análise de Processos CADE"
planilha = gc.open(NOME_DA_PLANILHA).sheet1

url_groq = "https://api.groq.com/openai/v1/chat/completions"
headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

PASTA_DOCUMENTOS = "./documentos"

# Ensure the documents directory exists; create it if missing
if not os.path.isdir(PASTA_DOCUMENTOS):
    logging.info(f"Directory {PASTA_DOCUMENTOS} does not exist — creating it.")
    try:
        os.makedirs(PASTA_DOCUMENTOS, exist_ok=True)
    except Exception:
        logging.exception("Failed to create documents directory")
        sys.exit(1)

arquivos = [f for f in os.listdir(PASTA_DOCUMENTOS) if f.endswith(('.pdf', '.rar'))]

# If there are no files to process, exit successfully
if not arquivos:
    logging.info("No documents found in ./documentos — nothing to process. Exiting.")
    sys.exit(0)

for arquivo in arquivos:
    caminho_completo = os.path.join(PASTA_DOCUMENTOS, arquivo)
    if arquivo.endswith('.rar'):
        planilha.append_row(["Dados Estatísticos", arquivo, "Atos de Concentração Gerais", "Múltiplas Empresas", "Análise Retrospectiva", "Múltiplos Mercados", "Base de Dados", "Remédios Ge[...] "])
        continue

    try:
        leitor = pypdf.PdfReader(caminho_completo)
        texto = ""
        for i in range(min(len(leitor.pages), 15)):
            texto += leitor.pages[i].extract_text() or ""
    except Exception:
        logging.exception(f"Failed to read or extract text from {caminho_completo}; skipping file.")
        continue

    prompt = f"Analise o texto e extraia em uma linha com no maximo 12 palavras por campo separados por '|': Número do Processo | Conduta Investigada | Plataforma Envolvida | Teoria do Dano | Mer[...]"
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.0}

    try:
        resposta = requests.post(url_groq, json=payload, headers=headers_groq)
        if resposta.status_code == 200:
            partes = [p.strip() for p in resposta.json()['choices'][0]['message']['content'].strip().split('|')]
            while len(partes) < 7: partes.append("Não identificado")
            planilha.append_row([partes[0], arquivo, partes[1], partes[2], partes[3], partes[4], partes[5], partes[6]])
        else:
            logging.error(f"GROQ API returned status {resposta.status_code} for file {arquivo}: {resposta.text}")
    except Exception:
        logging.exception("Request to GROQ API failed")
    time.sleep(2)
