"""
email_digest.py
Roda sozinho (disparado pelo GitHub Actions, veja .github/workflows/daily_digest.yml)
e manda por e-mail o resumo dos editais publicados no(s) último(s) dia(s).

Ninguém na FUNPEC precisa abrir nada para isso acontecer — é 100% automático.
"""

import os
import sys

from dou_radar import buscar_editais
from email_utils import enviar_email_com_planilha

# Quantos dias corridos verificar na varredura automática diária.
# 3 dias cobre com folga finais de semana/feriados entre uma execução e outra.
DIAS_PARA_ATRAS = int(os.environ.get("DIGEST_DIAS_PARA_ATRAS", "3"))

# Lista de destinatários fixos do resumo diário, separada por vírgula
# na variável de ambiente DIGEST_DESTINATARIOS (configurada como Secret
# no GitHub Actions — veja o README.md).
DESTINATARIOS = [
    e.strip() for e in os.environ.get("DIGEST_DESTINATARIOS", "").split(",") if e.strip()
]


def main() -> int:
    if not DESTINATARIOS:
        print("⚠️  Nenhum destinatário configurado em DIGEST_DESTINATARIOS. Abortando.")
        return 1

    print(f"⚡ Radar diário FUNPEC — verificando os últimos {DIAS_PARA_ATRAS} dia(s)...")

    def log_progresso(p):
        if p.atual % 20 == 0 or p.atual == p.total:
            print(f"  [{p.atual}/{p.total}] {p.mensagem} — {p.achados_ate_agora} achado(s) até agora")

    df = buscar_editais(dias_para_atras=DIAS_PARA_ATRAS, on_progress=log_progresso)

    print(f"✅ Varredura concluída: {len(df)} edital(is) único(s) encontrado(s).")

    enviar_email_com_planilha(
        destinatarios=DESTINATARIOS,
        df=df,
        assunto=f"Radar de Editais FUNPEC — resumo diário ({len(df)} resultado(s))",
    )
    print(f"✉️  E-mail enviado para: {', '.join(DESTINATARIOS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
