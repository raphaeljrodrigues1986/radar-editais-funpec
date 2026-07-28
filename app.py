"""
app.py — Radar de Editais e Licitações FUNPEC
Plataforma web para pesquisar, sem precisar programar:
  1) Editais de subvenção/fomento no Diário Oficial da União (DOU)
  2) Licitações no Portal Nacional de Contratações Públicas (PNCP)

Veja o README.md para o passo a passo de publicação.
"""

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from dou_radar import INSTITUICOES_PADRAO, TERMOS_PADRAO, buscar_editais, gerar_nome_arquivo
from pncp_radar import MODALIDADES, MODALIDADES_PADRAO, TERMOS_PADRAO as PNCP_TERMOS_PADRAO, buscar_licitacoes
from email_utils import enviar_email_com_planilha

# ---------------------------------------------------------------------------
# Configuração visual da página
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Radar de Editais — FUNPEC", page_icon="🔎", layout="wide")

NAVY = "#13294B"
BLUE = "#1565C0"
BLUE_LIGHT = "#E8F1FC"

st.markdown(f"""
<style>
    .stApp {{ background-color: #FFFFFF; }}
    .funpec-header {{
        background-color: {NAVY}; padding: 1.4rem 1.8rem; border-radius: 10px; margin-bottom: 1.2rem;
    }}
    .funpec-header h1 {{ color: white; font-size: 1.6rem; margin: 0; }}
    .funpec-header p {{ color: #C7D9F2; margin: 0.3rem 0 0 0; font-size: 0.95rem; }}
    .stButton>button {{
        background-color: {BLUE}; color: white; border: none;
        border-radius: 6px; padding: 0.55rem 1.4rem; font-weight: 600;
    }}
    .stButton>button:hover {{ background-color: {NAVY}; color: white; }}
    div[data-testid="stMetric"] {{ background-color: {BLUE_LIGHT}; padding: 0.8rem; border-radius: 8px; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="funpec-header">
    <h1>🔎 Radar de Editais e Licitações FUNPEC</h1>
    <p>Editais de subvenção/fomento (DOU) e licitações (PNCP) em um só lugar</p>
</div>
""", unsafe_allow_html=True)

# Se você tiver o arquivo da logo da FUNPEC, coloque-o na pasta como
# "logo_funpec.png" e descomente a linha abaixo.
# st.sidebar.image("logo_funpec.png", use_container_width=True)


def bloco_download_e_email(df: pd.DataFrame, chave: str, nome_planilha_prefixo: str):
    """Botões de download em Excel e envio por e-mail, reaproveitados nas duas abas.
    `chave` deve ser "dou" ou "pncp" para o e-mail usar as colunas certas."""
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    nome_arquivo = gerar_nome_arquivo(nome_planilha_prefixo)

    st.download_button(
        "📥 Baixar planilha (Excel)", data=buffer, file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"download_{chave}",
    )

    with st.expander("✉️ Enviar esses resultados por e-mail"):
        destinatarios = st.text_input(
            "E-mail(s) de destino (separados por vírgula)",
            placeholder="fulano@funpec.br, ciclana@funpec.br", key=f"email_input_{chave}",
        )
        if st.button("Enviar e-mail agora", key=f"email_btn_{chave}"):
            if not destinatarios.strip():
                st.warning("Informe ao menos um e-mail de destino.")
            else:
                try:
                    enviar_email_com_planilha(
                        destinatarios=[e.strip() for e in destinatarios.split(",") if e.strip()],
                        df=df, assunto=f"Radar FUNPEC — {len(df)} resultado(s)", tipo=chave,
                    )
                    st.success("E-mail enviado com sucesso!")
                except Exception as e:
                    st.error(f"Não foi possível enviar o e-mail: {e}")


def multiselect_editavel(label: str, options: list, default: list, key: str):
    """Multiselect em que a pessoa pode digitar uma palavra nova e apertar
    Enter para adicioná-la à lista, além de escolher as sugestões prontas.

    Se por algum motivo a versão do Streamlit publicada não tiver esse
    recurso (accept_new_options, disponível nas versões recentes), o app
    cai automaticamente para um campo de texto extra abaixo, sem quebrar.
    """
    try:
        return st.multiselect(
            label, options=options, default=default, key=key,
            accept_new_options=True,
            placeholder="Escolha ou digite e aperte Enter para adicionar",
        )
    except TypeError:
        selecionados = st.multiselect(label, options=options, default=default, key=f"{key}_base")
        extras = st.text_input(
            f"Adicionar outros itens (separados por vírgula)", key=f"{key}_extra"
        )
        if extras.strip():
            selecionados = selecionados + [e.strip() for e in extras.split(",") if e.strip()]
        return selecionados


# ---------------------------------------------------------------------------
# Abas
# ---------------------------------------------------------------------------
aba_dou, aba_pncp = st.tabs(["📰 Editais de Fomento (DOU)", "📄 Licitações (PNCP)"])

# =============================== ABA 1: DOU =================================
with aba_dou:
    st.caption("Busca editais de subvenção econômica, chamadas públicas e editais de fomento no Diário Oficial da União.")

    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        instituicoes_sel = multiselect_editavel(
            "Órgãos e instituições a monitorar", INSTITUICOES_PADRAO, INSTITUICOES_PADRAO, "dou_inst"
        )
    with col_b:
        termos_sel = multiselect_editavel(
            "Termos que caracterizam um edital", TERMOS_PADRAO, TERMOS_PADRAO, "dou_termos"
        )
    with col_c:
        dias_dou = st.slider("Dias corridos para trás", 1, 30, 7, key="dou_dias")
        st.caption(f"⏱️ ~{len(instituicoes_sel) * len(termos_sel) * dias_dou} combinações")

    if st.button("🔍 Buscar Editais de Fomento", key="dou_buscar", type="primary"):
        if not instituicoes_sel or not termos_sel:
            st.warning("Selecione ao menos uma instituição e um termo.")
        else:
            barra = st.progress(0, text="Iniciando varredura...")
            status = st.empty()

            def prog_dou(p):
                barra.progress(min(p.atual / max(p.total, 1), 1.0), text=f"Verificando {p.mensagem} ({p.atual}/{p.total})")
                status.caption(f"✨ {p.achados_ate_agora} edital(is) encontrado(s) até agora")

            with st.spinner("Consultando o Diário Oficial da União..."):
                df_dou = buscar_editais(instituicoes_sel, termos_sel, dias_dou, on_progress=prog_dou)
            barra.empty()
            status.empty()
            st.session_state["resultados_dou"] = df_dou
            st.session_state["busca_dou_em"] = datetime.now().strftime("%d/%m/%Y às %H:%M")

    df_dou = st.session_state.get("resultados_dou")
    if df_dou is not None:
        st.caption(f"Última busca: {st.session_state.get('busca_dou_em', '')}")
        c1, c2 = st.columns(2)
        c1.metric("Editais encontrados", len(df_dou))
        c2.metric("Instituições com resultado", df_dou["Órgão/Instituição"].nunique() if len(df_dou) else 0)

        if len(df_dou) == 0:
            st.info("Nenhum edital encontrado no período e critérios selecionados.")
        else:
            st.dataframe(
                df_dou, use_container_width=True, hide_index=True,
                column_config={"Link do Diário Oficial": st.column_config.LinkColumn("Link do Diário Oficial")},
            )
            bloco_download_e_email(df_dou, "dou", "radar_dou_funpec")
    else:
        st.info("Defina os parâmetros acima e clique em **Buscar Editais de Fomento** para começar.")

# =============================== ABA 2: PNCP =================================
with aba_pncp:
    st.caption(
        "Busca licitações (compras/contratações) no Portal Nacional de Contratações Públicas — "
        "útil quando a FUNPEC/NTCPP quer prestar serviços técnicos a outros órgãos."
    )
    st.info(
        "⚠️ Esta aba é nova e ainda não foi validada contra a API real do PNCP. "
        "Se algum resultado parecer estranho ou vier vazio sempre, me avise para ajustarmos.",
        icon="ℹ️",
    )

    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        modalidades_nomes = {v: k for k, v in MODALIDADES.items()}
        modalidades_sel_nomes = st.multiselect(
            "Modalidades de contratação",
            options=list(MODALIDADES.values()),
            default=[MODALIDADES[c] for c in MODALIDADES_PADRAO],
            key="pncp_modalidades",
        )
        modalidades_sel = [modalidades_nomes[n] for n in modalidades_sel_nomes]
    with col_b:
        termos_pncp_sel = multiselect_editavel(
            "Termos que devem aparecer no objeto da contratação", PNCP_TERMOS_PADRAO, PNCP_TERMOS_PADRAO, "pncp_termos"
        )
    with col_c:
        dias_pncp = st.slider("Dias corridos para trás", 1, 30, 7, key="pncp_dias")
        st.caption(f"⏱️ ~{len(modalidades_sel) * dias_pncp} consultas (+ paginação)")

    if st.button("🔍 Buscar Licitações", key="pncp_buscar", type="primary"):
        if not modalidades_sel or not termos_pncp_sel:
            st.warning("Selecione ao menos uma modalidade e um termo.")
        else:
            barra = st.progress(0, text="Iniciando varredura...")
            status = st.empty()

            def prog_pncp(p):
                barra.progress(min(p.atual / max(p.total, 1), 1.0), text=f"Verificando {p.mensagem} ({p.atual}/{p.total})")
                status.caption(f"✨ {p.achados_ate_agora} licitação(ões) encontrada(s) até agora")

            with st.spinner("Consultando o PNCP..."):
                try:
                    df_pncp = buscar_licitacoes(termos_pncp_sel, dias_pncp, modalidades_sel, on_progress=prog_pncp)
                    st.session_state["resultados_pncp"] = df_pncp
                    st.session_state["busca_pncp_em"] = datetime.now().strftime("%d/%m/%Y às %H:%M")
                except Exception as e:
                    st.error(f"Erro ao consultar o PNCP: {e}")
            barra.empty()
            status.empty()

    df_pncp = st.session_state.get("resultados_pncp")
    if df_pncp is not None:
        st.caption(f"Última busca: {st.session_state.get('busca_pncp_em', '')}")
        c1, c2 = st.columns(2)
        c1.metric("Licitações encontradas", len(df_pncp))
        c2.metric("Órgãos com resultado", df_pncp["Órgão"].nunique() if len(df_pncp) else 0)

        if len(df_pncp) == 0:
            st.info("Nenhuma licitação encontrada no período e critérios selecionados.")
        else:
            st.dataframe(
                df_pncp, use_container_width=True, hide_index=True,
                column_config={"Link": st.column_config.LinkColumn("Link")},
            )
            bloco_download_e_email(df_pncp, "pncp", "radar_pncp_funpec")
    else:
        st.info("Defina os parâmetros acima e clique em **Buscar Licitações** para começar.")

st.divider()
st.caption(
    "Fontes: Diário Oficial da União (in.gov.br) e Portal Nacional de Contratações Públicas (pncp.gov.br). "
    "Ferramenta interna FUNPEC — uso conforme disponibilidade das APIs públicas do governo."
)
