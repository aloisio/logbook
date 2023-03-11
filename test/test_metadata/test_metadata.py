from functools import partial
from pathlib import Path
from statistics import quantiles, stdev
from unittest.mock import MagicMock, PropertyMock

import pytest
from pytest import approx

from adapter import (
    AudioAdapter,
    VideoAdapter,
    ImageAdapter,
    Image,
    NullDigest,
)
from adapter.audio_adapter import LibrosaAudioAdapter
from adapter.image_adapter import DefaultImageAdapter
from metadata.audio_metadata import AudioFileMetadata
from metadata.file_metadata import (
    FileMetadata,
    CompositeMetadata,
    FileMetadataFactory,
)
from metadata.image_metadata import ImageMetadata, ImageFileMetadata
from metadata.video_metadata import VideoFileMetadata

FIXTURES = Path(__file__).parent.parent / "fixtures"
GRAYSCALE_IMAGE = FIXTURES / "sierpinski.jpg"
COLOUR_IMAGE = FIXTURES / "brazil.png"
AUDIO_FILE = FIXTURES / "100Hz_44100Hz_16bit_05sec.mp3"
VIDEO_FILE_ANIMATION = FIXTURES / "valid.mp4"
VIDEO_FILE_MOVIE = FIXTURES / "supertimor.mpg"

around = partial(approx, rel=0.01)


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
    assert composite_metadata.get(FileMetadata) is new_file_metadata
    composite_metadata.add(existing_file_metadata, overwrite=True)
    assert type(composite_metadata.get(FileMetadata)) == FileMetadata
    assert composite_metadata.get(FileMetadata) == existing_file_metadata
    assert composite_metadata.get(AudioFileMetadata) == audio_file_metadata
    assert list(composite_metadata.children) == [
        existing_file_metadata,
        audio_file_metadata,
    ]


def test_video_file_metadata():
    mock_video_adapter = MagicMock(spec=VideoAdapter)
    mock_video_adapter.metrics.return_value = VideoAdapter.Metrics(
        duration=4.0, frame_rate=30, width=256, height=256, number_of_frames=149
    )
    metadata = VideoFileMetadata(
        path=MagicMock(spec=Path),
        video_adapter=mock_video_adapter,
        image_adapter=MagicMock(spec=ImageAdapter),
    )
    assert metadata.duration == around(4.0)
    assert metadata.frame_rate == around(30)


def test_metadata_factory_empty_file(tmp_path):
    empty_file = tmp_path / "test.txt"
    empty_file.touch()
    composite_metadata = FileMetadataFactory().create_metadata(empty_file)
    file_metadata = composite_metadata.get(FileMetadata)
    assert isinstance(file_metadata, FileMetadata)
    assert file_metadata.checksum == "700ccbe90581dc21"
    assert file_metadata.path == empty_file
    assert (
        file_metadata.path_with_checksum
        == empty_file.parent / f"{empty_file.stem}.700ccbe90581dc21.txt"
    )
    assert file_metadata.size == 0
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.rgb_histogram == ([256 * 256] + 255 * [0]) * 3
    assert quantiles(histogram_image_metadata.fractal_dimension) == around([0, 0, 0])
    assert histogram_image_metadata.entropy == [around(1.584962)]
    assert histogram_image_metadata.contrast == around(0)
    assert histogram_image_metadata.saturation_histogram == [65536] + [0] * 255
    assert histogram_image_metadata.edge_intensity == around(0)
    assert histogram_image_metadata.colourfulness == around(0)
    assert histogram_image_metadata.sharpness == around(0)
    assert histogram_image_metadata.blurriness == around(0)
    assert histogram_image_metadata.noise == around(0)
    assert histogram_image_metadata.exposure == around(0)
    assert histogram_image_metadata.vibrance == around(0)


def test_metadata_factory_text_file(tmp_path):
    text_file = tmp_path / "test.txt"
    text_file.write_text("Hello World")
    composite_metadata = FileMetadataFactory().create_metadata(text_file)
    file_metadata = composite_metadata.get(FileMetadata)
    assert isinstance(file_metadata, FileMetadata)
    assert file_metadata.checksum == "f8a5e764340d6f3e"
    assert file_metadata.path == text_file
    assert (
        file_metadata.path_with_checksum
        == text_file.parent / f"{text_file.stem}.f8a5e764340d6f3e.txt"
    )
    assert file_metadata.size == 11
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(8.7913)
    assert histogram_image_metadata.colourfulness == around(0.0591)
    assert histogram_image_metadata.contrast == around(0.00015258789)
    assert histogram_image_metadata.edge_intensity == around(0.0389)
    assert histogram_image_metadata.entropy == [around(1.587117)]
    assert histogram_image_metadata.exposure == around(25.7)
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [0.61, 0.61, 0.61]
    )
    assert histogram_image_metadata.noise == around(2071.01)
    assert histogram_image_metadata.rgb_histogram == ([65526] + [0] * 254 + [10]) * 3
    assert histogram_image_metadata.saturation_histogram == [65536] + [0] * 255
    assert histogram_image_metadata.sharpness == around(198.343)
    assert histogram_image_metadata.vibrance == around(0)


def test_metadata_factory_grayscale_image():
    composite_metadata = FileMetadataFactory().create_metadata(GRAYSCALE_IMAGE)
    image_file_metadata = composite_metadata.get(ImageFileMetadata)
    assert isinstance(image_file_metadata, ImageFileMetadata)
    image_metadata = image_file_metadata.image_metadata
    assert image_metadata.blurriness == around(6713.04)
    assert image_metadata.colourfulness == around(1.482)
    assert image_metadata.contrast == around(-0.775573)
    assert image_metadata.edge_intensity == around(25.70326)
    assert image_metadata.entropy == [around(3.0831189)]
    assert image_metadata.exposure == around(0.0428)
    assert quantiles(image_metadata.fractal_dimension) == around([1.59, 1.64, 1.66])
    assert image_metadata.height == 821
    assert image_metadata.noise == around(55.4171)
    assert quantiles(image_metadata.rgb_histogram) == around([27.0, 40.5, 73.0])
    assert image_metadata.sharpness == around(7862.592510910472)
    assert image_metadata.vibrance == around(0)
    assert image_metadata.width == 1018
    file_metadata = composite_metadata.get(FileMetadata)
    assert isinstance(file_metadata, FileMetadata)
    assert file_metadata.checksum == "94cc2cbc92ef3c0f"
    assert file_metadata.path == GRAYSCALE_IMAGE
    assert (
        file_metadata.path_with_checksum
        == GRAYSCALE_IMAGE.parent / f"{GRAYSCALE_IMAGE.stem}.94cc2cbc92ef3c0f.jpg"
    )
    assert file_metadata.size == 127620
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(8082.16)
    assert histogram_image_metadata.colourfulness == around(3.2715)
    assert histogram_image_metadata.contrast == around(-0.27)
    assert histogram_image_metadata.edge_intensity == around(11.4405)
    assert histogram_image_metadata.entropy == [around(4.1861197)]
    assert histogram_image_metadata.exposure == around(0.276155)
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [0.4932759, 0.50088119, 0.7010070]
    )
    assert histogram_image_metadata.noise == around(212.52)
    assert stdev(histogram_image_metadata.rgb_histogram) == around(1851.915599)
    assert histogram_image_metadata.sharpness == around(306.2652)
    assert histogram_image_metadata.vibrance == around(1.554)
    assert quantiles(histogram_image_metadata.rgb_histogram) == around([0, 0, 0])


def test_metadata_factory_colour_image_file():
    composite_metadata = FileMetadataFactory().create_metadata(COLOUR_IMAGE)
    image_file_metadata = composite_metadata.get(ImageFileMetadata)
    assert isinstance(image_file_metadata, ImageFileMetadata)
    image_metadata = image_file_metadata.image_metadata
    assert image_metadata.blurriness == around(4250.1335)
    assert image_metadata.colourfulness == around(44.42)
    assert image_metadata.contrast == around(0.00317)
    assert image_metadata.edge_intensity == around(7.93135)
    assert image_metadata.entropy == [around(1.278420)]
    assert image_metadata.exposure == around(0.0092)
    assert quantiles(image_metadata.fractal_dimension) == around([0.97, 1.39, 1.40])
    assert image_metadata.height == 845
    assert image_metadata.noise == around(47.467)
    assert quantiles(image_metadata.rgb_histogram) == around([5.0, 8.0, 15.0])
    assert image_metadata.sharpness == around(972.562)
    assert image_metadata.vibrance == around(28.1481)
    assert image_metadata.width == 1187
    file_metadata = composite_metadata.get(FileMetadata)
    assert isinstance(file_metadata, FileMetadata)
    assert file_metadata.checksum == "139f194152e9346c"
    assert (
        file_metadata.path_with_checksum
        == COLOUR_IMAGE.parent / f"{COLOUR_IMAGE.stem}.139f194152e9346c.png"
    )
    assert file_metadata.size == 19845
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(5532.89)
    assert histogram_image_metadata.colourfulness == around(38.30)
    assert histogram_image_metadata.contrast == around(-0.616806)
    assert histogram_image_metadata.edge_intensity == around(52.92065)
    assert histogram_image_metadata.entropy == [around(2.5157758)]
    assert histogram_image_metadata.exposure == around(0.032306)
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [0.21160032, 1.9942328, 1.9943503]
    )
    assert histogram_image_metadata.noise == around(60.22)
    assert stdev(histogram_image_metadata.rgb_histogram) == around(3309.278007)
    assert histogram_image_metadata.sharpness == around(33854.1861)
    assert histogram_image_metadata.vibrance == around(25.5633)


def test_audio_file_metadata_factory():
    composite_metadata = FileMetadataFactory().create_metadata(AUDIO_FILE)
    audio_file_metadata = composite_metadata.get(AudioFileMetadata)
    assert isinstance(audio_file_metadata, AudioFileMetadata)
    assert audio_file_metadata.duration == around(5.0)
    assert audio_file_metadata.entropy == around(1.9632)
    file_metadata = composite_metadata.get(FileMetadata)
    assert file_metadata.checksum == "b5ea61b9156ad53c"
    assert file_metadata.path == AUDIO_FILE
    assert (
        file_metadata.path_with_checksum
        == AUDIO_FILE.parent / f"{AUDIO_FILE.stem}.b5ea61b9156ad53c.mp3"
    )
    assert file_metadata.size == 80666
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(12578.6)
    assert histogram_image_metadata.colourfulness == around(6.722)
    assert histogram_image_metadata.contrast == around(-0.88142)
    assert histogram_image_metadata.edge_intensity == around(5.459)
    assert histogram_image_metadata.entropy == [around(2.2659)]
    assert histogram_image_metadata.exposure == around(1.04053)
    assert stdev(histogram_image_metadata.fractal_dimension) == around(0.51336)
    assert histogram_image_metadata.noise == around(155.79)
    assert stdev(histogram_image_metadata.rgb_histogram) == around(3677.81)
    assert stdev(histogram_image_metadata.saturation_histogram) == around(3696.289)
    assert histogram_image_metadata.sharpness == around(424.31666)
    assert histogram_image_metadata.vibrance == around(4.2072)


def test_video_file_metadata_factory_movie():
    composite_metadata = FileMetadataFactory().create_metadata(VIDEO_FILE_MOVIE)
    metadata = composite_metadata.get(VideoFileMetadata)
    assert metadata.duration == around(29.44)
    assert metadata.frame_rate == around(25)
    assert metadata.width == 352
    assert metadata.height == 288
    file_metadata = composite_metadata.get(FileMetadata)
    assert file_metadata.checksum == "2fcdd282ae3b95b6"
    assert file_metadata.path == VIDEO_FILE_MOVIE
    assert (
        file_metadata.path_with_checksum
        == VIDEO_FILE_MOVIE.parent / f"{VIDEO_FILE_MOVIE.stem}.2fcdd282ae3b95b6.mpg"
    )
    assert file_metadata.size == 2026528
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(5489.10)
    assert histogram_image_metadata.colourfulness == around(23.708)
    assert histogram_image_metadata.contrast == around(-0.001251)
    assert histogram_image_metadata.edge_intensity == around(60.44)
    assert histogram_image_metadata.entropy == [around(7.3528)]
    assert histogram_image_metadata.exposure == around(0.01902)
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [1.1784, 1.6414, 1.9437]
    )
    assert histogram_image_metadata.noise == around(28.972)
    assert quantiles(histogram_image_metadata.rgb_histogram) == around(
        [0.0, 9.0, 111.0]
    )
    assert quantiles(histogram_image_metadata.saturation_histogram) == around(
        [0.0, 0.0, 2.75]
    )
    assert histogram_image_metadata.sharpness == around(5248.40)
    assert histogram_image_metadata.vibrance == around(14.3425)


def test_video_file_metadata_factory_animation():
    composite_metadata = FileMetadataFactory().create_metadata(VIDEO_FILE_ANIMATION)
    metadata = composite_metadata.get(VideoFileMetadata)
    assert metadata.duration == around(4.96666)
    assert metadata.frame_rate == around(30)
    assert metadata.width == 190
    assert metadata.height == 240
    file_metadata = composite_metadata.get(FileMetadata)
    assert file_metadata.checksum == "7f8ad742f2d4c988"
    assert (
        file_metadata.path_with_checksum
        == VIDEO_FILE_ANIMATION.parent
        / f"{VIDEO_FILE_ANIMATION.stem}.7f8ad742f2d4c988.mp4"
    )
    assert file_metadata.size == 245779
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(5489.10)
    assert histogram_image_metadata.colourfulness == around(51.521)
    assert histogram_image_metadata.contrast == around(-0.05145)
    assert histogram_image_metadata.edge_intensity == around(72.794876)
    assert histogram_image_metadata.entropy == [around(4.8672)]
    assert histogram_image_metadata.exposure == around(0.018298)
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [0.54295, 1.7692, 1.943965]
    )
    assert histogram_image_metadata.noise == around(32.991)
    assert quantiles(histogram_image_metadata.rgb_histogram) == around([0, 0, 2.0])
    assert quantiles(histogram_image_metadata.saturation_histogram) == around([0, 0, 1])
    assert histogram_image_metadata.sharpness == around(7305.969)
    assert histogram_image_metadata.vibrance == around(34.167)


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
    metadata = file_factory.create_metadata(sample_file).get(FileMetadata)
    assert isinstance(metadata, FileMetadata)
    assert metadata.path == sample_file
    assert metadata.size == 11


def test_image_metadata():
    mock_image_adapter = MagicMock(spec=ImageAdapter)
    image = MagicMock(spec=Image)
    type(mock_image_adapter).last_size = PropertyMock(return_value=(1280, 720))
    assert mock_image_adapter.last_size == (1280, 720)

    image_metadata = ImageMetadata(
        image=image, image_adapter=mock_image_adapter, fractal_dimension=True
    )

    assert image_metadata.width == 1280
    assert image_metadata.height == 720
