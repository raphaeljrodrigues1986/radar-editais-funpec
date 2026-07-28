"""
email_utils.py
Envio de e-mail com o resumo dos editais encontrados + planilha anexada.

Usa SMTP do Gmail com "senha de app" (App Password), que é gratuito e não
exige contratar nenhum serviço externo. Passo a passo de configuração no
README.md.

Credenciais são lidas de variáveis de ambiente (nunca fique com senha
escrita direto no código):
  EMAIL_REMETENTE       -> ex: radar.editais.funpec@gmail.com
  EMAIL_SENHA_APP        -> a senha de app gerada no Google (16 caracteres)
"""

from __future__ import annotations

import io
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _montar_corpo_html(df: pd.DataFrame, titulo: str) -> str:
    if len(df) == 0:
        linhas_html = "<p>Nenhum edital encontrado no período verificado.</p>"
    else:
        linhas = []
        for _, row in df.iterrows():
            linhas.append(
                f"<li style='margin-bottom:10px;'>"
                f"<b>{row['Órgão/Instituição']}</b> — {row['Título do Edital']}<br>"
                f"<span style='color:#666;font-size:13px;'>"
                f"{row['Data Publicação']} · Seção {row['Seção']} · "
                f"<a href='{row['Link do Diário Oficial']}'>ver no Diário Oficial</a></span>"
                f"</li>"
            )
        linhas_html = "<ul style='padding-left:18px;'>" + "".join(linhas) + "</ul>"

    return f"""
    <div style="font-family: Calibri, Arial, sans-serif; color: #13294B;">
        <div style="background-color:#13294B; padding:16px 20px; border-radius:8px;">
            <h2 style="color:white; margin:0;">🔎 {titulo}</h2>
        </div>
        <div style="padding: 16px 4px;">
            <p>{len(df)} edital(is) encontrado(s). A planilha completa está em anexo.</p>
            {linhas_html}
        </div>
        <p style="color:#888; font-size:12px;">
            Radar de Editais FUNPEC — busca automática no Diário Oficial da União (in.gov.br).
        </p>
    </div>
    """


def enviar_email_com_planilha(
    destinatarios: list[str],
    df: pd.DataFrame,
    assunto: str,
    remetente: str | None = None,
    senha_app: str | None = None,
) -> None:
    """Envia e-mail HTML com a planilha (.xlsx) dos resultados anexada."""
    remetente = remetente or os.environ.get("EMAIL_REMETENTE")
    senha_app = senha_app or os.environ.get("EMAIL_SENHA_APP")

    if not remetente or not senha_app:
        raise RuntimeError(
            "Credenciais de e-mail não configuradas. Defina as variáveis de ambiente "
            "EMAIL_REMETENTE e EMAIL_SENHA_APP (veja o README.md)."
        )

    msg = MIMEMultipart("mixed")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)

    corpo = _montar_corpo_html(df, assunto)
    msg.attach(MIMEText(corpo, "html", "utf-8"))

    if len(df) > 0:
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        anexo = MIMEApplication(buffer.read(), Name="radar_dou_funpec.xlsx")
        anexo["Content-Disposition"] = 'attachment; filename="radar_dou_funpec.xlsx"'
        msg.attach(anexo)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(remetente, senha_app)
        server.sendmail(remetente, destinatarios, msg.as_string())
