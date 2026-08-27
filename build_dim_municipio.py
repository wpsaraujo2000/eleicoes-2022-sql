"""
FASE 1 — construção de dim_municipio.

ATENÇÃO:
Este arquivo começa propositalmente como um esqueleto.

Antes de decidir se faremos GeoPandas/geobr novamente, execute:
    python -m src.utils.inspect_s3_csv

Se `base_municipios_com_rp.csv` já possuir as colunas necessárias,
vamos reutilizá-lo e evitar recomputar spatial joins.

Saída pretendida:
    CD_MUNICIPIO_TSE
    CD_MUNICIPIO_IBGE
    NM_MUNICIPIO
    SG_UF
    code_micro
    name_micro
    code_meso
    name_meso
    latitude
    longitude

Destino:
    s3://eleicoes-sql-2022/silver/dim_municipio/
"""


REQUIRED_COLUMNS = [
    "CD_MUNICIPIO_TSE",
    "CD_MUNICIPIO_IBGE",
    "NM_MUNICIPIO",
    "SG_UF",
    "code_micro",
    "name_micro",
    "code_meso",
    "name_meso",
    "latitude",
    "longitude",
]


def main() -> None:
    raise SystemExit(
        "Primeiro execute `python -m src.utils.inspect_s3_csv` "
        "e valide as colunas das duas fontes municipais."
    )


if __name__ == "__main__":
    main()
