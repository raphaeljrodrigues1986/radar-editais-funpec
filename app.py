"""
app.py — Radar de Editais FUNPEC
Plataforma web simples para qualquer pessoa da FUNPEC pesquisar editais de
subvenção/fomento publicados no Diário Oficial da União, sem precisar
saber programar ou usar o Google Colab.

Como publicar (uma vez só, feito por quem configurou):
  1. Suba esta pasta em um repositório no GitHub.
  2. Entre em https://share.streamlit.io, conecte o repositório e aponte
     para este arquivo (app.py). É gratuito.
  3. Pronto: a plataforma passa a ter um link fixo que qualquer pessoa
     da FUNPEC pode abrir no navegador (celular ou computador).

Veja o README.md para o passo a passo completo com prints.
"""

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from dou_radar import INSTITUICOES_PADRAO, TERMOS_PADRAO, buscar_editais, gerar_nome_arquivo
from email_utils import enviar_email_com_planilha

# ---------------------------------------------------------------------------
# Configuração visual da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Radar de Editais — FUNPEC",
    page_icon="🔎",
    layout="wide",
)

NAVY = "#13294B"
BLUE = "#1565C0"
BLUE_LIGHT = "#E8F1FC"

st.markdown(f"""
<style>
    .stApp {{ background-color: #FFFFFF; }}
    .funpec-header {{
        background-color: {NAVY};
        padding: 1.4rem 1.8rem;
        border-radius: 10px;
        margin-bottom: 1.4rem;
    }}
    .funpec-header h1 {{
        color: white; font-size: 1.6rem; margin: 0;
    }}
    .funpec-header p {{
        color: #C7D9F2; margin: 0.3rem 0 0 0; font-size: 0.95rem;
    }}
    .stButton>button {{
        background-color: {BLUE}; color: white; border: none;
        border-radius: 6px; padding: 0.55rem 1.4rem; font-weight: 600;
    }}
    .stButton>button:hover {{ background-color: {NAVY}; color: white; }}
    div[data-testid="stMetric"] {{
        background-color: {BLUE_LIGHT}; padding: 0.8rem; border-radius: 8px;
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="funpec-header">
    <h1>🔎 Radar de Editais FUNPEC</h1>
    <p>Busca automática de editais de subvenção, fomento e chamadas públicas no Diário Oficial da União</p>
</div>
""", unsafe_allow_html=True)

# Se você tiver o arquivo da logo da FUNPEC, coloque-o na pasta como
# "logo_funpec.png" e descomente a linha abaixo para exibi-la na barra lateral.
# st.sidebar.image("logo_funpec.png", use_container_width=True)

st.sidebar.header("Parâmetros da busca")

instituicoes_selecionadas = st.sidebar.multiselect(
    "Órgãos e instituições a monitorar",
    options=INSTITUICOES_PADRAO,
    default=INSTITUICOES_PADRAO,
    help="Você pode remover instituições que não interessam para deixar a busca mais rápida.",
)
outras_instituicoes = st.sidebar.text_input(
    "Adicionar outras instituições (separadas por vírgula)", value=""
)
if outras_instituicoes.strip():
    instituicoes_selecionadas += [i.strip() for i in outras_instituicoes.split(",") if i.strip()]

termos_selecionados = st.sidebar.multiselect(
    "Termos que caracterizam um edital",
    options=TERMOS_PADRAO,
    default=TERMOS_PADRAO,
)
outros_termos = st.sidebar.text_input(
    "Adicionar outros termos (separados por vírgula)", value=""
)
if outros_termos.strip():
    termos_selecionados += [t.strip() for t in outros_termos.split(",") if t.strip()]

dias_para_atras = st.sidebar.slider(
    "Quantos dias corridos para trás olhar?", min_value=1, max_value=30, value=7
)

st.sidebar.caption(
    f"⏱️ Estimativa: {len(instituicoes_selecionadas) * len(termos_selecionados) * dias_para_atras} "
    "combinações serão verificadas. Buscas maiores podem levar alguns minutos."
)

buscar = st.sidebar.button("🔍 Buscar Editais", use_container_width=True, type="primary")

# ---------------------------------------------------------------------------
# Execução da busca
# ---------------------------------------------------------------------------
if "resultados" not in st.session_state:
    st.session_state.resultados = None

if buscar:
    if not instituicoes_selecionadas or not termos_selecionados:
        st.warning("Selecione ao menos uma instituição e um termo antes de buscar.")
    else:
        barra = st.progress(0, text="Iniciando varredura...")
        status = st.empty()

        def atualizar_progresso(p):
            fracao = p.atual / max(p.total, 1)
            barra.progress(min(fracao, 1.0), text=f"Verificando {p.mensagem}  ({p.atual}/{p.total})")
            status.caption(f"✨ {p.achados_ate_agora} edital(is) encontrado(s) até agora")

        with st.spinner("Consultando o Diário Oficial da União..."):
            df = buscar_editais(
                instituicoes=instituicoes_selecionadas,
                termos=termos_selecionados,
                dias_para_atras=dias_para_atras,
                on_progress=atualizar_progresso,
            )
        barra.empty()
        status.empty()
        st.session_state.resultados = df
        st.session_state.busca_em = datetime.now().strftime("%d/%m/%Y às %H:%M")

# ---------------------------------------------------------------------------
# Exibição dos resultados
# ---------------------------------------------------------------------------
df = st.session_state.resultados

if df is not None:
    st.caption(f"Última busca: {st.session_state.busca_em}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Editais encontrados", len(df))
    col2.metric("Instituições com resultado", df["Órgão/Instituição"].nunique() if len(df) else 0)
    col3.metric("Dias verificados", dias_para_atras)

    if len(df) == 0:
        st.info("Nenhum edital encontrado no período e critérios selecionados. Tente ampliar o número de dias.")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Link do Diário Oficial": st.column_config.LinkColumn("Link do Diário Oficial"),
            },
            hide_index=True,
        )

        # ---- download da planilha ----
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        nome_arquivo = gerar_nome_arquivo("radar_dou_funpec")

        st.download_button(
            "📥 Baixar planilha (Excel)",
            data=buffer,
            file_name=nome_arquivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # ---- envio por e-mail ----
        with st.expander("✉️ Enviar esses resultados por e-mail"):
            destinatarios = st.text_input(
                "E-mail(s) de destino (separados por vírgula)",
                placeholder="fulano@funpec.br, ciclana@funpec.br",
            )
            if st.button("Enviar e-mail agora"):
                if not destinatarios.strip():
                    st.warning("Informe ao menos um e-mail de destino.")
                else:
                    try:
                        enviar_email_com_planilha(
                            destinatarios=[e.strip() for e in destinatarios.split(",") if e.strip()],
                            df=df,
                            assunto=f"Radar de Editais FUNPEC — {len(df)} resultado(s)",
                        )
                        st.success("E-mail enviado com sucesso!")
                    except Exception as e:
                        st.error(f"Não foi possível enviar o e-mail: {e}")
else:
    st.info("Defina os parâmetros na barra lateral e clique em **Buscar Editais** para começar.")

st.divider()
st.caption(
    "Fonte: Diário Oficial da União (in.gov.br). Ferramenta interna FUNPEC — uso conforme "
    "disponibilidade da API pública do governo."
)
