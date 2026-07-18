import os
import time
import requests
import gspread
import pypdf
import json
from google.oauth2.service_account import Credentials

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
arquivos = [f for f in os.listdir(PASTA_DOCUMENTOS) if f.endswith(('.pdf', '.rar'))]

for arquivo in arquivos:
    caminho_completo = os.path.join(PASTA_DOCUMENTOS, arquivo)
    if arquivo.endswith('.rar'):
        planilha.append_row(["Dados Estatísticos", arquivo, "Atos de Concentração Gerais", "Múltiplas Empresas", "Análise Retrospectiva", "Múltiplos Mercados", "Base de Dados", "Remédios Gerais"])
        continue

    try:
        leitor = pypdf.PdfReader(caminho_completo)
        texto = ""
        for i in range(min(len(leitor.pages), 15)):
            texto += leitor.pages[i].extract_text() or ""
    except:
        continue

    prompt = f"Analise o texto e extraia em uma linha com no maximo 12 palavras por campo separados por '|': Número do Processo | Conduta Investigada | Plataforma Envolvida | Teoria do Dano | Mercado Relevante | Status do Caso | Remédios Aplicados\\n\\nTexto:\\n{texto[:15000]}"
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.0}

    try:
        resposta = requests.post(url_groq, json=payload, headers=headers_groq)
        if resposta.status_code == 200:
            partes = [p.strip() for p in resposta.json()['choices'][0]['message']['content'].strip().split('|')]
            while len(partes) < 7: partes.append("Não identificado")
            planilha.append_row([partes[0], arquivo, partes[1], partes[2], partes[3], partes[4], partes[5], partes[6]])
    except:
        pass
    time.sleep(2)
