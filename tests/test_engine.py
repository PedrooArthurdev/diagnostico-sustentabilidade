"""
Testes unitários para o motor de cálculo (engine.py).
Execute com: python -m pytest tests/ -v
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import SustainabilityEngine, gerar_recomendacoes

SCHEMA = Path("data/indicadores.json")


@pytest.fixture
def engine():
    return SustainabilityEngine(SCHEMA)


@pytest.fixture
def row_perfeito():
    """Município com todas as respostas no valor máximo (4)."""
    return {
        "municipio": "Cidade Perfeita", "populacao": "100000",
        "responsavel": "Teste", "cargo": "Cargo", "email": "t@t.com",
        "sb_01": "4", "sb_02": "4", "sb_03": "4",
        "gr_01": "4", "gr_02": "4", "gr_03": "4",
        "mu_01": "4", "mu_02": "4", "mu_03": "4",
        "ea_01": "4", "ea_02": "4", "ea_03": "4",
        "bv_01": "4", "bv_02": "4", "bv_03": "4",
        "ga_01": "4", "ga_02": "4", "ga_03": "4",
    }


@pytest.fixture
def row_critico():
    """Município com todas as respostas zero."""
    return {
        "municipio": "Cidade Crítica", "populacao": "50000",
        "responsavel": "Teste", "cargo": "Cargo", "email": "t@t.com",
        "sb_01": "0", "sb_02": "0", "sb_03": "0",
        "gr_01": "0", "gr_02": "0", "gr_03": "0",
        "mu_01": "0", "mu_02": "0", "mu_03": "0",
        "ea_01": "0", "ea_02": "0", "ea_03": "0",
        "bv_01": "0", "bv_02": "0", "bv_03": "0",
        "ga_01": "0", "ga_02": "0", "ga_03": "0",
    }


class TestScoreLimites:
    def test_score_maximo_e_10(self, engine, row_perfeito):
        res = engine.process_dict(row_perfeito)
        assert abs(res.score_final - 10.0) < 0.001

    def test_score_minimo_e_0(self, engine, row_critico):
        res = engine.process_dict(row_critico)
        assert abs(res.score_final - 0.0) < 0.001

    def test_categorias_max_score_10(self, engine, row_perfeito):
        res = engine.process_dict(row_perfeito)
        for cat in res.categorias:
            assert abs(cat.score - 10.0) < 0.001, f"{cat.nome} não atingiu 10.0"

    def test_categorias_min_score_0(self, engine, row_critico):
        res = engine.process_dict(row_critico)
        for cat in res.categorias:
            assert abs(cat.score - 0.0) < 0.001, f"{cat.nome} não zerou"


class TestClassificacao:
    def test_nivel_excelente(self, engine, row_perfeito):
        res = engine.process_dict(row_perfeito)
        assert res.nivel_geral == "Excelente"

    def test_nivel_critico(self, engine, row_critico):
        res = engine.process_dict(row_critico)
        assert res.nivel_geral == "Crítico"

    def test_nivel_regular(self, engine):
        row = {
            "municipio": "Regular", "populacao": "10000",
            "responsavel": "A", "cargo": "B", "email": "a@b.com",
            **{k: "2" for k in [
                "sb_01","sb_02","sb_03","gr_01","gr_02","gr_03",
                "mu_01","mu_02","mu_03","ea_01","ea_02","ea_03",
                "bv_01","bv_02","bv_03","ga_01","ga_02","ga_03",
            ]}
        }
        res = engine.process_dict(row)
        # score deve ser 5.0 (2/4 * 10 = 5)
        assert abs(res.score_final - 5.0) < 0.01
        assert res.nivel_geral == "Regular"


class TestCSV:
    def test_csv_retorna_lista(self, engine):
        resultados = engine.process_csv(Path("data/municipios_sample.csv"))
        assert isinstance(resultados, list)
        assert len(resultados) > 0

    def test_municipio_belem_presente(self, engine):
        resultados = engine.process_csv(Path("data/municipios_sample.csv"))
        nomes = [r.municipio for r in resultados]
        assert "Belém" in nomes

    def test_numero_categorias(self, engine):
        resultados = engine.process_csv(Path("data/municipios_sample.csv"))
        for res in resultados:
            assert len(res.categorias) == 6, "Deve haver 6 categorias"


class TestRecomendacoes:
    def test_municipio_critico_tem_recomendacoes(self, engine, row_critico):
        res = engine.process_dict(row_critico)
        recs = gerar_recomendacoes(res)
        assert len(recs) > 0

    def test_municipio_excelente_sem_recomendacoes_criticas(self, engine, row_perfeito):
        res = engine.process_dict(row_perfeito)
        recs = gerar_recomendacoes(res)
        assert len(recs) == 0

    def test_recomendacoes_ordenadas_por_score(self, engine, row_critico):
        res = engine.process_dict(row_critico)
        recs = gerar_recomendacoes(res)
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores)
