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


COLUNAS_DOU = dict(coluna_orgao="Órgão/Instituição", coluna_titulo="Título do Edital",
                    coluna_data="Data Publicação", coluna_link="Link do Diário Oficial")
COLUNAS_PNCP = dict(coluna_orgao="Órgão", coluna_titulo="Objeto da Contratação",
                     coluna_data="Data Publicação", coluna_link="Link")


def _montar_lista_html(df: pd.DataFrame, coluna_orgao: str, coluna_titulo: str,
                        coluna_data: str, coluna_link: str) -> str:
    if len(df) == 0:
        return "<p style='color:#888;'>Nenhum resultado neste período.</p>"
    linhas = []
    for _, row in df.iterrows():
        linhas.append(
            f"<li style='margin-bottom:10px;'>"
            f"<b>{row.get(coluna_orgao, '')}</b> — {row.get(coluna_titulo, '')}<br>"
            f"<span style='color:#666;font-size:13px;'>"
            f"{row.get(coluna_data, '')} · "
            f"<a href='{row.get(coluna_link, '')}'>ver detalhes</a></span>"
            f"</li>"
        )
    return "<ul style='padding-left:18px;'>" + "".join(linhas) + "</ul>"


def _montar_corpo_html(
    df: pd.DataFrame,
    titulo: str,
    tipo: str = "dou",
    df_extra: "pd.DataFrame | None" = None,
    titulo_extra: str | None = None,
) -> str:
    colunas_principal = COLUNAS_DOU if tipo == "dou" else COLUNAS_PNCP
    rotulo_principal = "📰 Editais de Fomento (DOU)" if tipo == "dou" else "📄 Licitações (PNCP)"
    bloco_principal = _montar_lista_html(df, **colunas_principal)

    bloco_extra_html = ""
    if df_extra is not None:
        # a seção extra é sempre do "outro" tipo em relação à principal
        colunas_extra = COLUNAS_PNCP if tipo == "dou" else COLUNAS_DOU
        bloco_extra = _montar_lista_html(df_extra, **colunas_extra)
        bloco_extra_html = f"""
        <h3 style="margin-top:22px;">📄 {titulo_extra or 'Resultados adicionais'} — {len(df_extra)} encontrado(s)</h3>
        {bloco_extra}
        """

    return f"""
    <div style="font-family: Calibri, Arial, sans-serif; color: #13294B;">
        <div style="background-color:#13294B; padding:16px 20px; border-radius:8px;">
            <h2 style="color:white; margin:0;">🔎 {titulo}</h2>
        </div>
        <div style="padding: 16px 4px;">
            <h3 style="margin-top:0;">{rotulo_principal} — {len(df)} encontrado(s)</h3>
            <p>A planilha completa está em anexo.</p>
            {bloco_principal}
            {bloco_extra_html}
        </div>
        <p style="color:#888; font-size:12px;">
            Radar de Editais FUNPEC — busca automática no Diário Oficial da União (in.gov.br)
            {" e no Portal Nacional de Contratações Públicas (pncp.gov.br)" if df_extra is not None else ""}.
        </p>
    </div>
    """


def enviar_email_com_planilha(
    destinatarios: list[str],
    df: pd.DataFrame,
    assunto: str,
    tipo: str = "dou",
    remetente: str | None = None,
    senha_app: str | None = None,
    df_extra: "pd.DataFrame | None" = None,
    titulo_extra: str | None = None,
) -> None:
    """Envia e-mail HTML com a(s) planilha(s) de resultados anexada(s).

    `tipo` indica se `df` é resultado do DOU ("dou") ou do PNCP ("pncp"),
    para usar os nomes de coluna corretos no corpo do e-mail.
    Se `df_extra` for informado (o "outro" tipo), o e-mail ganha uma segunda
    seção no corpo e um segundo arquivo .xlsx anexado.
    """
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

    corpo = _montar_corpo_html(df, assunto, tipo=tipo, df_extra=df_extra, titulo_extra=titulo_extra)
    msg.attach(MIMEText(corpo, "html", "utf-8"))

    def _anexar(dataframe: pd.DataFrame, nome_arquivo: str):
        if dataframe is None or len(dataframe) == 0:
            return
        buffer = io.BytesIO()
        dataframe.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        anexo = MIMEApplication(buffer.read(), Name=nome_arquivo)
        anexo["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
        msg.attach(anexo)

    _anexar(df, "radar_dou_funpec.xlsx" if tipo == "dou" else "radar_pncp_funpec.xlsx")
    if df_extra is not None:
        _anexar(df_extra, "radar_pncp_funpec.xlsx" if tipo == "dou" else "radar_dou_funpec.xlsx")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(remetente, senha_app)
        server.sendmail(remetente, destinatarios, msg.as_string())
