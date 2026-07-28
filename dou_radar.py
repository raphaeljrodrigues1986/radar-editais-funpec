"""
dou_radar.py
Motor de busca de editais de subvenção/fomento no Diário Oficial da União (in.gov.br).

Este módulo concentra a lógica que antes estava no notebook do Google Colab.
Tanto o app web (app.py) quanto o robô de e-mail diário (email_digest.py)
importam e usam a função `buscar_editais` daqui — assim a lógica de busca
existe em um único lugar e qualquer ajuste futuro (novo termo, nova
instituição, correção de bug) vale para os dois automaticamente.

Observação sobre o notebook original: o `git clone` do repositório Ro-dou
não era efetivamente usado pelo restante do código (nenhuma função de lá
era importada) — a busca real acontecia via `requests` direto no endpoint
de busca do in.gov.br. Por isso essa etapa foi removida aqui: deixa a
ferramenta mais rápida de rodar e com menos dependências para instalar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuração padrão (pode ser sobrescrita por quem está usando o app/robô)
# ---------------------------------------------------------------------------

INSTITUICOES_PADRAO = [
    "CNPq", "FINEP", "MCTI",
    "BNDES", "BNB", "Banco do Nordeste",
    "Banco do Brasil", "Caixa Econômica",
    "MinC", "Ministério da Cultura", "MS", "Ministério da Saúde",
]

TERMOS_PADRAO = [
    "subvenção econômica",
    "chamada pública",
    "edital de fomento",
    "chamada de projetos",
    "seleção pública",
]

URL_BUSCA = "https://in.gov.br"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


@dataclass
class ProgressoBusca:
    """Snapshot do andamento da busca, repassado ao callback de progresso."""
    atual: int
    total: int
    mensagem: str
    achados_ate_agora: int = 0


def _dias_uteis(dias_para_atras: int, data_referencia: Optional[datetime] = None):
    """Gera as datas úteis (sem sábado/domingo) dos últimos `dias_para_atras` dias."""
    data_referencia = data_referencia or datetime.now()
    for i in range(dias_para_atras):
        dia = data_referencia - timedelta(days=i)
        if dia.weekday() < 5:  # 0=segunda ... 4=sexta
            yield dia


def buscar_editais(
    instituicoes: list[str] = None,
    termos: list[str] = None,
    dias_para_atras: int = 7,
    timeout: float = 6.0,
    pausa_entre_requisicoes: float = 0.05,
    on_progress: Optional[Callable[[ProgressoBusca], None]] = None,
) -> pd.DataFrame:
    """
    Varre o Diário Oficial da União cruzando instituições x termos x dias úteis.

    Parâmetros
    ----------
    instituicoes: lista de nomes/siglas de órgãos a monitorar.
    termos: lista de expressões que caracterizam um edital de fomento.
    dias_para_atras: quantos dias corridos (contando hoje) olhar para trás.
    on_progress: função opcional chamada a cada combinação testada, recebendo
        um objeto ProgressoBusca — útil para exibir barra de progresso na
        interface (Streamlit) ou logar no console/GitHub Actions.

    Retorna
    -------
    DataFrame com uma linha por edital único encontrado (duplicados pelo
    link do Diário Oficial são removidos).
    """
    instituicoes = instituicoes or INSTITUICOES_PADRAO
    termos = termos or TERMOS_PADRAO

    dias = [d for d in _dias_uteis(dias_para_atras)]
    total_combinacoes = len(dias) * len(instituicoes) * len(termos)

    dados_planilha: list[dict] = []
    contador = 0
    session = requests.Session()

    for dia_analisado in dias:
        data_formatada = dia_analisado.strftime("%d/%m/%Y")

        for inst in instituicoes:
            for termo in termos:
                contador += 1
                expressao_busca = f"{inst} {termo}"

                if on_progress:
                    on_progress(ProgressoBusca(
                        atual=contador,
                        total=total_combinacoes,
                        mensagem=f"{data_formatada} · {inst} · \"{termo}\"",
                        achados_ate_agora=len(dados_planilha),
                    ))

                params = {
                    "q": expressao_busca,
                    "txtDataInicio": data_formatada,
                    "txtDataFim": data_formatada,
                    "secao": "all",
                    "sort": "score",
                }

                try:
                    response = session.get(
                        URL_BUSCA, params=params, headers=HEADERS, timeout=timeout
                    )
                    if response.status_code == 200 and response.text.strip().startswith("{"):
                        artigos = response.json().get("artigos", [])
                        for artigo in artigos:
                            dados_planilha.append({
                                "Data Publicação": data_formatada,
                                "Órgão/Instituição": inst,
                                "Termo Encontrado": termo,
                                "Título do Edital": artigo.get("title"),
                                "Seção": artigo.get("secao"),
                                "Página": artigo.get("pagina"),
                                "Link do Diário Oficial": f"https://in.gov.br{artigo.get('urlTitle')}",
                            })
                    time.sleep(pausa_entre_requisicoes)
                except Exception:
                    # Falha pontual de rede não deve interromper a varredura inteira
                    continue

    if not dados_planilha:
        return pd.DataFrame(columns=[
            "Data Publicação", "Órgão/Instituição", "Termo Encontrado",
            "Título do Edital", "Seção", "Página", "Link do Diário Oficial",
        ])

    df = pd.DataFrame(dados_planilha)
    df.drop_duplicates(subset=["Link do Diário Oficial"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def gerar_nome_arquivo(prefixo: str = "radar_dou") -> str:
    return f"{prefixo}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
