# Eleições 2022 SQL

Projeto para processamento, análise e visualização dos dados das Eleições de 2022 utilizando Python, SQL e serviços AWS.

## Objetivo

O principal objetivo do projeto é otimizar o processamento das bases eleitorais, evitando o carregamento de grandes arquivos diretamente em Python ou na aplicação de visualização.

A arquitetura será organizada em três camadas:

```text
RAW → SILVER → GOLD
```

### RAW

Armazena os dados originais, sem alterações.

Exemplos:

* votação;
* candidatos;
* despesas;
* bens;
* eleitorado;
* municípios;
* indicadores.

### SILVER

Armazena dados tratados, reduzidos e organizados para consulta.

Nesta camada serão realizadas operações como:

* limpeza;
* padronização;
* conversão de tipos;
* relacionamentos entre bases;
* redução de colunas;
* agregações intermediárias;
* conversão para formatos mais eficientes, como Parquet.

### GOLD

Armazena os dados já preparados para análises, mapas, gráficos e aplicações.

A aplicação final não deverá carregar as bases eleitorais completas.

O fluxo esperado será:

```text
S3
 ↓
Athena / SQL
 ↓
dados agregados
 ↓
Python / API
 ↓
App ou site
```

## Organização do projeto

```text
eleicoes-2022-sql/
│
├── notebooks/
│   └── legacy/
│
├── src/
│
├── sql/
│
├── tests/
│
└── README.md
```

### `notebooks/legacy`

Contém os notebooks utilizados antes da migração.

Eles serão preservados como referência e para validação dos novos processos.

### `src`

Conterá os novos scripts Python.

### `sql`

Conterá os scripts SQL utilizados principalmente no Amazon Athena.

### `tests`

Conterá arquivos e rotinas utilizados para comparar os resultados antigos com os novos.

## Regra principal

Sempre priorizar:

1. menor leitura de dados;
2. menor uso de memória;
3. processamento com SQL quando adequado;
4. armazenamento otimizado;
5. evitar duplicação de informações;
6. enviar para o futuro app somente os dados necessários para visualização.

## Dados

Os arquivos de dados não serão armazenados neste repositório.

As bases serão mantidas no Amazon S3.
