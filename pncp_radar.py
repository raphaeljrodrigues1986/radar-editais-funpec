"""
pncp_radar.py
Motor de busca de licitações no Portal Nacional de Contratações Públicas (PNCP).

Diferente do Diário Oficial da União (editais de FOMENTO — dinheiro que entra),
o PNCP é onde os órgãos públicos publicam LICITAÇÕES (compras de bens e
serviços — a FUNPEC/NTCPP entraria como fornecedor/prestador de serviço, ex:
ensaios laboratoriais, consultoria técnica).

A API pública de consulta do PNCP não tem um campo de "palavra-chave" livre
no servidor — o filtro por termo é feito aqui no lado do cliente, sobre o
campo `objetoCompra` (o texto que descreve o que está sendo contratado).
Esse é o mesmo padrão usado por outras integrações públicas com essa API.

Documentação oficial: https://www.gov.br/pncp/pt-br/acesso-a-informacao/manuais
Endpoint usado: GET https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao

IMPORTANTE: este módulo não pôde ser testado contra a API real no momento em
que foi escrito (ambiente sem acesso a pncp.gov.br). A estrutura dos campos
retornados foi baseada na documentação oficial e em exemplos públicos — é
recomendável rodar um teste manual logo após publicar e ajustar nomes de
campo em `_extrair_linha` caso a API devolva algo ligeiramente diferente.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

import pandas as pd
import requests

URL_BASE = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"

# Código -> nome da modalidade de contratação (tabela de domínio do PNCP)
MODALIDADES = {
    1: "Concorrência",
    2: "Concorrência Eletrônica",
    4: "Concurso",
    5: "Leilão",
    6: "Pregão Eletrônico",
    7: "Pregão Presencial",
    8: "Dispensa",
    9: "Inexigibilidade",
    12: "Credenciamento",
}

MODALIDADES_PADRAO = [6, 8, 1, 12]  # Pregão Eletrônico, Dispensa, Concorrência, Credenciamento

TERMOS_PADRAO = [
    "cimentação de poços",
    "ensaios laboratoriais",
    "consultoria técnica especializada",
    "prestação de serviços técnicos",
    "pesquisa e desenvolvimento",
]

HEADERS = {"Accept": "application/json"}


@dataclass
class ProgressoBusca:
    atual: int
    total: int
    mensagem: str
    achados_ate_agora: int = 0


def _dias_uteis(dias_para_atras: int, data_referencia: Optional[datetime] = None):
    data_referencia = data_referencia or datetime.now()
    for i in range(dias_para_atras):
        dia = data_referencia - timedelta(days=i)
        if dia.weekday() < 5:
            yield dia


def _extrair_linha(item: dict, termo_casado: str) -> dict:
    """Converte um item da resposta da API em uma linha da planilha."""
    orgao = (item.get("orgaoEntidade") or {}).get("razaoSocial") or item.get("orgaoEntidade", {}).get("nomeRazaoSocial", "")
    unidade = (item.get("unidadeOrgao") or {}).get("nomeUnidade", "")
    link = item.get("linkSistemaOrigem") or ""
    if not link:
        # Monta um link de busca no próprio portal como alternativa
        numero_controle = item.get("numeroControlePNCP", "")
        link = f"https://pncp.gov.br/app/editais?q={numero_controle}"

    return {
        "Data Publicação": item.get("dataPublicacaoPncp", "")[:10] if item.get("dataPublicacaoPncp") else "",
        "Órgão": orgao,
        "Unidade": unidade,
        "Modalidade": item.get("modalidadeNome") or MODALIDADES.get(item.get("modalidadeId"), ""),
        "Termo Encontrado": termo_casado,
        "Objeto da Contratação": item.get("objetoCompra", ""),
        "Encerramento Propostas": (item.get("dataEncerramentoProposta") or "")[:16].replace("T", " "),
        "Situação": item.get("situacaoCompraNome", ""),
        "Link": link,
    }


def buscar_licitacoes(
    termos: list[str] = None,
    dias_para_atras: int = 7,
    modalidades: list[int] = None,
    timeout: float = 8.0,
    pausa_entre_requisicoes: float = 0.1,
    tamanho_pagina: int = 50,
    on_progress: Optional[Callable[[ProgressoBusca], None]] = None,
) -> pd.DataFrame:
    """
    Varre o PNCP por licitações publicadas nos últimos `dias_para_atras` dias
    cujo objeto de contratação contenha algum dos `termos`.
    """
    termos = termos or TERMOS_PADRAO
    modalidades = modalidades or MODALIDADES_PADRAO

    dias = list(_dias_uteis(dias_para_atras))
    total_combinacoes = len(dias) * len(modalidades)

    dados_planilha: list[dict] = []
    contador = 0
    session = requests.Session()

    for dia in dias:
        data_str = dia.strftime("%Y%m%d")

        for cod_modalidade in modalidades:
            contador += 1
            nome_modalidade = MODALIDADES.get(cod_modalidade, str(cod_modalidade))

            if on_progress:
                on_progress(ProgressoBusca(
                    atual=contador,
                    total=total_combinacoes,
                    mensagem=f"{dia.strftime('%d/%m/%Y')} · {nome_modalidade}",
                    achados_ate_agora=len(dados_planilha),
                ))

            pagina = 1
            while True:
                params = {
                    "dataInicial": data_str,
                    "dataFinal": data_str,
                    "codigoModalidadeContratacao": cod_modalidade,
                    "pagina": pagina,
                    "tamanhoPagina": tamanho_pagina,
                }
                try:
                    resp = session.get(URL_BASE, params=params, headers=HEADERS, timeout=timeout)
                    if resp.status_code != 200:
                        break
                    corpo = resp.json()
                    itens = corpo.get("data", corpo if isinstance(corpo, list) else [])

                    for item in itens:
                        objeto = (item.get("objetoCompra") or "").lower()
                        for termo in termos:
                            if termo.lower() in objeto:
                                dados_planilha.append(_extrair_linha(item, termo))
                                break  # não duplica o mesmo item por mais de um termo

                    total_paginas = corpo.get("totalPaginas", 1) if isinstance(corpo, dict) else 1
                    if pagina >= total_paginas or not itens:
                        break
                    pagina += 1
                    time.sleep(pausa_entre_requisicoes)
                except Exception:
                    break

            time.sleep(pausa_entre_requisicoes)

    colunas = ["Data Publicação", "Órgão", "Unidade", "Modalidade", "Termo Encontrado",
               "Objeto da Contratação", "Encerramento Propostas", "Situação", "Link"]
    if not dados_planilha:
        return pd.DataFrame(columns=colunas)

    df = pd.DataFrame(dados_planilha)
    df.drop_duplicates(subset=["Link", "Objeto da Contratação"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df
