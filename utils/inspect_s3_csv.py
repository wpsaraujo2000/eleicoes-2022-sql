import boto3

from src.config.settings import (
    AWS_REGION,
    S3_BUCKET,
    S3_MUNICIPIO_TSE_IBGE,
    S3_BASE_MUNICIPIOS_RP,
)


s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)


arquivos = [
    S3_MUNICIPIO_TSE_IBGE,
    S3_BASE_MUNICIPIOS_RP,
]


for arquivo in arquivos:

    print("\n" + "=" * 80)
    print(f"Arquivo: {arquivo}")

    resposta = s3.get_object(
        Bucket=S3_BUCKET,
        Key=arquivo,
        Range="bytes=0-65535"
    )

    conteudo = resposta["Body"].read()

    try:
        texto = conteudo.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        texto = conteudo.decode("latin1")
        encoding = "latin1"

    linhas = texto.splitlines()

    print(f"Encoding provável: {encoding}")

    if linhas:
        print("\nCabeçalho:")
        print(linhas[0])

        print("\nPrimeiras 3 linhas:")
        for linha in linhas[1:4]:
            print(linha)
