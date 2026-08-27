"""
FASE 1 — construção da dimensão municipal.

Objetivos:
- carregar a correspondência TSE ↔ IBGE;
- carregar atributos da malha municipal de 2024;
- padronizar códigos;
- corrigir divergências conhecidas;
- remover registros que não são municípios;
- criar o merge TSE ↔ IBGE ↔ geografia;
- validar o resultado.

Nesta etapa ainda NÃO gravamos dados no S3.
"""

from io import StringIO

import boto3
import pandas as pd
import pyogrio

from src.config.settings import (
    AWS_REGION,
    S3_BUCKET,
    S3_MUNICIPIO_TSE_IBGE,
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

SHAPEFILE_PATH = (
    "/vsis3/eleicoes-sql-2022/"
    "raw/geoespacial/BR_Municipios_2024/"
    "BR_Municipios_2024.shp"
)

# Registros da malha que não são municípios
CODIGOS_NAO_MUNICIPAIS = [
    "4300001",  # Área Operacional Lagoa Mirim
    "4300002",  # Área Operacional Lagoa dos Patos
]

# Correções conhecidas
CORRECOES_IBGE = {
    # Boa Esperança do Norte - MT
    "5300109": "5101837",
}


# ============================================================
# 1. TABELA TSE ↔ IBGE
# ============================================================

def carregar_municipios_tse() -> pd.DataFrame:
    """Carrega a tabela TSE ↔ IBGE diretamente do S3."""

    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
    )

    resposta = s3.get_object(
        Bucket=S3_BUCKET,
        Key=S3_MUNICIPIO_TSE_IBGE,
    )

    texto = resposta["Body"].read().decode("latin1")

    df = pd.read_csv(
        StringIO(texto),
        sep=";",
        dtype=str,
    )

    return df


def tratar_municipios_tse(
    df: pd.DataFrame
) -> pd.DataFrame:
    """Padroniza e corrige a tabela TSE ↔ IBGE."""

    colunas = [
        "CD_MUNICIPIO_TSE",
        "NM_MUNICIPIO_TSE",
        "CD_MUNICIPIO_IBGE",
        "NM_MUNICIPIO_IBGE",
        "SG_UF",
    ]

    df = df[colunas].copy()

    for coluna in colunas:
        df[coluna] = (
            df[coluna]
            .astype("string")
            .str.strip()
        )

    df["CD_MUNICIPIO_IBGE"] = (
        df["CD_MUNICIPIO_IBGE"]
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(7)
        .replace(CORRECOES_IBGE)
    )

    return df


# ============================================================
# 2. MALHA MUNICIPAL
# ============================================================

def carregar_malha_municipal() -> pd.DataFrame:
    """Carrega somente atributos da malha, sem geometria."""

    df = pyogrio.read_dataframe(
        SHAPEFILE_PATH,
        columns=[
            "CD_MUN",
            "NM_MUN",
            "SIGLA_UF",
            "AREA_KM2",
            "CD_RGI",
            "NM_RGI",
            "CD_RGINT",
            "NM_RGINT",
            "CD_REGIA",
            "NM_REGIA",
        ],
        read_geometry=False,
    )

    return df


def tratar_malha_municipal(
    df: pd.DataFrame
) -> pd.DataFrame:
    """Padroniza a malha e remove registros não municipais."""

    df = df.copy()

    df["CD_MUN"] = (
        df["CD_MUN"]
        .astype("string")
        .str.strip()
        .str.zfill(7)
    )

    df = df[
        ~df["CD_MUN"].isin(
            CODIGOS_NAO_MUNICIPAIS
        )
    ].copy()

    return df


# ============================================================
# 3. CRIAÇÃO DA DIMENSÃO
# ============================================================

def criar_dim_municipio(
    tse: pd.DataFrame,
    geo: pd.DataFrame
) -> pd.DataFrame:
    """
    Relaciona TSE e geografia usando o código IBGE.
    """

    dim = tse.merge(
        geo,
        left_on="CD_MUNICIPIO_IBGE",
        right_on="CD_MUN",
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    # Verificar falhas no relacionamento
    sem_geo = dim[
        dim["_merge"] != "both"
    ]

    if not sem_geo.empty:
        print("\nMunicípios sem geografia:")
        print(
            sem_geo[
                [
                    "CD_MUNICIPIO_TSE",
                    "CD_MUNICIPIO_IBGE",
                    "NM_MUNICIPIO_TSE",
                ]
            ].to_string(index=False)
        )

        raise ValueError(
            "Existem municípios sem correspondência geográfica."
        )

    # Nome municipal oficial da dimensão
    dim["NM_MUNICIPIO"] = dim["NM_MUN"]

    # Mantemos a UF da malha após validação
    dim["SG_UF"] = dim["SIGLA_UF"]

    # Renomear regiões modernas
    dim = dim.rename(
        columns={
            "CD_RGI": "CD_REGIAO_IMEDIATA",
            "NM_RGI": "NM_REGIAO_IMEDIATA",
            "CD_RGINT": "CD_REGIAO_INTERMEDIARIA",
            "NM_RGINT": "NM_REGIAO_INTERMEDIARIA",
            "CD_REGIA": "CD_REGIAO",
            "NM_REGIA": "NM_REGIAO",
        }
    )

    colunas_finais = [
        "CD_MUNICIPIO_TSE",
        "CD_MUNICIPIO_IBGE",
        "NM_MUNICIPIO",
        "SG_UF",
        "AREA_KM2",
        "CD_REGIAO_IMEDIATA",
        "NM_REGIAO_IMEDIATA",
        "CD_REGIAO_INTERMEDIARIA",
        "NM_REGIAO_INTERMEDIARIA",
        "CD_REGIAO",
        "NM_REGIAO",
    ]

    dim = (
        dim[colunas_finais]
        .sort_values(
            [
                "SG_UF",
                "CD_MUNICIPIO_IBGE",
            ]
        )
        .reset_index(drop=True)
    )

    return dim


# ============================================================
# 4. VALIDAÇÃO
# ============================================================

def validar_dim_municipio(
    dim: pd.DataFrame
) -> None:
    """Executa verificações básicas da dimensão."""

    print("\n" + "-" * 60)
    print("VALIDAÇÃO FINAL")
    print("-" * 60)

    print("Registros:", len(dim))

    print(
        "Códigos TSE únicos:",
        dim["CD_MUNICIPIO_TSE"].nunique()
    )

    print(
        "Códigos IBGE únicos:",
        dim["CD_MUNICIPIO_IBGE"].nunique()
    )

    print(
        "UFs:",
        dim["SG_UF"].nunique()
    )

    print(
        "Municípios sem nome:",
        dim["NM_MUNICIPIO"].isna().sum()
    )

    print(
        "Municípios sem área:",
        dim["AREA_KM2"].isna().sum()
    )

    if len(dim) != 5571:
        raise ValueError(
            f"Quantidade inesperada: {len(dim)}"
        )

    if dim["CD_MUNICIPIO_TSE"].nunique() != 5571:
        raise ValueError(
            "CD_MUNICIPIO_TSE não é único."
        )

    if dim["CD_MUNICIPIO_IBGE"].nunique() != 5571:
        raise ValueError(
            "CD_MUNICIPIO_IBGE não é único."
        )

    if dim["SG_UF"].nunique() != 27:
        raise ValueError(
            "Quantidade de UFs diferente de 27."
        )


# ============================================================
# 5. EXECUÇÃO
# ============================================================

def main() -> None:

    print("=" * 60)
    print("FASE 1 - DIMENSÃO MUNICÍPIO")
    print("=" * 60)

    print("\n[1/4] Carregando tabela TSE ↔ IBGE...")

    tse = carregar_municipios_tse()

    print(
        "Registros antes do tratamento:",
        len(tse)
    )

    tse = tratar_municipios_tse(tse)

    print(
        "Registros após o tratamento:",
        len(tse)
    )

    print("\n[2/4] Carregando malha municipal...")

    geo = carregar_malha_municipal()

    print(
        "Registros antes do tratamento:",
        len(geo)
    )

    geo = tratar_malha_municipal(geo)

    print(
        "Registros após o tratamento:",
        len(geo)
    )

    print("\n[3/4] Criando dimensão municipal...")

    dim = criar_dim_municipio(
        tse=tse,
        geo=geo,
    )

    print(
        "Registros após o merge:",
        len(dim)
    )

    print("\n[4/4] Validando dimensão...")

    validar_dim_municipio(dim)

    print("\n" + "-" * 60)
    print("AMOSTRA")
    print("-" * 60)

    print(
        dim.head(10).to_string(
            index=False
        )
    )

    print("\nProcesso concluído com sucesso.")
    print("Nenhum arquivo foi gravado no S3.")


if __name__ == "__main__":
    main()
