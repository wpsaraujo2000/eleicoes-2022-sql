"""
Auditoria leve de arquivos CSV armazenados no S3.

Objetivo:
- não baixar o arquivo inteiro;
- ler somente os primeiros bytes;
- identificar encoding, delimitador, cabeçalho e uma pequena amostra.

Uso:
    python -m src.utils.inspect_s3_csv
"""

from __future__ import annotations

import csv
import io
from typing import Iterable

import boto3

from config.settings import (
    AWS_REGION,
    S3_BUCKET,
    S3_MUNICIPIO_TSE_IBGE,
    S3_BASE_MUNICIPIOS_RP,
)


BYTES_TO_READ = 128 * 1024  # 128 KB


def decode_bytes(raw: bytes) -> tuple[str, str]:
    """Tenta os encodings mais comuns das bases eleitorais."""
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        "unknown", raw, 0, 1, "Não foi possível identificar o encoding."
    )


def detect_delimiter(sample: str) -> str:
    """Tenta detectar o separador do CSV."""
    try:
        dialect = csv.Sniffer().sniff(sample[:8192], delimiters=",;|\t")
        return dialect.delimiter
    except csv.Error:
        # TSE costuma usar ';', mas não assumimos silenciosamente.
        counts = {sep: sample.count(sep) for sep in (";", ",", "|", "\t")}
        return max(counts, key=counts.get)


def read_s3_sample(s3, bucket: str, key: str) -> bytes:
    """Lê apenas uma pequena faixa do objeto S3."""
    response = s3.get_object(
        Bucket=bucket,
        Key=key,
        Range=f"bytes=0-{BYTES_TO_READ - 1}",
    )
    return response["Body"].read()


def inspect_csv(s3, key: str) -> None:
    raw = read_s3_sample(s3, S3_BUCKET, key)
    text, encoding = decode_bytes(raw)
    delimiter = detect_delimiter(text)

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = []

    for row in reader:
        if row:
            rows.append(row)
        if len(rows) >= 4:
            break

    print("\n" + "=" * 100)
    print(f"ARQUIVO: s3://{S3_BUCKET}/{key}")
    print(f"Encoding provável: {encoding}")
    print(f"Separador provável: {repr(delimiter)}")

    if not rows:
        print("Nenhuma linha válida encontrada na amostra.")
        return

    header = [col.strip() for col in rows[0]]
    print(f"Nº de colunas: {len(header)}")
    print("\nCOLUNAS:")
    for i, col in enumerate(header, start=1):
        print(f"{i:02d}. {col}")

    if len(rows) > 1:
        print("\nAMOSTRA (até 3 linhas):")
        for row in rows[1:]:
            print(row)


def main(keys: Iterable[str] | None = None) -> None:
    s3 = boto3.client("s3", region_name=AWS_REGION)

    targets = list(keys or [
        S3_MUNICIPIO_TSE_IBGE,
        S3_BASE_MUNICIPIOS_RP,
    ])

    print(f"Bucket: s3://{S3_BUCKET}")
    print(f"Região: {AWS_REGION}")
    print(f"Leitura máxima por arquivo: {BYTES_TO_READ / 1024:.0f} KB")

    for key in targets:
        inspect_csv(s3, key)


if __name__ == "__main__":
    main()
