from pathlib import Path
from statistics import quantiles, stdev
from unittest.mock import MagicMock, PropertyMock

import pytest
from pytest import approx

from adapters import (
    AudioAdapter,
    VideoAdapter,
    ImageAdapter,
    Image,
    DefaultImageAdapter,
    NullDigest,
)
from adapters.librosa_audio_adapter import LibrosaAudioAdapter
from metadata import (
    AudioFileMetadata,
    VideoFileMetadata,
    FileMetadata,
    ImageFileMetadata,
    FileMetadataFactory,
    CompositeMetadata,
    ImageMetadata,
)

FIXTURES = Path(__file__).parent / "fixtures"
GRAYSCALE_IMAGE = FIXTURES / "sierpinski.jpg"
COLOUR_IMAGE = FIXTURES / "brazil.png"
AUDIO_FILE = FIXTURES / "100Hz_44100Hz_16bit_05sec.mp3"
VIDEO_FILE = FIXTURES / "valid.mp4"


def test_audio_file_metadata():
    path = Path("/examples/audio.wav")
    duration = 13.33
    entropy = 0.87
    mock_audio_adapter = MagicMock()
    mock_audio_adapter.metrics.return_value = AudioAdapter.Metrics(
        duration=duration, entropy=entropy
    )

    audio_file_metadata = AudioFileMetadata(path, mock_audio_adapter)

    assert audio_file_metadata.duration == duration
    assert audio_file_metadata.entropy == 0.87
    mock_audio_adapter.metrics.assert_called_once_with(path)


def test_audio_file_metadata_factory():
    path = AUDIO_FILE
    audio_file_metadata = (
        FileMetadataFactory().create_metadata(path).metadata(AudioFileMetadata)
    )
    assert isinstance(audio_file_metadata, AudioFileMetadata)
    assert audio_file_metadata.duration == approx(5.0, 0.01)
    assert audio_file_metadata.entropy == approx(1.9632, 0.0001)


def test_composite_metadata():
    existing_file_metadata = FileMetadata(
        GRAYSCALE_IMAGE, DefaultImageAdapter(), NullDigest()
    )
    new_file_metadata = FileMetadata(
        GRAYSCALE_IMAGE, DefaultImageAdapter(), NullDigest()
    )
    audio_file_metadata = AudioFileMetadata(AUDIO_FILE, LibrosaAudioAdapter())

    composite_metadata = CompositeMetadata(existing_file_metadata)

    composite_metadata.add(audio_file_metadata)
    with pytest.raises(ValueError):
        # noinspection PyTypeChecker
        composite_metadata.add("33")
    with pytest.raises(ValueError):
        composite_metadata.add(new_file_metadata)
    composite_metadata.add(new_file_metadata, overwrite=True)
    assert composite_metadata.metadata(FileMetadata) is new_file_metadata
    composite_metadata.add(existing_file_metadata, overwrite=True)
    assert type(composite_metadata.metadata(FileMetadata)) == FileMetadata
    assert composite_metadata.metadata(FileMetadata) == existing_file_metadata
    assert composite_metadata.metadata(AudioFileMetadata) == audio_file_metadata
    assert list(composite_metadata.children) == [
        existing_file_metadata,
        audio_file_metadata,
    ]


def test_video_file_metadata():
    mock_video_adapter = MagicMock(spec=VideoAdapter)
    mock_video_adapter.metrics.return_value = VideoAdapter.Metrics(
        duration=4.0, frame_rate=30
    )
    metadata = VideoFileMetadata(MagicMock(spec=Path), mock_video_adapter)
    assert metadata.duration == approx(4.0)
    assert metadata.frame_rate == approx(30)


def test_video_file_metadata_factory():
    metadata = (
        FileMetadataFactory().create_metadata(VIDEO_FILE).metadata(VideoFileMetadata)
    )
    assert metadata.duration == approx(4.96666, 0.00001)
    assert metadata.frame_rate == approx(30)
    assert metadata.width == 190
    assert metadata.height == 240


def test_test_metadata_factory_empty_file(tmp_path):
    empty_file = tmp_path / "test.txt"
    empty_file.touch()
    metadata = FileMetadataFactory().create_metadata(empty_file).metadata(FileMetadata)
    assert isinstance(metadata, FileMetadata)
    assert metadata.size == 0
    assert metadata.histogram_image_metadata.histogram == ([256 * 256] + 255 * [0]) * 3
    assert metadata.histogram_image_metadata.fractal_dimension == [approx(0)] * 256
    assert metadata.histogram_image_metadata.entropy == approx(1.584962)
    assert metadata.checksum == "700ccbe90581dc21"
    assert metadata.path_with_checksum == tmp_path / "test.700ccbe90581dc21.txt"


def test_metadata_factory_text_file(tmp_path):
    text_file = tmp_path / "test.txt"
    text_file.write_text("Hello World")
    metadata = FileMetadataFactory().create_metadata(text_file).metadata(FileMetadata)
    assert isinstance(metadata, FileMetadata)
    assert metadata.size == 11
    assert (
        metadata.histogram_image_metadata.histogram == ([65526] + [0] * 254 + [10]) * 3
    )
    assert metadata.histogram_image_metadata.fractal_dimension == [
        approx(0.6097147)
    ] * 255 + [approx(0)]
    assert metadata.histogram_image_metadata.entropy == approx(1.587117)
    assert metadata.checksum == "f8a5e764340d6f3e"
    assert metadata.path_with_checksum == tmp_path / "test.f8a5e764340d6f3e.txt"


def test_metadata_factory_grayscale_image():
    image_file = GRAYSCALE_IMAGE
    factory = FileMetadataFactory()
    all_metadata: CompositeMetadata = factory.create_metadata(image_file)
    metadata = all_metadata.metadata(ImageFileMetadata)
    assert isinstance(metadata, ImageFileMetadata)
    assert metadata.image_metadata.width == 1018
    assert metadata.image_metadata.height == 821
    assert quantiles(metadata.image_metadata.histogram) == [27.0, 40.5, 73.0]
    assert quantiles(metadata.image_metadata.fractal_dimension) == [
        approx(1.5880126),
        approx(1.643898),
        approx(1.660302),
    ]
    assert metadata.image_metadata.entropy == approx(3.0831189)
    metadata = all_metadata.metadata(FileMetadata)
    assert isinstance(metadata, FileMetadata)
    assert metadata.size == 127620
    assert stdev(metadata.histogram_image_metadata.histogram) == approx(1851.915599)
    assert quantiles(metadata.histogram_image_metadata.fractal_dimension) == list(
        map(approx, [0.4932759, 0.50088119, 0.7010070])
    )
    assert quantiles(metadata.histogram_image_metadata.histogram) == [0, 0, 0]
    assert metadata.histogram_image_metadata.entropy == approx(4.1861197)
    assert metadata.checksum == "94cc2cbc92ef3c0f"
    assert (
        metadata.path_with_checksum
        == image_file.parent / "sierpinski.94cc2cbc92ef3c0f.jpg"
    )


def test_metadata_factory_colour_image_file():
    image_file = COLOUR_IMAGE
    factory = FileMetadataFactory()
    all_metadata = factory.create_metadata(image_file)
    metadata = all_metadata.metadata(ImageFileMetadata)
    assert isinstance(metadata, ImageFileMetadata)
    assert metadata.image_metadata.width == 1187
    assert metadata.image_metadata.height == 845
    assert quantiles(metadata.image_metadata.histogram) == [5.0, 8.0, 15.0]
    assert quantiles(metadata.image_metadata.fractal_dimension) == list(
        map(approx, [0.99072488, 1.389666, 1.402276])
    )
    assert metadata.image_metadata.entropy == approx(1.278420)
    metadata = all_metadata.metadata(FileMetadata)
    assert isinstance(metadata, FileMetadata)
    assert metadata.size == 19845
    assert stdev(metadata.histogram_image_metadata.histogram) == approx(3309.278007)
    assert quantiles(metadata.histogram_image_metadata.fractal_dimension) == list(
        map(approx, [0.21160032, 1.9942328, 1.9943503])
    )
    assert metadata.histogram_image_metadata.entropy == approx(2.5157758)
    assert metadata.checksum == "139f194152e9346c"
    assert (
        metadata.path_with_checksum == image_file.parent / "brazil.139f194152e9346c.png"
    )


@pytest.fixture
def sample_file(tmp_path):
    """Fixture to create a sample file for testing"""
    file_path = tmp_path / "test.txt"
    file_path.write_text("sample text")
    return file_path


@pytest.fixture
def file_factory():
    """Fixture to create a FileMetadataFactory object"""
    return FileMetadataFactory()


def test_file_metadata_creation(sample_file, file_factory):
    """Test the creation of FileMetadata object using the factory"""
    metadata = file_factory.create_metadata(sample_file).metadata(FileMetadata)
    assert isinstance(metadata, FileMetadata)
    assert metadata.path == sample_file
    assert metadata.size == 11


def test_image_metadata():
    mock_image_adapter = MagicMock(spec=ImageAdapter)
    image = MagicMock(spec=Image)
    type(mock_image_adapter).last_size = PropertyMock(return_value=(1280, 720))
    assert mock_image_adapter.last_size == (1280, 720)

    image_metadata = ImageMetadata(
        image=image, image_adapter=mock_image_adapter, fractal_dimension=3
    )

    assert image_metadata.width == 1280
    assert image_metadata.height == 720
