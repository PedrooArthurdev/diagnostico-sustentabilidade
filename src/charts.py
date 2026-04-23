"""
charts.py - Geração do gráfico Radar (Teia de Aranha) com matplotlib.
Retorna o caminho para a imagem PNG gerada em /output/tmp/.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sem GUI, seguro para geração de arquivos
import matplotlib.pyplot as plt
import numpy as np


def gerar_radar_chart(
    categorias: list[str],
    scores: list[float],
    municipio: str,
    output_dir: str | Path = "output/tmp",
) -> Path:
    """
    Gera o gráfico Radar e salva como PNG.

    Args:
        categorias: lista de nomes das categorias (eixos).
        scores:     lista de scores (0–10) correspondentes.
        municipio:  nome do município (usado no título e no nome do arquivo).
        output_dir: diretório de saída para a imagem.

    Returns:
        Path para o arquivo PNG gerado.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    N = len(categorias)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]  # fecha o polígono

    scores_plot = list(scores) + [scores[0]]  # fecha

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

    # Grid e eixos
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(30)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], color="grey", fontsize=8)

    # Rótulos dos eixos — quebra linha longa para caber no gráfico
    labels = [_quebra_label(c) for c in categorias]
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9, fontweight="bold", color="#2c3e50")

    # Área preenchida
    ax.plot(angles, scores_plot, linewidth=2, linestyle="solid", color="#1565C0")
    ax.fill(angles, scores_plot, alpha=0.25, color="#1565C0")

    # Pontos
    ax.scatter(angles[:-1], scores, s=60, color="#0D47A1", zorder=5)

    # Título
    ax.set_title(
        f"Diagnóstico de Sustentabilidade\n{municipio}",
        size=13,
        fontweight="bold",
        color="#1a237e",
        pad=20,
    )

    # Faixas de referência
    _add_reference_zones(ax, angles)

    safe_name = municipio.lower().replace(" ", "_").replace("/", "-")
    output_path = output_dir / f"radar_{safe_name}.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path


def _add_reference_zones(ax: plt.Axes, angles: list[float]) -> None:
    """Adiciona faixas coloridas de referência no fundo do radar."""
    zonas = [
        (0, 2.5, "#D32F2F", 0.06),   # Crítico
        (2.5, 5.0, "#F57C00", 0.05),  # Insuficiente
        (5.0, 7.0, "#FBC02D", 0.04),  # Regular
        (7.0, 8.5, "#388E3C", 0.04),  # Bom
        (8.5, 10.0, "#1B5E20", 0.03), # Excelente
    ]
    for r_min, r_max, cor, alpha in zonas:
        theta = np.linspace(0, 2 * np.pi, 360)
        ax.fill_between(theta, r_min, r_max, color=cor, alpha=alpha, zorder=0)


def gerar_radar_plotly(
    categorias: list[str],
    scores: list[float],
    municipio: str,
):
    """
    Retorna um go.Figure do Plotly com o gráfico Radar interativo.
    Usado na interface Streamlit (não gera arquivo).
    """
    import plotly.graph_objects as go

    cats_fechadas = categorias + [categorias[0]]
    scores_fechados = scores + [scores[0]]

    fig = go.Figure()

    # Faixas de referência como shapes polares não são triviais no plotly,
    # então usamos traces preenchidos para simular as zonas
    zonas = [
        (10.0, "rgba(27,94,32,0.08)",   "Excelente"),
        (8.5,  "rgba(56,142,60,0.10)",  "Bom"),
        (7.0,  "rgba(251,192,45,0.12)", "Regular"),
        (5.0,  "rgba(245,124,0,0.12)",  "Insuficiente"),
        (2.5,  "rgba(211,47,47,0.14)",  "Crítico"),
    ]
    for valor, cor, nome in zonas:
        ring = [valor] * (len(categorias) + 1)
        fig.add_trace(go.Scatterpolar(
            r=ring,
            theta=cats_fechadas,
            fill="toself",
            fillcolor=cor,
            line=dict(color="rgba(0,0,0,0)", width=0),
            name=nome,
            hoverinfo="skip",
            showlegend=False,
        ))

    # Linha principal do município
    fig.add_trace(go.Scatterpolar(
        r=scores_fechados,
        theta=cats_fechadas,
        fill="toself",
        fillcolor="rgba(21,101,192,0.25)",
        line=dict(color="#1565C0", width=2.5),
        marker=dict(size=7, color="#0D47A1"),
        name=municipio,
        hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickvals=[2, 4, 6, 8, 10],
                tickfont=dict(size=10),
                gridcolor="#E0E0E0",
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color="#2c3e50"),
                gridcolor="#E0E0E0",
            ),
            bgcolor="white",
        ),
        showlegend=False,
        title=dict(
            text=f"<b>Diagnóstico de Sustentabilidade</b><br><sub>{municipio}</sub>",
            font=dict(size=15, color="#1a237e"),
            x=0.5,
        ),
        margin=dict(t=80, b=40, l=60, r=60),
        paper_bgcolor="white",
        height=480,
    )
    return fig


def _quebra_label(texto: str, max_chars: int = 16) -> str:
    """Quebra rótulos longos em duas linhas para caber no gráfico."""
    if len(texto) <= max_chars:
        return texto
    palavras = texto.split()
    linha1, linha2 = [], []
    for p in palavras:
        if sum(len(w) for w in linha1) + len(p) < max_chars:
            linha1.append(p)
        else:
            linha2.append(p)
    return " ".join(linha1) + "\n" + " ".join(linha2)
