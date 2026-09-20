from glados.audio_io import get_audio_system


def test_sounddevice_accepts_input_device_option() -> None:
    audio = get_audio_system("sounddevice", backend_options={"input_device": None})
    assert audio.get_input_device() is None


def test_sounddevice_rejects_unknown_option() -> None:
    try:
        get_audio_system("sounddevice", backend_options={"rooms": True})
    except ValueError as exc:
        assert "Unsupported sounddevice options" in str(exc)
    else:
        raise AssertionError("expected ValueError")
