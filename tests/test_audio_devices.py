from glados.audio_io import get_audio_system
from glados.audio_io.sounddevice_io import list_input_devices


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


def test_list_input_devices_has_unique_labels() -> None:
    labels = [label for _index, label in list_input_devices()]
    assert labels[0] == "System default"
    assert len(labels) == len(set(labels))
