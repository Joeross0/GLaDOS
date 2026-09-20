from glados.core.spoken_echo import SpokenTranscriptFilter, is_similar_utterance, normalize_utterance


def test_normalize_utterance_strips_punctuation() -> None:
    assert normalize_utterance('Well, since you asked so politely, let\'s see.') == (
        "well since you asked so politely let s see"
    )


def test_echo_matches_fragment_of_recent_tts() -> None:
    filt = SpokenTranscriptFilter(hangover_s=0.0)
    filt.remember("so, let's delve into the mysteries of greek mythology, shall we?")
    assert filt.is_echo("Shall we?")
    assert not filt.is_echo("What do you think about Prometheus?")


def test_similar_utterance_catches_repeated_script() -> None:
    assert is_similar_utterance(
        "I mean, it's a bit like asking for a pet, you know?",
        "I mean it's a bit like asking for a pet you know",
    )
    assert not is_similar_utterance("How are you?", "What time is it?")
