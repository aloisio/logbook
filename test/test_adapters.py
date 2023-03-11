from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
AUDIO_FILE = FIXTURES / "100Hz_44100Hz_16bit_05sec.mp3"
VIDEO_FILE = FIXTURES / "valid.mp4"
COLOUR_IMAGE = FIXTURES / "brazil.png"
GRAYSCALE_IMAGE = FIXTURES / "sierpinski.jpg"

from pytest import approx

from adapter import (
    AudioAdapter,
    FileTypeAdapter,
    DefaultFileTypeAdapter,
    VideoAdapter,
)
from adapter.video_adapter import DefaultVideoAdapter
from adapter.image_adapter import DefaultImageAdapter
from adapter.audio_adapter import LibrosaAudioAdapter


def test_default_audio_adapter():
    adapter: AudioAdapter = LibrosaAudioAdapter()
    audio_file = AUDIO_FILE
    assert adapter.metrics(audio_file)["duration"] == approx(5.0, 0.01)
    assert adapter.metrics(audio_file)["entropy"] == approx(1.96, 0.01)


def test_default_image_adapter():
    adapter = DefaultImageAdapter()
    image = adapter.load(GRAYSCALE_IMAGE)
    assert image.width == 1018
    assert image.height == 821


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


def test_default_video_adapter_metrics():
    adapter: VideoAdapter = DefaultVideoAdapter()
    assert adapter.metrics(VIDEO_FILE).duration == approx(5.0, 0.01)
    assert adapter.metrics(VIDEO_FILE).frame_rate == approx(30, 0.01)
    assert adapter.metrics(VIDEO_FILE).width == 190
    assert adapter.metrics(VIDEO_FILE).height == 240
    assert adapter.metrics(VIDEO_FILE).number_of_frames == 149


def test_default_video_adapter_frame_spec():
    adapter = DefaultVideoAdapter()
    spec = adapter.frame_spec(VIDEO_FILE)
    assert spec.size == (202, 256)
    assert spec.frame_numbers == ([8, 23, 38, 53, 68, 83, 98, 113, 128])
    assert spec.total_number_of_frames == 149
