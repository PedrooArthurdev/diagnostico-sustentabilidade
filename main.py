"""
main.py - Entry point do sistema de diagnóstico de sustentabilidade municipal.

Uso:
    python main.py                          # processa todos do CSV padrão
    python main.py --municipio "Belém"      # processa apenas um município
    python main.py --no-pdf                 # pula geração de PDF
    python main.py --dashboard              # exibe apenas o ranking CLI
"""

from __future__ import annotations

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import sys
from pathlib import Path

from src.engine import SustainabilityEngine
from src.report import gerar_relatorio_pdf
from src.dashboard import exibir_ranking

DATA_DIR   = Path("data")
OUTPUT_DIR = Path("output")
TMP_DIR    = Path("output/tmp")
SCHEMA     = DATA_DIR / "indicadores.json"
CSV_PADRAO = DATA_DIR / "municipios_sample.csv"


def main() -> None:
    args = _parse_args()

    engine = SustainabilityEngine(SCHEMA)
    resultados = engine.process_csv(args.csv)

    # Filtra por município, se solicitado
    if args.municipio:
        resultados = [
            r for r in resultados
            if r.municipio.lower() == args.municipio.lower()
        ]
        if not resultados:
            print(f"Município '{args.municipio}' não encontrado no CSV.")
            sys.exit(1)

    # Dashboard CLI
    exibir_ranking(resultados)

    if args.dashboard:
        return

    # Geração de PDFs
    if not args.no_pdf:
        print(f"Gerando {len(resultados)} relatório(s) PDF...\n")
        for res in resultados:
            pdf_path = gerar_relatorio_pdf(res, OUTPUT_DIR, TMP_DIR)
            print(f"  ✓ {res.municipio:<20} → {pdf_path}")
        print()
        print(f"PDFs salvos em: {OUTPUT_DIR.resolve()}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnóstico de Sustentabilidade Municipal — MVP"
    )
    parser.add_argument(
        "--csv",
        default=str(CSV_PADRAO),
        help=f"Caminho para o CSV de respostas (padrão: {CSV_PADRAO})",
    )
    parser.add_argument(
        "--municipio",
        default=None,
        help="Processa apenas o município especificado",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Pula a geração de arquivos PDF",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Exibe apenas o ranking CLI, sem gerar PDFs",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
