"""
app.py - Interface web Streamlit para o Diagnóstico de Sustentabilidade Municipal.

Para rodar:
    streamlit run app.py
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

from src.engine import SustainabilityEngine, ResultadoMunicipio, gerar_recomendacoes
from src.charts import gerar_radar_plotly
from src.report import gerar_relatorio_pdf

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Diagnóstico de Sustentabilidade Municipal",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCHEMA_PATH = Path("data/indicadores.json")
OUTPUT_DIR  = Path("output")
TMP_DIR     = Path("output/tmp")

NIVEL_EMOJI = {
    "Crítico":      "🔴",
    "Insuficiente": "🟠",
    "Regular":      "🟡",
    "Bom":          "🟢",
    "Excelente":    "✅",
}

NIVEL_COR_HEX = {
    "Crítico":      "#D32F2F",
    "Insuficiente": "#F57C00",
    "Regular":      "#F9A825",
    "Bom":          "#388E3C",
    "Excelente":    "#1B5E20",
}

# ---------------------------------------------------------------------------
# CSS customizado
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1565C0, #0D47A1);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { margin: 0; font-size: 1.7rem; }
    .main-header p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.95rem; }

    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        border-left: 5px solid #1565C0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }
    .metric-card h3 { margin: 0; font-size: 2rem; color: #1565C0; }
    .metric-card p  { margin: 0.2rem 0 0; color: #546E7A; font-size: 0.85rem; }

    .score-badge {
        display: inline-block;
        padding: 0.25rem 0.8rem;
        border-radius: 20px;
        color: white;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1565C0;
        border-bottom: 2px solid #E3F2FD;
        padding-bottom: 0.4rem;
        margin: 1.2rem 0 0.8rem;
    }
    div[data-testid="stTabs"] button { font-size: 1rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cache de processamento
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def processar_csv(conteudo_csv: bytes) -> list[dict]:
    """Processa o CSV e retorna lista de dicionários serializáveis."""
    engine = SustainabilityEngine(SCHEMA_PATH)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as f:
        f.write(conteudo_csv)
        tmp_path = Path(f.name)
    resultados = engine.process_csv(tmp_path)
    tmp_path.unlink(missing_ok=True)
    return [r.to_dict() for r in resultados]


def dict_para_resultado(d: dict) -> ResultadoMunicipio:
    """Reconstrói ResultadoMunicipio a partir do dict serializado."""
    from src.engine import ScoreCategoria, ResultadoMunicipio
    cats = [
        ScoreCategoria(
            id=c["id"],
            nome=c["nome"],
            score=c["score"],
            nivel=c["nivel"],
            cor_nivel=NIVEL_COR_HEX.get(c["nivel"], "#9E9E9E"),
        )
        for c in d["categorias"]
    ]
    nivel = d["nivel_geral"]
    return ResultadoMunicipio(
        municipio=d["municipio"],
        populacao=d["populacao"],
        responsavel=d["responsavel"],
        cargo=d["cargo"],
        email=d["email"],
        score_final=d["score_final"],
        nivel_geral=nivel,
        cor_nivel_geral=NIVEL_COR_HEX.get(nivel, "#9E9E9E"),
        categorias=cats,
    )


@st.cache_data(show_spinner=False)
def gerar_pdf_bytes(municipio_dict: str) -> bytes:
    """Gera o PDF e retorna como bytes para download."""
    import json
    d = json.loads(municipio_dict)
    resultado = dict_para_resultado(d)
    pdf_path = gerar_relatorio_pdf(resultado, OUTPUT_DIR, TMP_DIR)
    return pdf_path.read_bytes()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🌿 Diagnóstico Municipal")
    st.markdown("**ONG Pará · Sistema de Avaliação Ambiental**")
    st.divider()

    st.markdown("### 📂 Carregar dados")
    uploaded = st.file_uploader(
        "CSV exportado do Google Forms",
        type=["csv"],
        help="Exporte as respostas do formulário como CSV e faça upload aqui.",
    )

    if uploaded is not None:
        if st.button("✅ Processar arquivo", use_container_width=True, type="primary"):
            st.session_state["csv_bytes"] = uploaded.read()
            st.session_state.pop("resultados", None)
            st.rerun()

    st.divider()
    st.markdown("### 📋 Sobre")
    st.markdown("""
    Sistema de diagnóstico em **6 categorias**:
    - 💧 Saneamento Básico
    - ♻️ Gestão de Resíduos
    - 🚌 Mobilidade Urbana
    - 📚 Educação Ambiental
    - 🌳 Biodiversidade
    - 🏛️ Governança Ambiental

    Escala: **0 a 10** por categoria.
    """)

    st.divider()
    if st.button("🧪 Usar dados de exemplo", use_container_width=True):
        sample = Path("data/municipios_sample.csv")
        if sample.exists():
            with open(sample, "rb") as f:
                st.session_state["csv_bytes"] = f.read()
            st.session_state.pop("resultados", None)
            st.rerun()


# ---------------------------------------------------------------------------
# Cabeçalho principal
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>🌿 Diagnóstico de Sustentabilidade Municipal</h1>
    <p>Análise integrada de indicadores ambientais · Fase 1 MVP · Pará, Brasil</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Estado da sessão
# ---------------------------------------------------------------------------
csv_bytes = st.session_state.get("csv_bytes")

# ---------------------------------------------------------------------------
# Sem arquivo: tela de boas-vindas
# ---------------------------------------------------------------------------
if not csv_bytes:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.markdown("### 👋 Bem-vindo ao sistema")
        st.markdown("""
        Para começar, faça **upload do CSV** na barra lateral
        ou clique em **"Usar dados de exemplo"** para ver o sistema funcionando.

        O CSV deve ser exportado diretamente das respostas do Google Forms
        com a estrutura de colunas do formulário padrão.
        """)
        st.info("⬅️ Use a barra lateral para carregar um arquivo ou testar com dados de exemplo.")
    st.stop()

# ---------------------------------------------------------------------------
# Processar dados
# ---------------------------------------------------------------------------
if "resultados" not in st.session_state:
    with st.spinner("Processando dados dos municípios..."):
        try:
            st.session_state["resultados"] = processar_csv(csv_bytes)
        except Exception as e:
            st.error(f"Erro ao processar o CSV: {e}")
            st.stop()

resultados_dicts: list[dict] = st.session_state["resultados"]

# Valida se o CSV tinha o formato correto (municípios não podem ser todos N/D)
municipios_nd = sum(1 for r in resultados_dicts if r["municipio"] == "N/D")
if municipios_nd == len(resultados_dicts):
    st.error(
        "⚠️ O CSV enviado não está no formato esperado pelo sistema. "
        "As colunas não foram reconhecidas. "
        "Verifique se o arquivo foi exportado corretamente do Google Forms "
        "ou use os **dados de exemplo** na barra lateral para testar."
    )
    st.info(
        "**Formato esperado:** o CSV deve ter colunas como `municipio`, `sb_01`, `sb_02`, "
        "`gr_01`... conforme o modelo do formulário padrão do sistema."
    )
    if st.button("🧪 Carregar dados de exemplo agora", type="primary"):
        sample = Path("data/municipios_sample.csv")
        with open(sample, "rb") as f:
            st.session_state["csv_bytes"] = f.read()
        st.session_state.pop("resultados", None)
        st.rerun()
    st.stop()

ranking = sorted(resultados_dicts, key=lambda r: r["score_final"], reverse=True)

# ---------------------------------------------------------------------------
# Métricas gerais
# ---------------------------------------------------------------------------
total       = len(ranking)
media_geral = sum(r["score_final"] for r in ranking) / total
melhor      = ranking[0]
pior        = ranking[-1]

# Categoria com menor média
cat_medias: dict[str, list[float]] = {}
for r in ranking:
    for c in r["categorias"]:
        cat_medias.setdefault(c["nome"], []).append(c["score"])
cat_media_final = {n: sum(v)/len(v) for n, v in cat_medias.items()}
cat_critica = min(cat_media_final, key=cat_media_final.get)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <h3>{total}</h3><p>Municípios avaliados</p>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <h3>{media_geral:.1f}</h3><p>Score médio geral (0–10)</p>
    </div>""", unsafe_allow_html=True)
with c3:
    cor_melhor = NIVEL_COR_HEX.get(melhor["nivel_geral"], "#388E3C")
    st.markdown(f"""
    <div class="metric-card" style="border-color:{cor_melhor}">
        <h3 style="color:{cor_melhor}">{melhor["municipio"]}</h3>
        <p>Melhor avaliado · {melhor["score_final"]:.1f}</p>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="metric-card" style="border-color:#D32F2F">
        <h3 style="color:#D32F2F; font-size:1.1rem">{cat_critica}</h3>
        <p>Categoria mais crítica · {cat_media_final[cat_critica]:.1f}</p>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Abas principais
# ---------------------------------------------------------------------------
aba_ranking, aba_detalhe, aba_comparar = st.tabs(
    ["📊 Ranking Geral", "🔍 Diagnóstico Individual", "📈 Comparar Categorias"]
)

# ============================================================
# ABA 1 — RANKING
# ============================================================
with aba_ranking:
    st.markdown('<div class="section-title">Ranking de Municípios</div>', unsafe_allow_html=True)

    linhas = []
    for i, r in enumerate(ranking):
        emoji = NIVEL_EMOJI.get(r["nivel_geral"], "⚪")
        medalha = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}º"
        linhas.append({
            "Pos.":       medalha,
            "Município":  r["municipio"],
            "Score":      r["score_final"],
            "Nível":      f"{emoji} {r['nivel_geral']}",
            "População":  f"{r['populacao']:,}".replace(",", "."),
        })

    df_rank = pd.DataFrame(linhas)

    def colorir_score(val):
        if val >= 8.5:   return "background-color:#E8F5E9; color:#1B5E20; font-weight:bold"
        if val >= 7.0:   return "background-color:#F1F8E9; color:#388E3C; font-weight:bold"
        if val >= 5.0:   return "background-color:#FFFDE7; color:#F57F17; font-weight:bold"
        if val >= 2.5:   return "background-color:#FFF3E0; color:#E65100; font-weight:bold"
        return "background-color:#FFEBEE; color:#B71C1C; font-weight:bold"

    st.dataframe(
        df_rank.style
            .map(colorir_score, subset=["Score"])
            .format({"Score": "{:.1f}"}),
        use_container_width=True,
        hide_index=True,
        height=min(80 + total * 38, 500),
    )

    st.markdown('<div class="section-title">Scores por Categoria (todos os municípios)</div>', unsafe_allow_html=True)

    cat_rows = []
    for r in ranking:
        row = {"Município": r["municipio"]}
        for c in r["categorias"]:
            row[c["nome"][:22]] = round(c["score"], 1)
        cat_rows.append(row)

    df_cats = pd.DataFrame(cat_rows)  # índice padrão numérico — evita conflito com Styler

    def colorir_celula(val):
        if not isinstance(val, (int, float)):
            return ""
        if val >= 7.0:   return "background-color:#C8E6C9; color:#1B5E20"
        if val >= 5.0:   return "background-color:#FFF9C4; color:#F57F17"
        if val >= 2.5:   return "background-color:#FFE0B2; color:#E65100"
        return "background-color:#FFCDD2; color:#B71C1C"

    colunas_score = [c for c in df_cats.columns if c != "Município"]
    st.dataframe(
        df_cats.style
            .map(colorir_celula, subset=colunas_score)
            .format("{:.1f}", subset=colunas_score),
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# ABA 2 — DIAGNÓSTICO INDIVIDUAL
# ============================================================
with aba_detalhe:
    nomes = [r["municipio"] for r in ranking]
    municipio_sel = st.selectbox("Selecione o município", nomes)

    res_dict = next(r for r in resultados_dicts if r["municipio"] == municipio_sel)
    resultado = dict_para_resultado(res_dict)

    # Cabeçalho do município
    cor_nivel = NIVEL_COR_HEX.get(resultado.nivel_geral, "#9E9E9E")
    emoji_nivel = NIVEL_EMOJI.get(resultado.nivel_geral, "⚪")

    col_info, col_score = st.columns([3, 1])
    with col_info:
        st.markdown(f"**Responsável:** {resultado.responsavel} · {resultado.cargo}")
        st.markdown(f"**E-mail:** {resultado.email} &nbsp;|&nbsp; **População:** {resultado.populacao:,}".replace(",", "."))
    with col_score:
        st.markdown(f"""
        <div style="text-align:center; background:{cor_nivel}; padding:0.8rem 1rem;
                    border-radius:10px; color:white;">
            <div style="font-size:2rem; font-weight:800">{resultado.score_final:.1f}</div>
            <div style="font-size:1rem">{emoji_nivel} {resultado.nivel_geral}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    col_radar, col_tabela = st.columns([3, 2])

    with col_radar:
        fig = gerar_radar_plotly(
            [c.nome for c in resultado.categorias],
            [c.score for c in resultado.categorias],
            resultado.municipio,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_tabela:
        st.markdown('<div class="section-title">Scores por Categoria</div>', unsafe_allow_html=True)
        for cat in sorted(resultado.categorias, key=lambda c: c.score):
            cor  = NIVEL_COR_HEX.get(cat.nivel, "#9E9E9E")
            emj  = NIVEL_EMOJI.get(cat.nivel, "⚪")
            pct  = int(cat.score / 10 * 100)
            st.markdown(f"""
            <div style="margin-bottom:0.6rem">
                <div style="display:flex; justify-content:space-between; margin-bottom:3px">
                    <span style="font-size:0.85rem; font-weight:600">{cat.nome}</span>
                    <span style="font-size:0.85rem; color:{cor}; font-weight:700">{cat.score:.1f} {emj}</span>
                </div>
                <div style="background:#E0E0E0; border-radius:6px; height:8px">
                    <div style="background:{cor}; width:{pct}%; height:8px; border-radius:6px"></div>
                </div>
            </div>""", unsafe_allow_html=True)

    # Recomendações
    st.markdown('<div class="section-title">Recomendações Prioritárias</div>', unsafe_allow_html=True)
    recomendacoes = gerar_recomendacoes(resultado)
    if recomendacoes:
        for rec in recomendacoes:
            cor  = NIVEL_COR_HEX.get(rec["nivel"], "#9E9E9E")
            emj  = NIVEL_EMOJI.get(rec["nivel"], "⚪")
            with st.container():
                st.markdown(f"""
                <div style="border-left:4px solid {cor}; padding:0.6rem 1rem;
                            background:#FAFAFA; border-radius:0 8px 8px 0; margin-bottom:0.6rem">
                    <div style="font-size:0.78rem; color:{cor}; font-weight:700; margin-bottom:3px">
                        {emj} {rec['categoria']} · Score {rec['score']:.1f}
                    </div>
                    <div style="font-size:0.9rem; color:#212121">{rec['recomendacao']}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.success("✅ Nenhuma recomendação crítica para este município.")

    # Botão de download do PDF
    st.markdown("---")
    import json
    with st.spinner("Preparando PDF..."):
        try:
            pdf_bytes = gerar_pdf_bytes(json.dumps(res_dict))
            st.download_button(
                label="📄 Baixar Relatório PDF",
                data=pdf_bytes,
                file_name=f"diagnostico_{municipio_sel.lower().replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

# ============================================================
# ABA 3 — COMPARAR CATEGORIAS
# ============================================================
with aba_comparar:
    import plotly.graph_objects as go

    st.markdown('<div class="section-title">Comparação de Municípios por Categoria</div>', unsafe_allow_html=True)

    municipios_sel = st.multiselect(
        "Selecione os municípios para comparar",
        options=nomes,
        default=nomes[:4] if len(nomes) >= 4 else nomes,
    )

    if not municipios_sel:
        st.info("Selecione ao menos um município para comparar.")
    else:
        selecionados = [r for r in resultados_dicts if r["municipio"] in municipios_sel]
        paleta = [
            "#1565C0", "#D32F2F", "#388E3C", "#F57C00",
            "#7B1FA2", "#00838F", "#558B2F", "#6D4C41",
        ]

        def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha})"

        # Radar comparativo
        cats_nomes = [c["nome"] for c in selecionados[0]["categorias"]]
        fig_comp = go.Figure()
        for i, r in enumerate(selecionados):
            scores_m = [c["score"] for c in r["categorias"]]
            scores_m += [scores_m[0]]
            cats_f = cats_nomes + [cats_nomes[0]]
            fig_comp.add_trace(go.Scatterpolar(
                r=scores_m,
                theta=cats_f,
                name=r["municipio"],
                line=dict(color=paleta[i % len(paleta)], width=2),
                fill="toself",
                fillcolor=hex_to_rgba(paleta[i % len(paleta)], alpha=0.12),
            ))
        fig_comp.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            title=dict(text="<b>Comparativo de Sustentabilidade</b>", font=dict(size=14)),
            height=500,
            margin=dict(t=60, b=40),
            paper_bgcolor="white",
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # Gráfico de barras por categoria
        st.markdown('<div class="section-title">Score por Categoria (barras)</div>', unsafe_allow_html=True)
        bar_data = []
        for r in selecionados:
            for c in r["categorias"]:
                bar_data.append({
                    "Município": r["municipio"],
                    "Categoria": c["nome"][:22],
                    "Score": c["score"],
                })
        df_bar = pd.DataFrame(bar_data)

        import plotly.express as px
        fig_bar = px.bar(
            df_bar,
            x="Categoria",
            y="Score",
            color="Município",
            barmode="group",
            color_discrete_sequence=paleta,
            range_y=[0, 10],
        )
        fig_bar.add_hline(y=5, line_dash="dot", line_color="#F57C00",
                          annotation_text="Limiar Regular (5.0)")
        fig_bar.add_hline(y=7, line_dash="dot", line_color="#388E3C",
                          annotation_text="Limiar Bom (7.0)")
        fig_bar.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white",
            margin=dict(t=20, b=60),
            height=400,
        )
        st.plotly_chart(fig_bar, use_container_width=True)
