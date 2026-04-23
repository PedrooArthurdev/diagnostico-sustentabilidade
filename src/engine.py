"""
engine.py - Motor de cálculo de scores de sustentabilidade municipal.

Responsável por:
- Carregar o schema de indicadores/pesos (indicadores.json)
- Processar respostas brutas do Google Forms (CSV)
- Calcular scores normalizados (0-10) por categoria e score final ponderado
"""

from __future__ import annotations

import json
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class ScoreCategoria:
    id: str
    nome: str
    score: float          # 0.0 – 10.0
    nivel: str            # Crítico / Insuficiente / Regular / Bom / Excelente
    cor_nivel: str        # hex, para uso no relatório
    detalhes: dict[str, float] = field(default_factory=dict)  # indicador_id → score parcial


@dataclass
class ResultadoMunicipio:
    municipio: str
    populacao: int
    responsavel: str
    cargo: str
    email: str
    score_final: float
    nivel_geral: str
    cor_nivel_geral: str
    categorias: list[ScoreCategoria] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "municipio": self.municipio,
            "populacao": self.populacao,
            "responsavel": self.responsavel,
            "cargo": self.cargo,
            "email": self.email,
            "score_final": round(self.score_final, 2),
            "nivel_geral": self.nivel_geral,
            "categorias": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "score": round(c.score, 2),
                    "nivel": c.nivel,
                }
                for c in self.categorias
            ],
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class SustainabilityEngine:
    """Carrega o schema e processa respostas brutas em ResultadoMunicipio."""

    def __init__(self, schema_path: str | Path):
        self.schema_path = Path(schema_path)
        self._schema: dict = self._load_schema()
        self._categorias: list[dict] = self._schema["categorias"]
        self._faixas: list[dict] = self._schema["faixas_classificacao"]

    # ------------------------------------------------------------------
    # Públicos
    # ------------------------------------------------------------------

    def process_csv(self, csv_path: str | Path) -> list[ResultadoMunicipio]:
        """Lê o CSV exportado do Google Forms e retorna lista de resultados."""
        resultados: list[ResultadoMunicipio] = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                resultados.append(self._process_row(row))
        return resultados

    def process_dict(self, data: dict[str, Any]) -> ResultadoMunicipio:
        """Processa uma única resposta em formato dicionário."""
        return self._process_row(data)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _load_schema(self) -> dict:
        with open(self.schema_path, encoding="utf-8") as f:
            return json.load(f)

    def _process_row(self, row: dict[str, Any]) -> ResultadoMunicipio:
        """Calcula scores de uma linha do formulário."""
        scores_cat: list[ScoreCategoria] = []
        score_final_ponderado = 0.0

        for categoria in self._categorias:
            cat_id = categoria["id"]
            indicadores = categoria["indicadores"]
            peso_final = categoria["peso_final"]

            score_cat_normalizado, detalhes = self._calc_categoria(
                indicadores, row
            )

            nivel, cor = self._classify(score_cat_normalizado)
            scores_cat.append(
                ScoreCategoria(
                    id=cat_id,
                    nome=categoria["nome"],
                    score=score_cat_normalizado,
                    nivel=nivel,
                    cor_nivel=cor,
                    detalhes=detalhes,
                )
            )
            score_final_ponderado += score_cat_normalizado * peso_final

        nivel_geral, cor_geral = self._classify(score_final_ponderado)

        return ResultadoMunicipio(
            municipio=row.get("municipio", "N/D"),
            populacao=int(row.get("populacao", 0)),
            responsavel=row.get("responsavel", "N/D"),
            cargo=row.get("cargo", "N/D"),
            email=row.get("email", "N/D"),
            score_final=score_final_ponderado,
            nivel_geral=nivel_geral,
            cor_nivel_geral=cor_geral,
            categorias=scores_cat,
        )

    def _calc_categoria(
        self, indicadores: list[dict], row: dict
    ) -> tuple[float, dict[str, float]]:
        """
        Retorna (score_normalizado_0_10, detalhes_por_indicador).

        Fórmula:
            score_bruto = Σ (resposta_i / escala_i) * peso_i
            score_normalizado = score_bruto * 10
        """
        score_bruto = 0.0
        detalhes: dict[str, float] = {}

        for ind in indicadores:
            ind_id = ind["id"]
            peso = ind["peso"]
            escala = ind["escala"]  # valor máximo da escala (ex: 4)

            raw = row.get(ind_id, 0)
            try:
                valor = float(raw)
            except (ValueError, TypeError):
                valor = 0.0

            valor = max(0.0, min(float(escala), valor))
            contribuicao = (valor / escala) * peso
            score_bruto += contribuicao
            detalhes[ind_id] = round(contribuicao * 10, 3)

        return score_bruto * 10, detalhes

    def _classify(self, score: float) -> tuple[str, str]:
        """Retorna (nivel, cor_hex) para um score 0-10.

        Usa intervalo fechado apenas no último nível [min, max],
        e meio-aberto [min, max) nos demais, evitando sobreposição nos limites.
        """
        last = len(self._faixas) - 1
        for i, faixa in enumerate(self._faixas):
            upper_ok = score <= faixa["maximo"] if i == last else score < faixa["maximo"]
            if faixa["minimo"] <= score and upper_ok:
                return faixa["nivel"], faixa["cor"]
        return "Indefinido", "#9E9E9E"


# ---------------------------------------------------------------------------
# Recomendações
# ---------------------------------------------------------------------------

RECOMENDACOES: dict[str, list[dict[str, str]]] = {
    "saneamento_basico": [
        {
            "nivel_max": "Insuficiente",
            "texto": "Elaborar Plano Municipal de Saneamento Básico (PMSB) conforme Lei 14.026/2020.",
        },
        {
            "nivel_max": "Regular",
            "texto": "Ampliar rede de esgotamento sanitário com prioridade em áreas de vulnerabilidade social.",
        },
        {
            "nivel_max": "Bom",
            "texto": "Implantar sistema de monitoramento contínuo de qualidade da água.",
        },
    ],
    "gestao_residuos": [
        {
            "nivel_max": "Insuficiente",
            "texto": "Encerrar lixões e implantar aterro sanitário licenciado conforme PNRS (Lei 12.305/2010).",
        },
        {
            "nivel_max": "Regular",
            "texto": "Estruturar cooperativas de catadores e implantar coleta seletiva.",
        },
        {
            "nivel_max": "Bom",
            "texto": "Elaborar e implementar o PMGIRS com metas anuais de redução de resíduos.",
        },
    ],
    "mobilidade_urbana": [
        {
            "nivel_max": "Insuficiente",
            "texto": "Elaborar Plano de Mobilidade Urbana (PlanMob) conforme Lei 12.587/2012.",
        },
        {
            "nivel_max": "Regular",
            "texto": "Ampliar infraestrutura de calçadas acessíveis e ciclovias conectadas.",
        },
        {
            "nivel_max": "Bom",
            "texto": "Renovar frota de transporte público com veículos de menor emissão.",
        },
    ],
    "educacao_ambiental": [
        {
            "nivel_max": "Insuficiente",
            "texto": "Criar Programa Municipal de Educação Ambiental (PMEA) alinhado à PNEA (Lei 9.795/1999).",
        },
        {
            "nivel_max": "Regular",
            "texto": "Inserir educação ambiental como eixo transversal no currículo escolar municipal.",
        },
        {
            "nivel_max": "Bom",
            "texto": "Firmar convênios com universidades para projetos de extensão em sustentabilidade.",
        },
    ],
    "biodiversidade": [
        {
            "nivel_max": "Insuficiente",
            "texto": "Criar Unidades de Conservação municipais e inventariar áreas de relevância ecológica.",
        },
        {
            "nivel_max": "Regular",
            "texto": "Elaborar planos de manejo para UCs existentes e iniciar programas de recuperação de matas ciliares.",
        },
        {
            "nivel_max": "Bom",
            "texto": "Ampliar áreas verdes urbanas para atingir o índice de 12 m²/hab recomendado pela OMS.",
        },
    ],
    "governanca_ambiental": [
        {
            "nivel_max": "Insuficiente",
            "texto": "Criar e regulamentar o Conselho Municipal de Meio Ambiente com representação paritária.",
        },
        {
            "nivel_max": "Regular",
            "texto": "Estruturar a Secretaria Municipal de Meio Ambiente com técnicos especializados.",
        },
        {
            "nivel_max": "Bom",
            "texto": "Atualizar a legislação ambiental municipal e criar mecanismos eficazes de fiscalização.",
        },
    ],
}

ORDEM_NIVEL = ["Crítico", "Insuficiente", "Regular", "Bom", "Excelente"]


def gerar_recomendacoes(resultado: ResultadoMunicipio) -> list[dict]:
    """Retorna lista de recomendações priorizadas para o município."""
    recomendacoes: list[dict] = []
    for cat in resultado.categorias:
        recs_cat = RECOMENDACOES.get(cat.id, [])
        idx_nivel = ORDEM_NIVEL.index(cat.nivel) if cat.nivel in ORDEM_NIVEL else 0
        for rec in recs_cat:
            nivel_max = rec["nivel_max"]
            idx_max = ORDEM_NIVEL.index(nivel_max) if nivel_max in ORDEM_NIVEL else 4
            if idx_nivel <= idx_max:
                recomendacoes.append(
                    {
                        "categoria": cat.nome,
                        "score": cat.score,
                        "nivel": cat.nivel,
                        "recomendacao": rec["texto"],
                    }
                )
    # Prioriza as categorias com menor score
    return sorted(recomendacoes, key=lambda r: r["score"])
