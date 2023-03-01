from pathlib import Path

from pytest import approx

from adapters import DefaultAudioAdapter, AudioAdapter
from test.adapters import FileTypeAdapter, DefaultFileTypeAdapter


def test_default_audio_adapter():
    adapter: AudioAdapter = DefaultAudioAdapter()
    audio_file = Path(__file__).parent / '100Hz_44100Hz_16bit_05sec.mp3'
    assert adapter.duration(audio_file) == approx(5.0, 0.01)


def test_default_file_type_adapter_image():
    adapter: FileTypeAdapter = DefaultFileTypeAdapter()
    assert adapter.is_image(Path('sierpinski.jpg'))
    assert not adapter.is_image(Path('100Hz_44100Hz_16bit_05sec.mp3'))


def test_default_file_type_adapter_audio():
    adapter: FileTypeAdapter = DefaultFileTypeAdapter()
    assert not adapter.is_audio(Path('sierpinski.jpg'))
    assert adapter.is_audio(Path('100Hz_44100Hz_16bit_05sec.mp3'))
