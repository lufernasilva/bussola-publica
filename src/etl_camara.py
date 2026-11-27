"""
Bússola Pública — Etapa 1: Extração e padronização da API da Câmara dos Deputados.

Fluxo:
    API da Câmara  --(paginação + retry)-->  data/raw/*.json     (Bronze)
                   --(padronização)------->  data/silver/*.json  (Silver)

A carga no banco (UPSERT no Supabase) é da Etapa 2 e não é feita aqui.

Uso:
    python src/etl_camara.py                          # últimos 30 dias, todos os deputados
    python src/etl_camara.py --dias 7                 # janela menor
    python src/etl_camara.py --amostra-deputados 10   # despesas só de 10 deputados (teste rápido)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
ITENS_POR_PAGINA = 100      # máximo aceito pela API
PAUSA_ENTRE_PAGINAS = 0.2   # segundos, para respeitar o rate limit
TIMEOUT = 60

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "raw"
PASTA_SILVER = RAIZ / "data" / "silver"

log = logging.getLogger("etl_camara")


# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------
def criar_sessao() -> requests.Session:
    """Sessão HTTP com retry e backoff exponencial para erros transitórios (429 e 5xx)."""
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    sessao = requests.Session()
    sessao.mount("https://", HTTPAdapter(max_retries=retry))
    sessao.headers.update({"Accept": "application/json", "User-Agent": "bussola-publica-etl/1.0"})
    return sessao


def proximo_link(links: list[dict]) -> str | None:
    """Retorna o href do link 'next', ou None na última página."""
    for link in links:
        if link.get("rel") == "next":
            return link.get("href")
    return None


def extrair_paginado(sessao: requests.Session, endpoint: str, params: dict | None = None) -> list[dict]:
    """Percorre todas as páginas de um endpoint seguindo o link 'next'."""
    url: str | None = f"{BASE_URL}/{endpoint}"
    params = {**(params or {}), "itens": ITENS_POR_PAGINA}
    registros: list[dict] = []
    pagina = 0

    while url:
        resposta = sessao.get(url, params=params, timeout=TIMEOUT)
        resposta.raise_for_status()
        corpo = resposta.json()

        dados = corpo.get("dados", [])
        registros.extend(dados)
        pagina += 1
        log.debug("[%s] página %d: %d itens (acumulado %d)", endpoint, pagina, len(dados), len(registros))

        # O link 'next' já carrega os parâmetros. Se a página veio vazia, para (evita loop infinito).
        url = proximo_link(corpo.get("links", [])) if dados else None
        params = None
        if url:
            time.sleep(PAUSA_ENTRE_PAGINAS)

    log.info("%s: %d registros em %d página(s)", endpoint, len(registros), pagina)
    return registros


def extrair_tudo(data_inicio: date, data_fim: date, amostra_deputados: int | None) -> dict[str, list[dict]]:
    sessao = criar_sessao()

    partidos = extrair_paginado(sessao, "partidos")
    deputados = extrair_paginado(sessao, "deputados")

    proposicoes = extrair_paginado(sessao, "proposicoes", {
        "dataApresentacaoInicio": data_inicio.isoformat(),
        "dataApresentacaoFim": data_fim.isoformat(),
        "ordem": "ASC",
        "ordenarPor": "id",
    })

    # Em /votacoes o dataFim não inclui o último dia inteiro: envia +1 dia e filtra depois.
    votacoes = extrair_paginado(sessao, "votacoes", {
        "dataInicio": data_inicio.isoformat(),
        "dataFim": (data_fim + timedelta(days=1)).isoformat(),
    })
    votacoes = [v for v in votacoes if data_inicio.isoformat() <= v["data"] <= data_fim.isoformat()]

    # Despesas são por deputado: um while de paginação dentro de um for pelos deputados.
    ids = [d["id"] for d in deputados][:amostra_deputados]
    anos = range(data_inicio.year, data_fim.year + 1)
    despesas: list[dict] = []
    for i, id_dep in enumerate(ids, start=1):
        for ano in anos:
            lote = extrair_paginado(sessao, f"deputados/{id_dep}/despesas", {"ano": ano, "ordem": "ASC", "ordenarPor": "ano"})
            for d in lote:
                d["idDeputado"] = id_dep  # a API não devolve o id do deputado no registro
            despesas.extend(lote)
        if i % 50 == 0 or i == len(ids):
            log.info("despesas: %d/%d deputados processados (%d registros)", i, len(ids), len(despesas))

    return {
        "partidos": partidos,
        "deputados": deputados,
        "proposicoes": proposicoes,
        "votacoes": votacoes,
        "despesas": despesas,
    }


# ---------------------------------------------------------------------------
# Padronização
# ---------------------------------------------------------------------------
def limpar_texto(serie: pd.Series) -> pd.Series:
    """strip + colapsa espaços/quebras de linha + texto vazio vira nulo."""
    return serie.astype("string").str.replace(r"\s+", " ", regex=True).str.strip().replace("", pd.NA)


def padronizar(df: pd.DataFrame, colunas: dict[str, str]) -> pd.DataFrame:
    """Seleciona e renomeia colunas (API -> banco), na ordem do dicionário."""
    return df[list(colunas)].rename(columns=colunas).copy()


def deduplicar(df: pd.DataFrame, chave: str, nome: str) -> pd.DataFrame:
    antes = len(df)
    df = df.drop_duplicates(subset=chave, keep="last").reset_index(drop=True)
    if antes - len(df):
        log.info("%s: %d duplicado(s) removido(s) pela chave %s", nome, antes - len(df), chave)
    return df


def validar(df: pd.DataFrame, pk: str, obrigatorias: list[str], nome: str) -> None:
    if not df[pk].is_unique:
        raise ValueError(f"{nome}: chave {pk} repetida")
    for col in [pk, *obrigatorias]:
        nulos = int(df[col].isna().sum())
        if nulos:
            raise ValueError(f"{nome}: {nulos} nulo(s) na coluna obrigatória {col}")
    log.info("%s: %d linhas válidas", nome, len(df))


def padronizar_partidos(raw: list[dict], atualizado_em: pd.Timestamp) -> pd.DataFrame:
    df = padronizar(pd.DataFrame(raw), {"id": "id_partido", "sigla": "sigla", "nome": "nome"})
    df["id_partido"] = df["id_partido"].astype("Int64")
    df["sigla"] = limpar_texto(df["sigla"]).str.upper()
    df["nome"] = limpar_texto(df["nome"])
    df["atualizado_em"] = atualizado_em
    df = deduplicar(df, "id_partido", "dim_partidos")
    validar(df, "id_partido", ["sigla", "nome"], "dim_partidos")
    return df


def padronizar_deputados(raw: list[dict], atualizado_em: pd.Timestamp) -> pd.DataFrame:
    df = padronizar(pd.DataFrame(raw), {
        "id": "id_deputado",
        "nome": "nome",
        "siglaPartido": "sigla_partido",
        "siglaUf": "sigla_uf",
        "urlFoto": "url_foto",
        "email": "email",
    })
    df["id_deputado"] = df["id_deputado"].astype("Int64")
    for col in ["nome", "url_foto"]:
        df[col] = limpar_texto(df[col])
    for col in ["sigla_partido", "sigla_uf"]:
        df[col] = limpar_texto(df[col]).str.upper()
    df["email"] = limpar_texto(df["email"]).str.lower()
    df["atualizado_em"] = atualizado_em
    df = deduplicar(df, "id_deputado", "dim_deputados")
    validar(df, "id_deputado", ["nome"], "dim_deputados")
    return df


def padronizar_proposicoes(raw: list[dict]) -> pd.DataFrame:
    df = padronizar(pd.DataFrame(raw), {
        "id": "id_proposicao",
        "siglaTipo": "sigla_tipo",
        "numero": "numero",
        "ano": "ano",
        "ementa": "ementa",
        "dataApresentacao": "data_apresentacao",
        "uri": "uri",
    })
    for col in ["id_proposicao", "numero", "ano"]:
        df[col] = df[col].astype("Int64")
    df["sigla_tipo"] = limpar_texto(df["sigla_tipo"]).str.upper()
    df["ementa"] = limpar_texto(df["ementa"])
    df["uri"] = limpar_texto(df["uri"])
    df["data_apresentacao"] = pd.to_datetime(df["data_apresentacao"], errors="coerce")
    df = deduplicar(df, "id_proposicao", "fato_proposicoes")
    validar(df, "id_proposicao", ["sigla_tipo", "numero", "ano", "data_apresentacao"], "fato_proposicoes")
    sem_ementa = int(df["ementa"].isna().sum())
    if sem_ementa:
        log.warning("fato_proposicoes: %d proposição(ões) sem ementa", sem_ementa)
    return df


def padronizar_votacoes(raw: list[dict]) -> pd.DataFrame:
    vot = pd.DataFrame(raw)
    vot["id_proposicao"] = (
        vot["uriProposicaoObjeto"].astype("string").str.extract(r"/proposicoes/(\d+)$", expand=False).astype("Int64")
    )
    df = padronizar(vot, {
        "id": "id_votacao",
        "id_proposicao": "id_proposicao",
        "data": "data_votacao",
        "descricao": "descricao",
        "aprovacao": "aprovacao",
    })
    df["id_votacao"] = limpar_texto(df["id_votacao"])
    df["data_votacao"] = pd.to_datetime(df["data_votacao"], errors="coerce").dt.date
    df["descricao"] = limpar_texto(df["descricao"])
    df["aprovacao"] = df["aprovacao"].map({1.0: True, 0.0: False}).astype("boolean")
    df = deduplicar(df, "id_votacao", "fato_votacoes")
    validar(df, "id_votacao", ["data_votacao"], "fato_votacoes")
    return df


# codDocumento se repete na API (telefonia vem "0", passagens SIGEPA repetem o GUID),
# por isso a chave é um hash determinístico do lançamento inteiro.
CAMPOS_HASH_DESPESA = [
    "idDeputado", "ano", "mes", "tipoDespesa", "codDocumento", "numDocumento",
    "dataDocumento", "valorDocumento", "valorLiquido", "valorGlosa",
    "cnpjCpfFornecedor", "numRessarcimento", "codLote", "parcela",
]


def gerar_id_despesa(linha: pd.Series) -> str:
    chave = "|".join("" if pd.isna(linha[c]) else str(linha[c]) for c in CAMPOS_HASH_DESPESA)
    return hashlib.md5(chave.encode("utf-8")).hexdigest()


def padronizar_despesas(raw: list[dict]) -> pd.DataFrame:
    colunas = {
        "id_despesa": "id_despesa",
        "codDocumento": "cod_documento",
        "idDeputado": "id_deputado",
        "ano": "ano",
        "mes": "mes",
        "tipoDespesa": "tipo_despesa",
        "valorDocumento": "valor_documento",
        "valorGlosa": "valor_glosa",
        "valorLiquido": "valor_liquido",
        "dataDocumento": "data_documento",
        "nomeFornecedor": "nome_fornecedor",
        "cnpjCpfFornecedor": "cnpj_cpf_fornecedor",
        "urlDocumento": "url_documento",
    }
    desp = pd.DataFrame(raw)
    if desp.empty:
        return pd.DataFrame(columns=list(colunas.values()))

    desp["id_despesa"] = desp.apply(gerar_id_despesa, axis=1)
    df = padronizar(desp, colunas)
    for col in ["id_deputado", "ano", "mes"]:
        df[col] = df[col].astype("Int64")
    for col in ["valor_documento", "valor_glosa", "valor_liquido"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)
    df["valor_glosa"] = df["valor_glosa"].fillna(0.0)
    df["data_documento"] = pd.to_datetime(df["data_documento"], errors="coerce").dt.date
    df["cod_documento"] = limpar_texto(df["cod_documento"])
    df["tipo_despesa"] = limpar_texto(df["tipo_despesa"]).str.upper().str.rstrip(".")
    df["nome_fornecedor"] = limpar_texto(df["nome_fornecedor"])
    df["cnpj_cpf_fornecedor"] = limpar_texto(df["cnpj_cpf_fornecedor"]).str.replace(r"\D", "", regex=True).replace("", pd.NA)
    df["url_documento"] = limpar_texto(df["url_documento"])
    df = deduplicar(df, "id_despesa", "fato_despesas")
    validar(df, "id_despesa", ["id_deputado", "ano", "mes", "tipo_despesa", "valor_liquido"], "fato_despesas")
    return df


def padronizar_tudo(brutos: dict[str, list[dict]]) -> dict[str, pd.DataFrame]:
    atualizado_em = pd.Timestamp(datetime.now()).floor("s")
    silver = {
        "dim_partidos": padronizar_partidos(brutos["partidos"], atualizado_em),
        "dim_deputados": padronizar_deputados(brutos["deputados"], atualizado_em),
        "fato_proposicoes": padronizar_proposicoes(brutos["proposicoes"]),
        "fato_votacoes": padronizar_votacoes(brutos["votacoes"]),
        "fato_despesas": padronizar_despesas(brutos["despesas"]),
    }

    # Integridade referencial (só avisa; a decisão de bloquear fica para a carga)
    sem_partido = set(silver["dim_deputados"]["sigla_partido"].dropna()) - set(silver["dim_partidos"]["sigla"])
    if sem_partido:
        log.warning("dim_deputados: siglas de partido sem correspondência: %s", sorted(sem_partido))
    orfas = int((~silver["fato_despesas"]["id_deputado"].isin(silver["dim_deputados"]["id_deputado"])).sum())
    if orfas:
        log.warning("fato_despesas: %d despesa(s) sem deputado na dimensão", orfas)
    return silver


# ---------------------------------------------------------------------------
# Persistência local (Bronze / Silver)
# ---------------------------------------------------------------------------
def salvar_bronze(brutos: dict[str, list[dict]]) -> None:
    PASTA_RAW.mkdir(parents=True, exist_ok=True)
    for nome, registros in brutos.items():
        caminho = PASTA_RAW / f"{nome}.json"
        caminho.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")
        log.info("Bronze salvo: %s (%d registros)", caminho.relative_to(RAIZ), len(registros))


def salvar_silver(silver: dict[str, pd.DataFrame]) -> None:
    PASTA_SILVER.mkdir(parents=True, exist_ok=True)
    for nome, df in silver.items():
        caminho = PASTA_SILVER / f"{nome}.json"
        df.to_json(caminho, orient="records", date_format="iso", force_ascii=False, indent=0)
        log.info("Silver salvo: %s (%d linhas)", caminho.relative_to(RAIZ), len(df))


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="ETL Etapa 1: extração e padronização da API da Câmara.")
    parser.add_argument("--dias", type=int, default=30, help="tamanho da janela em dias até hoje (padrão: 30)")
    parser.add_argument("--amostra-deputados", type=int, default=None,
                        help="limita as despesas a N deputados (padrão: todos)")
    parser.add_argument("--verbose", action="store_true", help="mostra o log de cada página")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=args.dias)
    log.info("Janela: %s -> %s | amostra de deputados: %s", data_inicio, data_fim, args.amostra_deputados or "todos")

    inicio = time.time()
    brutos = extrair_tudo(data_inicio, data_fim, args.amostra_deputados)
    salvar_bronze(brutos)

    silver = padronizar_tudo(brutos)
    salvar_silver(silver)

    resumo = ", ".join(f"{nome}={len(df)}" for nome, df in silver.items())
    log.info("Concluído em %.1fs | %s", time.time() - inicio, resumo)


if __name__ == "__main__":
    main()
