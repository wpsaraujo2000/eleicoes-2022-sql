# eleicoes-2022-sql

Pipeline otimizado para processamento e disponibilização de dados das Eleições 2022.

## Arquitetura

RAW → SILVER → GOLD → análise/app

- **RAW:** arquivos originais no S3.
- **SILVER:** dados limpos, tipados, reduzidos e preferencialmente em Parquet.
- **GOLD:** agregações finais para análises, mapas e aplicações.
- **Python:** orquestração, geoprocessamento pontual e análises estatísticas.
- **Athena/SQL:** filtros, joins e agregações pesadas.

## Fase atual

### FASE 0
Estrutura inicial do repositório.

### FASE 1
Construção de `dim_municipio`.

Antes de reconstruir a geografia, auditamos as duas fontes existentes no S3:

- `municipio_tse_ibge.csv`
- `base_municipios_com_rp.csv`

Execute:

```bash
python -m src.utils.inspect_s3_csv
```

O script lê apenas os primeiros 128 KB de cada arquivo.

Depois da auditoria será implementado:

```text
src/dimensions/build_dim_municipio.py
```

com destino planejado:

```text
s3://eleicoes-sql-2022/silver/dim_municipio/
```

## Regra do projeto

A aplicação final nunca deverá carregar as bases eleitorais completas.
Ela consumirá somente dados GOLD já agregados para mapas, gráficos e consultas.
