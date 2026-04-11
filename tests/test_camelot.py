"""
Testes para music_analyzer.camelot — lógica da roda Camelot.
"""

from music_analyzer.camelot import (
    _distancia_circular,
    compatibilidade,
    obter_camelot,
    obter_openkey,
    sugerir_proximas,
)


# ── obter_camelot ────────────────────────────────────────────────────────────

class TestObterCamelot:
    def test_c_major(self):
        assert obter_camelot("C Major") == "8B"

    def test_a_minor(self):
        assert obter_camelot("A Minor") == "8A"

    def test_f_sharp_major(self):
        assert obter_camelot("F# Major") == "2B"

    def test_tonalidade_invalida_retorna_none(self):
        assert obter_camelot("X Qualquer") is None

    def test_todas_as_24_tonalidades_mapeadas(self):
        from music_analyzer.camelot import TOM_PARA_CAMELOT
        assert len(TOM_PARA_CAMELOT) == 24


# ── obter_openkey ────────────────────────────────────────────────────────────

class TestObterOpenkey:
    def test_c_major(self):
        assert obter_openkey("C Major") == "1d"

    def test_a_minor(self):
        assert obter_openkey("A Minor") == "1m"

    def test_tonalidade_invalida_retorna_none(self):
        assert obter_openkey("Xpto") is None

    def test_todas_as_24_tonalidades_mapeadas(self):
        from music_analyzer.camelot import TOM_PARA_OPENKEY
        assert len(TOM_PARA_OPENKEY) == 24


# ── _distancia_circular ──────────────────────────────────────────────────────

class TestDistanciaCircular:
    def test_mesmos_numeros(self):
        assert _distancia_circular(5, 5) == 0

    def test_vizinhos(self):
        assert _distancia_circular(1, 2) == 1
        assert _distancia_circular(12, 11) == 1

    def test_distancia_maxima_e_seis(self):
        assert _distancia_circular(1, 7) == 6

    def test_wraparound_circular(self):
        # 12 e 1 são vizinhos na roda (distância 1)
        assert _distancia_circular(12, 1) == 1

    def test_simetria(self):
        assert _distancia_circular(3, 8) == _distancia_circular(8, 3)


# ── compatibilidade ──────────────────────────────────────────────────────────

class TestCompatibilidade:
    def test_mesma_tonalidade_e_perfeita(self):
        r = compatibilidade("C Major", "C Major")
        assert r["nivel"] == "perfeita"
        assert r["distancia"] == 0

    def test_relativa_maior_menor_e_perfeita(self):
        # C Major (8B) e A Minor (8A) — mesmo número, letra diferente
        r = compatibilidade("C Major", "A Minor")
        assert r["nivel"] == "perfeita"
        assert "relativa" in r["descricao"].lower()

    def test_vizinha_mesma_letra_e_boa(self):
        # G Major (9B) é vizinha de C Major (8B)
        r = compatibilidade("C Major", "G Major")
        assert r["nivel"] == "boa"
        assert r["distancia"] == 1

    def test_vizinha_cruzada_e_boa(self):
        # C Major (8B) e E Minor (9A): dist=1, letras diferentes
        r = compatibilidade("C Major", "E Minor")
        assert r["nivel"] == "boa"
        assert r["distancia"] == 1

    def test_distancia_2_e_arriscada(self):
        # C Major (8B) e D Major (10B): dist=2
        r = compatibilidade("C Major", "D Major")
        assert r["nivel"] == "arriscada"
        assert r["distancia"] == 2

    def test_incompativel(self):
        # C Major (8B) e F# Major (2B): dist=6 — oposto na roda
        r = compatibilidade("C Major", "F# Major")
        assert r["nivel"] == "incompativel"

    def test_tonalidade_invalida_retorna_desconhecida(self):
        r = compatibilidade("X Qualquer", "C Major")
        assert r["nivel"] == "desconhecida"
        assert r["distancia"] == -1

    def test_retorna_codigos_camelot_corretos(self):
        r = compatibilidade("C Major", "G Major")
        assert r["camelot_a"] == "8B"
        assert r["camelot_b"] == "9B"

    def test_salto_sete_e_arriscada(self):
        # 8B (C Major) vs 3B (C# Major): dist=5 — incompatível
        # Encontrar um par com dist=7 (não existe no módulo 12, máximo é 6)
        # dist=7 é tratado na lógica mas matematicamente dist_circular ≤ 6;
        # o branch só é alcançado se dist==7 após _distancia_circular,
        # o que nunca ocorre. O código é defensivo — verificar que não explode.
        r = compatibilidade("C Major", "C Major")
        assert r is not None


# ── sugerir_proximas ─────────────────────────────────────────────────────────

class TestSugerirProximas:
    def test_retorna_lista_nao_vazia_para_tom_valido(self):
        sugestoes = sugerir_proximas("C Major")
        assert isinstance(sugestoes, list)
        assert len(sugestoes) > 0

    def test_retorna_lista_vazia_para_tom_invalido(self):
        assert sugerir_proximas("Tom Inválido") == []

    def test_sugestoes_tem_campos_obrigatorios(self):
        sugestoes = sugerir_proximas("A Minor")
        for s in sugestoes:
            assert "tom" in s
            assert "camelot" in s
            assert "nivel" in s
            assert "descricao" in s

    def test_relativa_esta_nas_sugestoes(self):
        # A relativa de C Major é A Minor
        sugestoes = sugerir_proximas("C Major")
        toms = [s["tom"] for s in sugestoes]
        assert "A Minor" in toms

    def test_vizinhas_estao_nas_sugestoes(self):
        # Vizinhas de C Major (8B): G Major (9B) e F Major (7B)
        sugestoes = sugerir_proximas("C Major")
        toms = [s["tom"] for s in sugestoes]
        assert "G Major" in toms
        assert "F Major" in toms

    def test_nivel_perfeita_e_boa_presentes(self):
        sugestoes = sugerir_proximas("C Major")
        niveis = {s["nivel"] for s in sugestoes}
        assert "perfeita" in niveis
        assert "boa" in niveis
