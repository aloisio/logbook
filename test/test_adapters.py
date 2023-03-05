from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
AUDIO_FILE = FIXTURES / "100Hz_44100Hz_16bit_05sec.mp3"
VIDEO_FILE = FIXTURES / "valid.mp4"
COLOUR_IMAGE = FIXTURES / "brazil.png"
GRAYSCALE_IMAGE = FIXTURES / "sierpinski.jpg"

from pytest import approx

from adapters import (
    DefaultAudioAdapter,
    AudioAdapter,
    FileTypeAdapter,
    DefaultFileTypeAdapter,
    VideoAdapter,
    DefaultVideoAdapter,
)


def test_default_audio_adapter():
    adapter: AudioAdapter = DefaultAudioAdapter()
    audio_file = AUDIO_FILE
    assert adapter.duration(audio_file) == approx(5.0, 0.01)


def test_default_file_type_adapter_image():
    adapter: FileTypeAdapter = DefaultFileTypeAdapter()
    assert adapter.is_image(COLOUR_IMAGE)
    assert adapter.is_image(GRAYSCALE_IMAGE)
    assert not adapter.is_image(AUDIO_FILE)
    assert not adapter.is_image(VIDEO_FILE)


def test_default_file_type_adapter_audio():
    adapter: FileTypeAdapter = DefaultFileTypeAdapter()
    assert not adapter.is_audio(COLOUR_IMAGE)
    assert not adapter.is_audio(GRAYSCALE_IMAGE)
    assert adapter.is_audio(AUDIO_FILE)
    assert not adapter.is_audio(VIDEO_FILE)


def test_default_file_type_adapter_video():
    adapter: FileTypeAdapter = DefaultFileTypeAdapter()
    assert not adapter.is_video(COLOUR_IMAGE)
    assert not adapter.is_video(GRAYSCALE_IMAGE)
    assert not adapter.is_video(AUDIO_FILE)
    assert adapter.is_video(VIDEO_FILE)


def test_default_video_adapter():
    adapter: VideoAdapter = DefaultVideoAdapter()
    assert adapter.metrics(VIDEO_FILE)["duration"] == approx(5.0, 0.01)
    assert adapter.metrics(VIDEO_FILE)["frame_rate"] == approx(30, 0.01)
    assert adapter.metrics(VIDEO_FILE)["width"] == 190
    assert adapter.metrics(VIDEO_FILE)["height"] == 240
