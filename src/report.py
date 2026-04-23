"""
report.py - Geração do relatório PDF de diagnóstico municipal.

Utiliza ReportLab para montar o documento com:
- Capa / cabeçalho com dados do município
- Gráfico Radar (imagem PNG gerada por charts.py)
- Tabela de scores por categoria
- Tabela de recomendações priorizadas
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from src.engine import ResultadoMunicipio, gerar_recomendacoes
from src.charts import gerar_radar_chart

# Paleta de cores
COR_PRIMARIA = colors.HexColor("#1565C0")
COR_SECUNDARIA = colors.HexColor("#0D47A1")
COR_DESTAQUE = colors.HexColor("#FBC02D")
COR_FUNDO_HEADER = colors.HexColor("#E3F2FD")
COR_TEXTO = colors.HexColor("#212121")
COR_CINZA_CLARO = colors.HexColor("#F5F5F5")

NIVEL_CORES: dict[str, str] = {
    "Crítico": "#D32F2F",
    "Insuficiente": "#F57C00",
    "Regular": "#FBC02D",
    "Bom": "#388E3C",
    "Excelente": "#1B5E20",
}


def gerar_relatorio_pdf(
    resultado: ResultadoMunicipio,
    output_dir: str | Path = "output",
    tmp_dir: str | Path = "output/tmp",
) -> Path:
    """
    Gera o PDF de diagnóstico para um município e retorna o caminho do arquivo.

    Args:
        resultado:  objeto ResultadoMunicipio já calculado pelo engine.
        output_dir: pasta onde o PDF será salvo.
        tmp_dir:    pasta temporária para imagens auxiliares.

    Returns:
        Path do PDF gerado.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = resultado.municipio.lower().replace(" ", "_").replace("/", "-")
    pdf_path = output_dir / f"diagnostico_{safe_name}.pdf"

    # 1. Gerar gráfico radar
    categorias = [c.nome for c in resultado.categorias]
    scores = [c.score for c in resultado.categorias]
    radar_path = gerar_radar_chart(categorias, scores, resultado.municipio, tmp_dir)

    # 2. Montar documento
    doc = BaseDocTemplate(
        str(pdf_path),
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
    )
    template = PageTemplate(
        id="base",
        frames=[frame],
        onPage=_rodape,
    )
    doc.addPageTemplates([template])

    estilos = _estilos()
    historia: list = []

    # --- Capa ---
    historia += _capa(resultado, estilos)
    historia.append(PageBreak())

    # --- Gráfico Radar ---
    historia += _secao_radar(radar_path, estilos)
    historia.append(Spacer(1, 0.5 * cm))

    # --- Tabela de Scores ---
    historia += _tabela_scores(resultado, estilos)
    historia.append(Spacer(1, 0.8 * cm))

    # --- Recomendações ---
    historia += _tabela_recomendacoes(resultado, estilos)

    doc.build(historia)
    return pdf_path


# ---------------------------------------------------------------------------
# Seções
# ---------------------------------------------------------------------------

def _capa(resultado: ResultadoMunicipio, estilos: dict) -> list:
    elementos = []

    # Logo / título do projeto
    elementos.append(Spacer(1, 1 * cm))
    elementos.append(
        Paragraph("DIAGNÓSTICO DE SUSTENTABILIDADE MUNICIPAL", estilos["titulo_capa"])
    )
    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(
        Paragraph("Sistema de Avaliação Ambiental · Fase 1 MVP", estilos["subtitulo_capa"])
    )
    elementos.append(Spacer(1, 1 * cm))

    # Separador
    elementos.append(
        Table([[""]], colWidths=[16 * cm], rowHeights=[0.15 * cm],
              style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), COR_PRIMARIA)]))
    )
    elementos.append(Spacer(1, 1 * cm))

    # Dados do município
    dados = [
        ["Município:", resultado.municipio],
        ["População:", f"{resultado.populacao:,}".replace(",", ".") + " habitantes"],
        ["Responsável:", resultado.responsavel],
        ["Cargo:", resultado.cargo],
        ["E-mail:", resultado.email],
        ["Data do diagnóstico:", date.today().strftime("%d/%m/%Y")],
    ]

    t_dados = Table(dados, colWidths=[5 * cm, 10 * cm])
    t_dados.setStyle(
        TableStyle([
            ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 0), (-1, -1), 11),
            ("TEXTCOLOR",   (0, 0), (0, -1), COR_SECUNDARIA),
            ("TEXTCOLOR",   (1, 0), (1, -1), COR_TEXTO),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COR_FUNDO_HEADER, colors.white]),
            ("ROUNDEDCORNERS", (0, 0), (-1, -1), [4]),
        ])
    )
    elementos.append(t_dados)
    elementos.append(Spacer(1, 1 * cm))

    # Score final em destaque
    cor_nivel = NIVEL_CORES.get(resultado.nivel_geral, "#9E9E9E")
    score_data = [
        [f"SCORE GERAL: {resultado.score_final:.1f} / 10 · {resultado.nivel_geral}"]
    ]
    t_score = Table(score_data, colWidths=[15 * cm])
    t_score.setStyle(
        TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor(cor_nivel)),
            ("TEXTCOLOR",    (0, 0), (-1, -1), colors.white),
            ("FONTNAME",     (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 16),
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",   (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 14),
        ])
    )
    elementos.append(t_score)

    return elementos


def _secao_radar(radar_path: Path, estilos: dict) -> list:
    elementos = [
        Paragraph("Perfil de Sustentabilidade por Categoria", estilos["titulo_secao"]),
        Spacer(1, 0.4 * cm),
    ]
    img = Image(str(radar_path), width=13 * cm, height=13 * cm)
    img.hAlign = "CENTER"
    elementos.append(img)
    return elementos


def _tabela_scores(resultado: ResultadoMunicipio, estilos: dict) -> list:
    elementos = [
        Paragraph("Scores por Categoria", estilos["titulo_secao"]),
        Spacer(1, 0.3 * cm),
    ]

    cabecalho = [["Categoria", "Score (0–10)", "Nível"]]
    linhas = []
    for cat in resultado.categorias:
        linhas.append([cat.nome, f"{cat.score:.1f}", cat.nivel])

    dados = cabecalho + linhas
    t = Table(dados, colWidths=[9 * cm, 3.5 * cm, 3.5 * cm])

    estilo_tabela = [
        # Cabeçalho
        ("BACKGROUND",    (0, 0), (-1, 0), COR_PRIMARIA),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#BDBDBD")),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_CINZA_CLARO]),
    ]

    # Colore a coluna Nível conforme classificação
    for i, cat in enumerate(resultado.categorias, start=1):
        cor = colors.HexColor(NIVEL_CORES.get(cat.nivel, "#9E9E9E"))
        estilo_tabela += [
            ("BACKGROUND", (2, i), (2, i), cor),
            ("TEXTCOLOR",  (2, i), (2, i), colors.white),
            ("FONTNAME",   (2, i), (2, i), "Helvetica-Bold"),
        ]

    t.setStyle(TableStyle(estilo_tabela))
    elementos.append(t)
    return elementos


def _tabela_recomendacoes(resultado: ResultadoMunicipio, estilos: dict) -> list:
    elementos = [
        Paragraph("Recomendações Prioritárias", estilos["titulo_secao"]),
        Spacer(1, 0.3 * cm),
        Paragraph(
            "As recomendações abaixo estão ordenadas por prioridade, "
            "das categorias com menor desempenho para as melhores.",
            estilos["corpo"],
        ),
        Spacer(1, 0.4 * cm),
    ]

    recomendacoes = gerar_recomendacoes(resultado)
    if not recomendacoes:
        elementos.append(
            Paragraph("Nenhuma recomendação crítica identificada.", estilos["corpo"])
        )
        return elementos

    cabecalho = [["Categoria", "Nível", "Recomendação"]]
    linhas = []
    for r in recomendacoes:
        linhas.append([
            Paragraph(r["categoria"], estilos["celula"]),
            Paragraph(r["nivel"], estilos["celula"]),
            Paragraph(r["recomendacao"], estilos["celula_texto"]),
        ])

    dados = cabecalho + linhas
    t = Table(dados, colWidths=[4.5 * cm, 2.5 * cm, 9 * cm])

    estilo_tabela = [
        ("BACKGROUND",    (0, 0), (-1, 0), COR_SECUNDARIA),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("ALIGN",         (1, 0), (1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#BDBDBD")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_CINZA_CLARO]),
    ]

    for i, r in enumerate(recomendacoes, start=1):
        cor = colors.HexColor(NIVEL_CORES.get(r["nivel"], "#9E9E9E"))
        estilo_tabela += [
            ("BACKGROUND", (1, i), (1, i), cor),
            ("TEXTCOLOR",  (1, i), (1, i), colors.white),
            ("FONTNAME",   (1, i), (1, i), "Helvetica-Bold"),
        ]

    t.setStyle(TableStyle(estilo_tabela))
    elementos.append(t)
    return elementos


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo_capa": ParagraphStyle(
            "titulo_capa",
            fontSize=18,
            fontName="Helvetica-Bold",
            textColor=COR_SECUNDARIA,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "subtitulo_capa": ParagraphStyle(
            "subtitulo_capa",
            fontSize=11,
            fontName="Helvetica",
            textColor=colors.HexColor("#546E7A"),
            alignment=TA_CENTER,
        ),
        "titulo_secao": ParagraphStyle(
            "titulo_secao",
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=COR_PRIMARIA,
            spaceBefore=10,
            spaceAfter=4,
            borderPad=4,
        ),
        "corpo": ParagraphStyle(
            "corpo",
            fontSize=9,
            fontName="Helvetica",
            textColor=COR_TEXTO,
            alignment=TA_JUSTIFY,
        ),
        "celula": ParagraphStyle("celula", fontSize=8, fontName="Helvetica"),
        "celula_texto": ParagraphStyle(
            "celula_texto", fontSize=8, fontName="Helvetica", alignment=TA_JUSTIFY
        ),
    }


def _rodape(canvas, doc):
    """Adiciona número de página e linha no rodapé."""
    canvas.saveState()
    canvas.setStrokeColor(COR_PRIMARIA)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.2 * cm, A4[0] - 2 * cm, 1.2 * cm)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#546E7A"))
    canvas.drawString(2 * cm, 0.8 * cm, "Diagnóstico de Sustentabilidade Municipal · Gerado automaticamente")
    canvas.drawRightString(
        A4[0] - 2 * cm, 0.8 * cm, f"Página {doc.page}"
    )
    canvas.restoreState()
