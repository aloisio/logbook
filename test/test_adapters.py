from base64 import b64encode
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from pytest import approx

from adapter import (
    Image,
    AudioAdapter,
    FileTypeAdapter,
    DefaultFileTypeAdapter,
    VideoAdapter,
)
from adapter.audio_adapter import LibrosaAudioAdapter
from adapter.image_adapter import DefaultImageAdapter
from adapter.video_adapter import DefaultVideoAdapter

FIXTURES = Path(__file__).parent / "fixtures"
AUDIO_FILE = FIXTURES / "100Hz_44100Hz_16bit_05sec.mp3"
VIDEO_FILE = FIXTURES / "valid.mp4"
COLOUR_IMAGE = FIXTURES / "brazil.png"
GRAYSCALE_IMAGE = FIXTURES / "sierpinski.jpg"


def test_from_data_url():
    # Define a sample image
    sample_image = PILImage.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    sample_image.save(buffer, format="PNG")
    image_data = buffer.getvalue()

    # Convert the image to a data url
    data_url = f"data:image/png;base64,{b64encode(image_data).decode()}"

    # Test the from_data_url method
    adapter = DefaultImageAdapter()
    img = adapter.from_data_url(data_url)

    # Verify the result
    assert isinstance(img, Image)
    assert img.mode == "RGB"
    assert img.size == (100, 100)
    assert img.getpixel((0, 0)) == (255, 0, 0)


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
    assert spec.frame_numbers == ([4, 20, 36, 52, 68, 84, 100, 116, 132])
    assert spec.total_number_of_frames == 149
