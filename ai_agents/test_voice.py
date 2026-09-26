"""Script de Teste e Validação do Módulo de Voz ElevenLabs e Mesa Viva.

Valida:
1. Mapeamento de vozes dos 8 protagonistas + O Mestre da Ordem.
2. Sistema de Cache em Disco (SHA256, quota preservation, hits e misses).
3. Gerenciamento de credenciais e modo Fallback gracioso (offline/sem chave).
4. Reprodução de áudio assíncrona (Windows MCI e thread pool).
5. Integração com o loop do AgenteGameOrchestrator.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Garante import do pacote ai_agents
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_agents.voice_elevenlabs import (
    ElevenLabsVoiceManager,
    DEFAULT_VOICE_PROFILES,
    WindowsAudioPlayer,
    AudioCacheManager,
)
from ai_agents.orchestrator import AgenteGameOrchestrator
from ai_agents.schemas import AgenteFicha, TurnoDecisao, AcaoPadrao, MovimentoAcao


def test_voice_profiles_mapping():
    """Valida o mapeamento dos 8 protagonistas + O Mestre."""
    print("\n" + "=" * 60)
    print(" [1/5] TESTANDO MAPEAMENTO DE VOZES (8 PROTAGONISTAS + O MESTRE)")
    print("=" * 60)

    manager = ElevenLabsVoiceManager(api_key="mock_key_for_test")

    personagens_alvo = [
        ("Arthur", "arthur", "grave, forte e determinada"),
        ("Arthur Cervero", "arthur", "grave, forte e determinada"),
        ("Kaiser", "kaiser", "jovem, ágil e focada"),
        ("Dante", "dante", "sombria, misteriosa e sussurrada"),
        ("Joui", "joui", "honrada, energética e respeitosa"),
        ("Joui Jouki", "joui", "honrada, energética e respeitosa"),
        ("Liz", "liz", "serena, empática e científica"),
        ("Liz Sena", "liz", "serena, empática e científica"),
        ("Thiago", "thiago", "madura, firme e de liderança"),
        ("Thiago Fritz", "thiago", "madura, firme e de liderança"),
        ("Rubens", "rubens", "prática, direta e rouca"),
        ("Rubens Naluti", "rubens", "prática, direta e rouca"),
        ("Milo", "milo", "excêntrica e intensa"),
        ("Milo Foster", "milo", "excêntrica e intensa"),
        ("O Mestre", "mestre", "profunda e cinematográfica"),
        ("Narrador", "mestre", "profunda e cinematográfica"),
    ]

    for entrada_nome, chave_esperada, desc_esperada in personagens_alvo:
        profile = manager.resolve_voice_profile(entrada_nome)
        assert profile.speaker_key == chave_esperada, (
            f"Erro: '{entrada_nome}' mapeou para '{profile.speaker_key}', esperado '{chave_esperada}'"
        )
        print(f"  [OK] '{entrada_nome:15}' -> {profile.display_name:15} | Voice ID: {profile.voice_id[:10]}... | {profile.description}")

    # Checa contagem total de perfis canônicos
    assert len(DEFAULT_VOICE_PROFILES) >= 9, "Devem existir ao menos 9 perfis (8 protagonistas + O Mestre)"
    print("  -> Todos os 8 protagonistas e O Mestre mapeados com sucesso!\n")


def test_audio_cache_system():
    """Valida o mecanismo de hash e cache em disco."""
    print("=" * 60)
    print(" [2/5] TESTANDO SISTEMA DE CACHE EM DISCO (SHA256 & QUOTA)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        cache = AudioCacheManager(cache_dir=Path(temp_dir))
        settings = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.0, "use_speaker_boost": True}

        texto = "Pelo poder do Sangue, eu não vou cair hoje!"
        voice_id = "test_voice_id_123"
        model_id = "eleven_multilingual_v2"

        # 1. Teste de Hashing
        hash_1 = cache.compute_hash(texto, voice_id, model_id, settings)
        hash_2 = cache.compute_hash("   " + texto + "  \n", voice_id, model_id, settings)
        assert hash_1 == hash_2, "O hash deve ser normalizado para variações de espaçamento."
        print(f"  [OK] Hash SHA256 gerado: {hash_1[:20]}...")

        # 2. Teste de Cache Miss
        cached = cache.get_cached_path("arthur", hash_1)
        assert cached is None, "Primeira consulta deve resultar em Cache Miss."
        assert cache.misses == 1, "Contador de misses deve ser 1."
        print("  [OK] Cache Miss validado na 1ª requisição.")

        # 3. Salva áudio sintético no cache
        mock_audio_bytes = b"ID3\x04\x00\x00\x00\x00\x00#MOCK_ELEVENLABS_AUDIO_BYTES_FOR_CACHE_TEST"
        saved_file = cache.save_to_cache("arthur", hash_1, mock_audio_bytes)
        assert saved_file.exists(), "Arquivo deve existir no diretório de cache."
        assert saved_file.stat().st_size == len(mock_audio_bytes)
        print(f"  [OK] Áudio gravado no cache com sucesso: {saved_file.name}")

        # 4. Teste de Cache Hit
        cached_hit = cache.get_cached_path("arthur", hash_1)
        assert cached_hit is not None, "Segunda consulta deve resultar em Cache Hit."
        assert cached_hit == saved_file, "Caminho retornado deve ser idêntico ao gravado."
        assert cache.hits == 1, "Contador de hits deve ser 1."
        print("  [OK] Cache Hit validado na 2ª requisição (Quota economizada!).")

        stats = cache.get_stats()
        print(f"  [OK] Estatísticas do Cache: {stats}")
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio_percent"] == 50.0


def test_graceful_fallback():
    """Valida o comportamento com ausência de chave de API ou erro de rede."""
    print("=" * 60)
    print(" [3/5] TESTANDO FALLBACK GRACIOSO (SEM CHAVE / OFFLINE)")
    print("=" * 60)

    # Inicializa sem chave de API
    manager = ElevenLabsVoiceManager(api_key="")
    assert not manager.has_valid_api_key, "Manager não deve considerar chave vazia como válida."

    # Teste de synthesize sem chave (não deve levantar exceção)
    result = manager.synthesize("O ritual consome as sombras ao redor.", speaker_name="Dante")
    assert result is None, "Synthesize sem API Key deve retornar None sem travar."
    print("  [OK] Fallback silencioso executado sem quebrar o loop do jogo.")

    # Teste de speak no modo fallback
    result_speak = manager.speak("Não baixem a guarda!", speaker_name="Thiago Fritz")
    assert result_speak is None, "Speak sem chave deve registrar log e retornar None graciosamente."
    print("  [OK] Fala de personagem simulada textualmente com sucesso.")


def test_windows_audio_player():
    """Valida a reprodução assíncrona não-bloqueante no Windows."""
    print("=" * 60)
    print(" [4/5] TESTANDO REPRODUÇÃO ASSÍNCRONA COMPATÍVEL COM WINDOWS")
    print("=" * 60)

    player = WindowsAudioPlayer()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        # Cria um arquivo simulado de áudio MP3
        f.write(b"MOCK_AUDIO_DATA_FOR_NON_BLOCKING_TEST")
        temp_audio = Path(f.name)

    try:
        t0 = time.time()
        # Disparo assíncrono (não bloqueante)
        success = player.play(temp_audio, async_play=True)
        duration = time.time() - t0
        assert success is True, "player.play deve retornar True."
        assert duration < 0.25, f"Disparo assíncrono deve ser imediato (<250ms), levou {duration:.4f}s"
        print(f"  [OK] Playback assíncrono disparado em {duration*1000:.2f}ms (Não-bloqueante!).")

        player.stop_all()
        print("  [OK] Comando stop_all executado com segurança.")
    finally:
        if temp_audio.exists():
            try:
                temp_audio.unlink()
            except OSError:
                pass


class MockLLMClient:
    """Mock do cliente LLM para testar o loop do orquestrador sem dependência de rede local."""
    def request_turn_decision(self, system_prompt: str, user_prompt: str) -> TurnoDecisao:
        return TurnoDecisao(
            pensamento="Preciso proteger meus aliados e avançar pela lateral.",
            fala="Mantenham a formação! Eu cuido do flanco direito!",
            movimento=MovimentoAcao(destino_grid="C4", descricao="Avança com cautela."),
            acao_padrao=AcaoPadrao(tipo="ataque", arma="Espingarda", alvo_nome="Zumbi de Sangue"),
        )


def test_orchestrator_integration():
    """Valida a integração completa com o AgenteGameOrchestrator."""
    print("=" * 60)
    print(" [5/5] TESTANDO INTEGRAÇÃO COM O ORQUESTRADOR DE JOGO")
    print("=" * 60)

    # Cria voice manager em modo de teste
    test_voice = ElevenLabsVoiceManager(api_key="")
    orchestrator = AgenteGameOrchestrator(
        llm_client=MockLLMClient(),
        voice_manager=test_voice,
    )

    # 1. Testa narração d'O Mestre
    narracao = "Uma névoa espessa rasteja pelo assoalho. O som de passos arrastados ecoa."
    orchestrator.narrar_mestre(narracao, async_play=True)
    print("  [OK] Narração d'O Mestre engatilhada no loop.")

    # 2. Testa turno do agente com fala
    decisao = orchestrator.executar_turno_agente(
        token_id=1,  # Arthur
        narrativa_mestre=narracao,
        narrar_mestre_agora=False,
    )

    assert decisao.fala == "Mantenham a formação! Eu cuido do flanco direito!"
    print(f"  [OK] Turno do Agente {orchestrator.agentes[1].nome} executado com fala: \"{decisao.fala}\"")

    # 3. Testa acesso aos 8 protagonistas cadastrados
    assert len(orchestrator.agentes) >= 8, "Orquestrador deve conter todos os 8 protagonistas cadastrados."
    nomes = [a.nome for a in orchestrator.agentes.values()]
    print(f"  [OK] Protagonistas disponíveis na mesa ({len(nomes)}): {', '.join(nomes)}")


def main():
    print("=" * 70)
    print("      MESA VIVA: SUITE DE TESTES DO MÓDULO ELEVENLABS")
    print("=" * 70)

    t_start = time.time()

    test_voice_profiles_mapping()
    test_audio_cache_system()
    test_graceful_fallback()
    test_windows_audio_player()
    test_orchestrator_integration()

    total_time = time.time() - t_start
    print("=" * 70)
    print(f"   TODOS OS TESTES FORAM CONCLUÍDOS COM SUCESSO! ({total_time:.2f}s)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
