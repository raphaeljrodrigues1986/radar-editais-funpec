"""
email_digest.py
Roda sozinho (disparado pelo GitHub Actions, veja .github/workflows/daily_digest.yml)
e manda por e-mail o resumo dos editais de fomento (DOU) e das licitações
(PNCP) publicados no(s) último(s) dia(s).

Ninguém na FUNPEC precisa abrir nada para isso acontecer — é 100% automático.
"""

import os
import sys

import pandas as pd

from dou_radar import buscar_editais
from pncp_radar import buscar_licitacoes
from email_utils import enviar_email_com_planilha

# Quantos dias corridos verificar na varredura automática diária.
DIAS_PARA_ATRAS = int(os.environ.get("DIGEST_DIAS_PARA_ATRAS", "3"))

DESTINATARIOS = [
    e.strip() for e in os.environ.get("DIGEST_DESTINATARIOS", "").split(",") if e.strip()
]

# Ligar/desligar a busca de licitações no robô diário sem precisar mexer no
# código — útil enquanto a integração com o PNCP ainda está em validação.
INCLUIR_PNCP = os.environ.get("DIGEST_INCLUIR_PNCP", "true").lower() in ("1", "true", "sim")


def log_progresso(prefixo):
    def _log(p):
        if p.atual % 20 == 0 or p.atual == p.total:
            print(f"  [{prefixo} {p.atual}/{p.total}] {p.mensagem} — {p.achados_ate_agora} achado(s) até agora")
    return _log


def main() -> int:
    if not DESTINATARIOS:
        print("⚠️  Nenhum destinatário configurado em DIGEST_DESTINATARIOS. Abortando.")
        return 1

    print(f"⚡ Radar diário FUNPEC — verificando os últimos {DIAS_PARA_ATRAS} dia(s)...")

    print("📰 Buscando editais de fomento no DOU...")
    df_dou = buscar_editais(dias_para_atras=DIAS_PARA_ATRAS, on_progress=log_progresso("DOU"))
    print(f"✅ DOU: {len(df_dou)} edital(is) único(s) encontrado(s).")

    df_pncp = pd.DataFrame()
    if INCLUIR_PNCP:
        print("📄 Buscando licitações no PNCP...")
        try:
            df_pncp = buscar_licitacoes(dias_para_atras=DIAS_PARA_ATRAS, on_progress=log_progresso("PNCP"))
            print(f"✅ PNCP: {len(df_pncp)} licitação(ões) única(s) encontrada(s).")
        except Exception as e:
            print(f"⚠️  Falha ao consultar o PNCP (seguindo só com o DOU): {e}")

    total = len(df_dou) + len(df_pncp)
    assunto = f"Radar FUNPEC — resumo diário ({len(df_dou)} edital(is) + {len(df_pncp)} licitação(ões))"

    enviar_email_com_planilha(
        destinatarios=DESTINATARIOS,
        df=df_dou,
        assunto=assunto,
        df_extra=df_pncp,
        titulo_extra="Licitações (PNCP)",
    )
    print(f"✉️  E-mail enviado para: {', '.join(DESTINATARIOS)} ({total} resultado(s) no total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
