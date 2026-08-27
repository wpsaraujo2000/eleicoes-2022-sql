"""Configurações centrais do projeto."""

AWS_REGION = "us-east-2"
S3_BUCKET = "eleicoes-sql-2022"

# Camada RAW / fontes atuais
S3_MUNICIPIO_TSE_IBGE = "raw/municipios/municipio_tse_ibge.csv"
S3_BASE_MUNICIPIOS_RP = "raw/municipios/base_municipios_com_rp.csv"

# Destinos futuros
S3_SILVER_DIM_MUNICIPIO = "silver/dim_municipio/"
ATHENA_RESULTS = "athena-results/"
