"""
dashboard.py - Dashboard CLI de ranking dos municípios processados.

Uso:
    python -m src.dashboard                  # processa CSV padrão
    python -m src.dashboard --csv data/outro.csv
    python -m src.dashboard --json           # exibe saída JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Força UTF-8 no terminal Windows para suportar caracteres especiais e emojis
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ajuste de path para execução direta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import SustainabilityEngine, ResultadoMunicipio

# Cores ANSI
R = "\033[0m"
BOLD = "\033[1m"
CORES_NIVEL: dict[str, str] = {
    "Crítico":     "\033[91m",   # vermelho
    "Insuficiente":"\033[93m",   # amarelo
    "Regular":     "\033[33m",   # laranja aproximado
    "Bom":         "\033[92m",   # verde
    "Excelente":   "\033[32m",   # verde escuro
}

MEDALHAS = ["🥇", "🥈", "🥉"]


def exibir_ranking(resultados: list[ResultadoMunicipio], formato_json: bool = False) -> None:
    """Imprime o ranking dos municípios no terminal."""
    ranking = sorted(resultados, key=lambda r: r.score_final, reverse=True)

    if formato_json:
        print(json.dumps([r.to_dict() for r in ranking], ensure_ascii=False, indent=2))
        return

    largura = 70
    print()
    print("=" * largura)
    print(f"{BOLD}{'RANKING DE SUSTENTABILIDADE MUNICIPAL':^{largura}}{R}")
    print(f"{'Diagnóstico Ambiental · Pará':^{largura}}")
    print("=" * largura)
    print(
        f"  {'#':<4} {'Município':<18} {'Score':>6}  {'Nível':<14} {'Pop.':>10}"
    )
    print("-" * largura)

    for i, res in enumerate(ranking):
        medalha = MEDALHAS[i] if i < 3 else f"{i+1:>2}."
        cor = CORES_NIVEL.get(res.nivel_geral, "")
        pop_fmt = f"{res.populacao:,}".replace(",", ".")
        print(
            f"  {medalha:<4} {res.municipio:<18} "
            f"{cor}{BOLD}{res.score_final:>5.1f}{R}  "
            f"{cor}{res.nivel_geral:<14}{R} {pop_fmt:>10}"
        )

    print("-" * largura)
    media = sum(r.score_final for r in ranking) / len(ranking)
    print(f"  {'Média geral:':<23} {BOLD}{media:>5.1f}{R}")
    print("=" * largura)
    print()

    # Destaque das categorias mais críticas no conjunto
    print(f"{BOLD}  Categorias com maior déficit (média dos municípios):{R}")
    cat_scores: dict[str, list[float]] = {}
    for res in ranking:
        for cat in res.categorias:
            cat_scores.setdefault(cat.nome, []).append(cat.score)

    medias_cat = {nome: sum(v) / len(v) for nome, v in cat_scores.items()}
    for nome, media_cat in sorted(medias_cat.items(), key=lambda x: x[1]):
        barra = _barra_progresso(media_cat)
        cor = _cor_score(media_cat)
        print(f"  {nome:<35} {cor}{barra} {media_cat:.1f}{R}")
    print()


def _barra_progresso(score: float, largura: int = 10) -> str:
    preenchido = int(round(score / 10 * largura))
    return "█" * preenchido + "░" * (largura - preenchido)


def _cor_score(score: float) -> str:
    if score < 2.5:
        return CORES_NIVEL["Crítico"]
    if score < 5.0:
        return CORES_NIVEL["Insuficiente"]
    if score < 7.0:
        return CORES_NIVEL["Regular"]
    if score < 8.5:
        return CORES_NIVEL["Bom"]
    return CORES_NIVEL["Excelente"]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dashboard CLI — Diagnóstico de Sustentabilidade Municipal"
    )
    parser.add_argument(
        "--csv",
        default="data/municipios_sample.csv",
        help="Caminho para o CSV exportado do Google Forms (padrão: data/municipios_sample.csv)",
    )
    parser.add_argument(
        "--schema",
        default="data/indicadores.json",
        help="Caminho para o schema de indicadores (padrão: data/indicadores.json)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="formato_json",
        help="Exibe saída em formato JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    schema_path = Path(args.schema)
    csv_path = Path(args.csv)

    if not schema_path.exists():
        print(f"Erro: schema não encontrado em '{schema_path}'")
        sys.exit(1)
    if not csv_path.exists():
        print(f"Erro: CSV não encontrado em '{csv_path}'")
        sys.exit(1)

    engine = SustainabilityEngine(schema_path)
    resultados = engine.process_csv(csv_path)
    exibir_ranking(resultados, formato_json=args.formato_json)


if __name__ == "__main__":
    main()
