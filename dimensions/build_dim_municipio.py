"""
FASE 1 — construção da dimensão municipal.

Objetivos desta etapa:
- carregar a tabela de correspondência TSE ↔ IBGE;
- carregar atributos da malha municipal de 2024;
- padronizar códigos municipais;
- corrigir divergências conhecidas;
- remover registros que não representam municípios;
- relacionar TSE e IBGE;
- validar a correspondência entre as fontes.

IMPORTANTE
----------
A camada RAW nunca é alterada.

Nesta etapa ainda NÃO fazemos:
- gravação no S3;
- geração de Parquet;
- latitude/longitude;
- microrregião/mesorregião da classificação antiga.

Destino futuro:
    s3://eleicoes-sql-2022/silver/dim_municipio/
"""

from __future__ import annotations

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


# Códigos presentes na malha, mas que não representam municípios
CODIGOS_NAO_MUNICIPAIS = [
    "4300001",  # Área Operacional Lagoa Mirim
    "4300002",  # Área Operacional Lagoa dos Patos
]


# Correções conhecidas na tabela TSE ↔ IBGE
CORRECOES_CODIGO_IBGE = {
    # Boa Esperança do Norte - MT
    "5300109": "5101837",
}


# ============================================================
# 1. CARREGAMENTO TSE ↔ IBGE
# ============================================================

def carregar_municipios_tse() -> pd.DataFrame:
    """
    Lê a tabela de correspondência TSE ↔ IBGE diretamente do S3.

    Retorna
    -------
    pd.DataFrame
        Base original da correspondência municipal.
    """

    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
    )

    resposta = s3.get_object(
        Bucket=S3_BUCKET,
        Key=S3_MUNICIPIO_TSE_IBGE,
    )

    # O arquivo foi identificado anteriormente como Latin-1.
    texto = resposta["Body"].read().decode("latin1")

    df = pd.read_csv(
        StringIO(texto),
        sep=";",
        dtype=str,
    )

    return df


# ============================================================
# 2. TRATAMENTO TSE ↔ IBGE
# ============================================================

def tratar_municipios_tse(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Padroniza a tabela TSE ↔ IBGE.

    Operações:
    - mantém somente colunas necessárias;
    - remove espaços;
    - padroniza códigos;
    - corrige divergências conhecidas;
    - valida unicidade do código TSE.
    """

    colunas = [
        "CD_MUNICIPIO_TSE",
        "NM_MUNICIPIO_TSE",
        "CD_MUNICIPIO_IBGE",
        "NM_MUNICIPIO_IBGE",
        "SG_UF",
    ]

    faltantes = [
        coluna
        for coluna in colunas
        if coluna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Colunas ausentes na tabela TSE ↔ IBGE: {faltantes}"
        )

    df = df[colunas].copy()

    # --------------------------------------------------------
    # Limpeza textual
    # --------------------------------------------------------

    for coluna in [
        "CD_MUNICIPIO_TSE",
        "CD_MUNICIPIO_IBGE",
        "NM_MUNICIPIO_TSE",
        "NM_MUNICIPIO_IBGE",
        "SG_UF",
    ]:
        df[coluna] = (
            df[coluna]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Código TSE
    # --------------------------------------------------------

    df["CD_MUNICIPIO_TSE"] = (
        df["CD_MUNICIPIO_TSE"]
        .str.replace(r"\.0$", "", regex=True)
    )

    # --------------------------------------------------------
    # Código IBGE
    # --------------------------------------------------------

    df["CD_MUNICIPIO_IBGE"] = (
        df["CD_MUNICIPIO_IBGE"]
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(7)
    )

    # --------------------------------------------------------
    # Correções conhecidas
    # --------------------------------------------------------

    df["CD_MUNICIPIO_IBGE"] = (
        df["CD_MUNICIPIO_IBGE"]
        .replace(CORRECOES_CODIGO_IBGE)
    )

    # --------------------------------------------------------
    # Validação
    # --------------------------------------------------------

    duplicados_tse = (
        df["CD_MUNICIPIO_TSE"]
        .duplicated()
        .sum()
    )

    if duplicados_tse > 0:
        raise ValueError(
            f"Foram encontrados {duplicados_tse} "
            "códigos TSE duplicados."
        )

    duplicados_ibge = (
        df["CD_MUNICIPIO_IBGE"]
        .duplicated()
        .sum()
    )

    if duplicados_ibge > 0:
        raise ValueError(
            f"Foram encontrados {duplicados_ibge} "
            "códigos IBGE duplicados após tratamento."
        )

    return df


# ============================================================
# 3. CARREGAMENTO DA MALHA MUNICIPAL
# ============================================================

def carregar_malha_municipal() -> pd.DataFrame:
    """
    Lê somente os atributos necessários da malha municipal.

    A geometria não é carregada nesta etapa para reduzir
    consumo de memória e transferência de dados.
    """

    colunas = [
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
    ]

    df = pyogrio.read_dataframe(
        SHAPEFILE_PATH,
        columns=colunas,
        read_geometry=False,
    )

    return df


# ============================================================
# 4. TRATAMENTO DA MALHA
# ============================================================

def tratar_malha_municipal(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Padroniza a malha municipal.

    Operações:
    - padroniza código IBGE;
    - remove áreas não municipais;
    - padroniza textos;
    - valida unicidade municipal.
    """

    df = df.copy()

    df["CD_MUN"] = (
        df["CD_MUN"]
        .astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(7)
    )

    # --------------------------------------------------------
    # Remover áreas que não representam municípios
    # --------------------------------------------------------

    df = df[
        ~df["CD_MUN"].isin(
            CODIGOS_NAO_MUNICIPAIS
        )
    ].copy()

    # --------------------------------------------------------
    # Padronização textual
    # --------------------------------------------------------

    colunas_texto = [
        "NM_MUN",
        "SIGLA_UF",
        "CD_RGI",
        "NM_RGI",
        "CD_RGINT",
        "NM_RGINT",
        "CD_REGIA",
        "NM_REGIA",
    ]

    for coluna in colunas_texto:
        if coluna in df.columns:
            df[coluna] = (
                df[coluna]
                .astype("string")
                .str.strip()
            )

    # --------------------------------------------------------
    # Área municipal
    # --------------------------------------------------------

    df["AREA_KM2"] = pd.to_numeric(
        df["AREA_KM2"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Validação
    # --------------------------------------------------------

    duplicados = (
        df["CD_MUN"]
        .duplicated()
        .sum()
    )

    if duplicados > 0:
        raise ValueError(
            f"Foram encontrados {duplicados} "
            "códigos municipais duplicados na malha."
        )

    return df


# ============================================================
# 5. CRIAÇÃO DA DIMENSÃO
# ============================================================

def criar_dim_municipio(
    tse: pd.DataFrame,
    geo: pd.DataFrame,
) -> pd.DataFrame:
    """
    Junta a tabela TSE ↔ IBGE com a malha municipal.

    O relacionamento é feito por:

        CD_MUNICIPIO_IBGE = CD_MUN

    Como ambas as bases devem possuir uma linha por município,
    o merge é validado como one_to_one.
    """

    dim = tse.merge(
        geo,
        left_on="CD_MUNICIPIO_IBGE",
        right_on="CD_MUN",
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    # --------------------------------------------------------
    # Validar municípios sem correspondência
    # --------------------------------------------------------

    sem_correspondencia = dim[
        dim["_merge"] != "both"
    ]

    if not sem_correspondencia.empty:
        colunas_erro = [
            "CD_MUNICIPIO_TSE",
            "CD_MUNICIPIO_IBGE",
            "NM_MUNICIPIO_TSE",
            "_merge",
        ]

        raise ValueError(
            "Existem municípios sem correspondência geográfica:\n"
            + sem_correspondencia[
                colunas_erro
            ].to_string(index=False)
        )

    dim = dim.drop(
        columns=[
            "_merge",
            "CD_MUN",
        ]
    )

    # --------------------------------------------------------
    # Nome e UF oficiais da dimensão
    # --------------------------------------------------------

    dim["NM_MUNICIPIO"] = dim["NM_MUN"]

    dim["SG_UF"] = (
        dim["SIGLA_UF"]
        .fillna(dim["SG_UF"])
    )

    # --------------------------------------------------------
    # Renomear atributos geográficos modernos
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Seleção e ordenação
    # --------------------------------------------------------

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

    dim = dim[
        colunas_finais
    ].copy()

    dim = dim.sort_values(
        [
            "SG_UF",
            "CD_MUNICIPIO_IBGE",
        ]
    ).reset_index(drop=True)

    return dim


# ============================================================
# 6. VALIDAÇÃO FINAL
# ============================================================

def validar_dim_municipio(
    dim: pd.DataFrame,
) -> None:
    """
    Executa verificações básicas de integridade da dimensão.
    """

    print("\n" + "-" * 60)
    print("VALIDAÇÃO FINAL")
    print("-" * 60)

    print(
        "Registros:",
        len(dim)
    )

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

    print(
        "Municípios sem região imediata:",
        dim["CD_REGIAO_IMEDIATA"].isna().sum()
    )

    print(
        "Municípios sem região intermediária:",
        dim["CD_REGIAO_INTERMEDIARIA"].isna().sum()
    )

    # --------------------------------------------------------
    # Regras críticas
    # --------------------------------------------------------

    if len(dim) != 5571:
        raise ValueError(
            f"Quantidade inesperada de municípios: {len(dim)}"
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
            f"Quantidade inesperada de UFs: "
            f"{dim['SG_UF'].nunique()}"
        )


# ============================================================
# 7. EXECUÇÃO
# ============================================================

def main() -> None:

    print("=" * 60)
    print("FASE 1 - DIMENSÃO MUNICÍPIO")
    print("=" * 60)

    # --------------------------------------------------------
    # TSE
    # --------------------------------------------------------

    print(
        "\n[1/4] Carregando tabela TSE ↔ IBGE..."
    )

    tse = carregar_municipios_tse()

    print(
        "Registros antes do tratamento:",
        len(tse)
    )

    tse = tratar_municipios_tse(
        tse
    )

    print(
        "Registros após o tratamento:",
        len(tse)
    )

    # --------------------------------------------------------
    # MALHA
    # --------------------------------------------------------

    print(
        "\n[2/4] Carregando malha municipal..."
    )

    geo = carregar_malha_municipal()

    print(
        "Registros antes do tratamento:",
        len(geo)
    )

    geo = tratar_malha_municipal(
        geo
    )

    print(
        "Registros após o tratamento:",
        len(geo)
    )

    # --------------------------------------------------------
    # MERGE
    # --------------------------------------------------------

    print(
        "\n[3/4] Criando dimensão municipal..."
    )

    dim = criar_dim_municipio(
        tse=tse,
        geo=geo,
    )

    print(
        "Registros após o merge:",
        len(dim)
    )

    # --------------------------------------------------------
    # VALIDAÇÃO
    # --------------------------------------------------------

    print(
        "\n[4/4] Validando dimensão..."
    )

    validar_dim_municipio(
        dim
    )

    # --------------------------------------------------------
    # AMOSTRA
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("AMOSTRA")
    print("-" * 60)

    print(
        dim.head(10).to_string(
            index=False
        )
    )

    print("\nProcesso concluído com sucesso.")

    print(
        "\nOBSERVAÇÃO:"
        "\nA dimensão ainda não foi gravada no S3."
        "\nA gravação em Parquet será adicionada"
        "\nna próxima etapa."
    )


if __name__ == "__main__":
    main()
