from functools import partial
from pathlib import Path
from statistics import quantiles, stdev
from unittest.mock import MagicMock, PropertyMock
from unittest.mock import Mock

import numpy as np
import pytest
from numpy.testing import assert_array_equal
from pytest import approx

from adapter import (
    AudioAdapter,
    VideoAdapter,
    ImageAdapter,
    Image,
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
ONE_PIXEL_IMAGE = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAA1JREFUGFdjYGBg+"
    "A8AAQQBAHAgZQsAAAAASUVORK5CYII="
)

around = partial(approx, rel=0.01)


def test_vector():
    # Define mock ImageAdapter object
    mock_adapter = Mock(spec=ImageAdapter)
    mock_adapter.to_grayscale.return_value = Mock()
    mock_adapter.quadrants.return_value = (Mock(), Mock(), Mock(), Mock())
    mock_adapter.rgb_histogram.return_value = [1, 2, 3]
    mock_adapter.entropy.return_value = 11.0
    mock_adapter.contrast.return_value = 1.0
    mock_adapter.saturation_histogram.return_value = [4, 5, 6]
    mock_adapter.edge_intensity.return_value = 2.0
    mock_adapter.colourfulness.return_value = 3.0
    mock_adapter.sharpness.return_value = 4.0
    mock_adapter.blurriness.return_value = 5.0
    mock_adapter.exposure.return_value = 6.0
    mock_adapter.vibrance.return_value = 7.0
    mock_adapter.noise.return_value = 8.0
    mock_adapter.fractal_dimension.return_value = [9.0, 10.0]

    # Define input arguments for ImageMetadata object
    image = DefaultImageAdapter().from_data_url(ONE_PIXEL_IMAGE)
    metadata_args = {
        "image": image,
        "image_adapter": mock_adapter,
        "fractal_dimension": True,
    }

    # Create ImageMetadata object and verify vector
    metadata = ImageMetadata(**metadata_args)
    expected_vector = np.array(
        [
            1,
            1,
            *[1, 2, 3],
            *[11, 11, 11, 11, 11],
            *[1, 1, 1, 1, 1],
            *[4, 5, 6],
            *[2, 2, 2, 2, 2],
            *[3, 3, 3, 3, 3],
            *[4, 4, 4, 4, 4],
            *[5, 5, 5, 5, 5],
            *[6, 6, 6, 6, 6],
            *[7, 7, 7, 7, 7],
            *[8, 8, 8, 8, 8],
            *[9, 10],
        ]
    )
    assert_array_equal(metadata.vector, expected_vector)


def test_vector_without_fractal_dimension():
    image = DefaultImageAdapter().from_data_url(ONE_PIXEL_IMAGE)
    metadata_args = {
        "image": image,
        "image_adapter": DefaultImageAdapter(),
        "fractal_dimension": False,
    }

    # Create ImageMetadata object and verify vector
    metadata = ImageMetadata(**metadata_args)
    assert metadata.vector.size == 1071


def test_audio_file_metadata():
    path = Path("/examples/audio.wav")
    duration = 13.33
    entropy = 0.87
    mock_audio_adapter = MagicMock(spec=AudioAdapter)
    mock_audio_adapter.metrics.return_value = AudioAdapter.Metrics(
        duration=duration, entropy=entropy
    )

    audio_file_metadata = AudioFileMetadata(path, mock_audio_adapter)

    assert audio_file_metadata.duration == duration
    assert audio_file_metadata.entropy == 0.87
    mock_audio_adapter.metrics.assert_called_once_with(path)


def test_composite_metadata():
    existing_file_metadata = FileMetadata(GRAYSCALE_IMAGE, DefaultImageAdapter())
    new_file_metadata = FileMetadata(GRAYSCALE_IMAGE, DefaultImageAdapter())
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
    assert file_metadata.checksum == "cae66941d9efbd404e4d88758ea67670"
    assert file_metadata.path == empty_file
    assert (
        file_metadata.path_with_checksum
        == empty_file.parent / f"{empty_file.stem}.cae66941d9efbd404e4d88758ea67670.txt"
    )
    assert file_metadata.size == 0
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.rgb_histogram == ([256 * 256] + 255 * [0]) * 3
    assert quantiles(histogram_image_metadata.fractal_dimension) == around([0, 0, 0])
    assert histogram_image_metadata.entropy == around([1.584962] * 5)
    assert histogram_image_metadata.contrast == around([0] * 5)
    assert histogram_image_metadata.saturation_histogram == [65536] + [0] * 255
    assert histogram_image_metadata.edge_intensity == around([0] * 5)
    assert histogram_image_metadata.colourfulness == around([0] * 5)
    assert histogram_image_metadata.sharpness == around([0] * 5)
    assert histogram_image_metadata.blurriness == around([0] * 5)
    assert histogram_image_metadata.noise == around([0] * 5)
    assert histogram_image_metadata.exposure == around([0] * 5)
    assert histogram_image_metadata.vibrance == around([0] * 5)


def test_metadata_factory_text_file(tmp_path):
    text_file = tmp_path / "test.txt"
    text_file.write_text("Hello World")
    composite_metadata = FileMetadataFactory().create_metadata(text_file)
    file_metadata = composite_metadata.get(FileMetadata)
    assert isinstance(file_metadata, FileMetadata)
    assert file_metadata.checksum == "0cc84ab57c476d2385b899ca742a2790"
    assert file_metadata.path == text_file
    assert (
        file_metadata.path_with_checksum
        == text_file.parent / f"{text_file.stem}.0cc84ab57c476d2385b899ca742a2790.txt"
    )
    assert file_metadata.size == 11
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around([8.7913, 35.147, 0, 0, 0])
    assert histogram_image_metadata.colourfulness == around(
        [0.0591767867482153, 0.1183535734964306, 0.0, 0.0, 0.0]
    )
    assert histogram_image_metadata.contrast == around(
        [0.000152, 0.000610, 0.0, 0.0, 0.0]
    )
    assert histogram_image_metadata.edge_intensity == around(
        [0.0389, 0.155, 0.0, 0.0, 0.0]
    )
    assert histogram_image_metadata.entropy == around(
        [1.587, 1.592, 1.585, 1.585, 1.585]
    )
    assert histogram_image_metadata.exposure == around([25.7, 6.425, 0, 0, 0])
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [0.61, 0.61, 0.61]
    )
    assert histogram_image_metadata.noise == around([2071.01, 516.72, 0, 0, 0])
    assert histogram_image_metadata.rgb_histogram == ([65526] + [0] * 254 + [10]) * 3
    assert histogram_image_metadata.saturation_histogram == [65536] + [0] * 255
    assert histogram_image_metadata.sharpness == around([198.3, 792.2, 0.0, 0.0, 0.0])
    assert histogram_image_metadata.vibrance == around([0] * 5)


def test_metadata_factory_grayscale_image():
    composite_metadata = FileMetadataFactory().create_metadata(GRAYSCALE_IMAGE)
    image_file_metadata = composite_metadata.get(ImageFileMetadata)
    assert isinstance(image_file_metadata, ImageFileMetadata)
    image_metadata = image_file_metadata.image_metadata
    assert image_metadata.blurriness == around(
        [6713.04, 5103.49, 4882.61, 7993.09, 7861.69]
    )
    assert image_metadata.colourfulness == around([1.482, 1.208, 1.207, 1.709, 1.715])
    assert image_metadata.contrast == around([-0.775, -0.844, -0.849, -0.699, -0.708])
    assert image_metadata.edge_intensity == around([25.70, 15.17, 16.07, 34.72, 36.01])
    assert image_metadata.entropy == around([3.917, 3.244, 3.200, 4.583, 4.444])
    assert image_metadata.exposure == around([0.0428, 0.0644, 0.0645, 0.0321, 0.0319])
    assert quantiles(image_metadata.fractal_dimension) == around([1.59, 1.64, 1.66])
    assert image_metadata.height == 821
    assert image_metadata.noise == around([55.417, 46.385, 46.077, 62.678, 61.995])
    assert quantiles(image_metadata.rgb_histogram) == around([27.0, 40.5, 73.0])
    assert image_metadata.sharpness == around([7862.5, 6059.8, 4965.3, 11665.7, 7956.0])
    assert image_metadata.vibrance == around([0] * 5)
    assert image_metadata.width == 1018
    file_metadata = composite_metadata.get(FileMetadata)
    assert isinstance(file_metadata, FileMetadata)
    assert file_metadata.checksum == "ff6a4ce58da125c968e0eb74d64160dc"
    assert file_metadata.path == GRAYSCALE_IMAGE
    assert (
        file_metadata.path_with_checksum
        == GRAYSCALE_IMAGE.parent
        / f"{GRAYSCALE_IMAGE.stem}.ff6a4ce58da125c968e0eb74d64160dc.jpg"
    )
    assert file_metadata.size == 127620
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(
        [8082.160, 8016.943, 8035.965, 8173.517, 8168.495]
    )
    assert histogram_image_metadata.colourfulness == around(
        [3.2715, 3.5368, 3.2100, 3.2600, 3.0587]
    )
    assert histogram_image_metadata.contrast == around(
        [-0.269, -0.271, -0.260, -0.275, -0.274]
    )
    assert histogram_image_metadata.edge_intensity == around(
        [11.440, 11.492, 11.176, 11.302, 11.141]
    )
    assert histogram_image_metadata.entropy == around(
        [4.186, 4.204, 4.192, 4.172, 4.167]
    )
    assert histogram_image_metadata.exposure == around(
        [0.2761, 0.2660, 0.2749, 0.2808, 0.2833]
    )
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [0.4932759, 0.50088119, 0.7010070]
    )
    assert histogram_image_metadata.noise == around(
        [212.52, 99.43, 25.66, 63.44, 61.71]
    )
    assert stdev(histogram_image_metadata.rgb_histogram) == around(1851.915599)
    assert histogram_image_metadata.sharpness == around(
        [306.2, 626.0, 175.2, 226.8, 191.6]
    )
    assert histogram_image_metadata.vibrance == around(
        [1.553, 1.686, 1.496, 1.600, 1.398]
    )
    assert quantiles(histogram_image_metadata.rgb_histogram) == around([0, 0, 0])


def test_metadata_factory_colour_image_file():
    composite_metadata = FileMetadataFactory().create_metadata(COLOUR_IMAGE)
    image_file_metadata = composite_metadata.get(ImageFileMetadata)
    assert isinstance(image_file_metadata, ImageFileMetadata)
    image_metadata = image_file_metadata.image_metadata
    assert image_metadata.blurriness == around(
        [4250.13, 3978.46, 4441.19, 3873.40, 4730.39]
    )
    assert image_metadata.colourfulness == around(
        [44.422, 44.417, 44.399, 44.877, 43.971]
    )
    assert image_metadata.contrast == around(
        [0.0031738, -0.0007934, 0.0045166, -0.0003051, 0.0033569]
    )
    assert image_metadata.edge_intensity == around([7.931, 10.602, 9.788, 8.675, 9.532])
    assert image_metadata.entropy == around([3.557, 3.578, 3.548, 3.429, 3.574])
    assert image_metadata.exposure == around(
        [0.00928, 0.00912, 0.00924, 0.00947, 0.00931]
    )
    assert quantiles(image_metadata.fractal_dimension) == around([0.97, 1.39, 1.40])
    assert image_metadata.height == 845
    assert image_metadata.noise == around([47.46, 78.81, 77.44, 75.94, 76.86])
    assert quantiles(image_metadata.rgb_histogram) == around([5.0, 8.0, 15.0])
    assert image_metadata.sharpness == around([972.5, 1258.1, 1603.1, 883.3, 1388.4])
    assert image_metadata.vibrance == around([28.14, 28.14, 28.12, 28.44, 27.85])
    assert image_metadata.width == 1187
    file_metadata = composite_metadata.get(FileMetadata)
    assert isinstance(file_metadata, FileMetadata)
    assert file_metadata.checksum == "fc3649e778f180bb3c13f85c3710cc62"
    assert (
        file_metadata.path_with_checksum
        == COLOUR_IMAGE.parent
        / f"{COLOUR_IMAGE.stem}.fc3649e778f180bb3c13f85c3710cc62.png"
    )
    assert file_metadata.size == 19845
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(
        [5532.89, 5499.30, 5598.42, 5500.00, 5550.48]
    )
    assert histogram_image_metadata.colourfulness == around(
        [38.304, 39.495, 38.053, 37.891, 37.700]
    )
    assert histogram_image_metadata.contrast == around(
        [-0.616, -0.579, -0.624, -0.628, -0.634]
    )
    assert histogram_image_metadata.edge_intensity == around(
        [52.92, 59.08, 51.23, 50.74, 49.60]
    )
    assert histogram_image_metadata.entropy == around(
        [2.515, 2.650, 2.478, 2.476, 2.445]
    )
    assert histogram_image_metadata.exposure == around(
        [0.0323, 0.0288, 0.0332, 0.0335, 0.0342]
    )
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [0.21160032, 1.9942328, 1.9943503]
    )
    assert histogram_image_metadata.noise == around([60.22, 65.72, 61.63, 61.44, 60.80])
    assert stdev(histogram_image_metadata.rgb_histogram) == around(3309.278007)
    assert histogram_image_metadata.sharpness == around(
        [33854.1, 33352.4, 34037.0, 33959.1, 34099.3]
    )
    assert histogram_image_metadata.vibrance == around(
        [25.56, 26.32, 25.40, 25.29, 25.17]
    )


def test_audio_file_metadata_factory():
    composite_metadata = FileMetadataFactory().create_metadata(AUDIO_FILE)
    audio_file_metadata = composite_metadata.get(AudioFileMetadata)
    assert isinstance(audio_file_metadata, AudioFileMetadata)
    assert audio_file_metadata.duration == around(5.0)
    assert audio_file_metadata.entropy == around(1.9632340669631958)
    file_metadata = composite_metadata.get(FileMetadata)
    assert file_metadata.checksum == "cce974fae4db6a85015d4d71684847cd"
    assert file_metadata.path == AUDIO_FILE
    assert (
        file_metadata.path_with_checksum
        == AUDIO_FILE.parent / f"{AUDIO_FILE.stem}.cce974fae4db6a85015d4d71684847cd.mp3"
    )
    assert file_metadata.size == 80666
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(
        [12578.6, 10677.7, 12783.4, 12831.6, 13689.6]
    )
    assert histogram_image_metadata.colourfulness == around(
        [6.722, 8.204, 6.192, 6.475, 5.695]
    )
    assert histogram_image_metadata.contrast == around(
        [-0.881, -0.846, -0.887, -0.889, -0.911]
    )
    assert histogram_image_metadata.edge_intensity == around(
        [5.459, 7.639, 4.902, 4.947, 3.795]
    )
    assert histogram_image_metadata.entropy == around(
        [2.265, 2.454, 2.232, 2.224, 2.124]
    )
    assert histogram_image_metadata.exposure == around(
        [1.040, 0.733, 1.157, 1.143, 1.345]
    )
    assert stdev(histogram_image_metadata.fractal_dimension) == around(0.51336)
    assert histogram_image_metadata.noise == around(
        [155.79, 41.89, 59.32, 73.18, 102.37]
    )
    assert stdev(histogram_image_metadata.rgb_histogram) == around(3677.81)
    assert stdev(histogram_image_metadata.saturation_histogram) == around(3696.289)
    assert histogram_image_metadata.sharpness == around(
        [424.3, 541.4, 306.2, 369.0, 470.0]
    )
    assert histogram_image_metadata.vibrance == around(
        [4.207, 5.133, 3.840, 4.056, 3.598]
    )


def test_video_file_metadata_factory_movie():
    composite_metadata = FileMetadataFactory().create_metadata(VIDEO_FILE_MOVIE)
    metadata = composite_metadata.get(VideoFileMetadata)
    assert metadata.duration == around(29.44)
    assert metadata.frame_rate == around(25)
    assert metadata.width == 352
    assert metadata.height == 288
    file_metadata = composite_metadata.get(FileMetadata)
    assert file_metadata.checksum == "af8b3d993439c694cc7bd52dfaca1183"
    assert file_metadata.path == VIDEO_FILE_MOVIE
    assert (
        file_metadata.path_with_checksum
        == VIDEO_FILE_MOVIE.parent
        / f"{VIDEO_FILE_MOVIE.stem}.af8b3d993439c694cc7bd52dfaca1183.mpg"
    )
    assert file_metadata.size == 2026528
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(
        [5489.10, 5519.67, 5481.07, 5484.44, 5462.82]
    )
    assert histogram_image_metadata.colourfulness == around(
        [23.707, 24.302, 23.926, 23.372, 23.190]
    )
    assert histogram_image_metadata.contrast == around(
        [-0.0012512, -0.0027465, 0.0003662, -0.0028076, -0.0055541]
    )
    assert histogram_image_metadata.edge_intensity == around(
        [60.439, 62.289, 59.293, 60.423, 58.409]
    )
    assert histogram_image_metadata.entropy == around(
        [7.352, 7.386, 7.337, 7.335, 7.321]
    )
    assert histogram_image_metadata.exposure == around(
        [0.01902, 0.01901, 0.01912, 0.01912, 0.01881]
    )
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [1.1784, 1.6414, 1.9437]
    )
    assert histogram_image_metadata.noise == around([28.97, 47.57, 46.61, 46.61, 46.74])
    assert quantiles(histogram_image_metadata.rgb_histogram) == around(
        [0.0, 9.0, 111.0]
    )
    assert quantiles(histogram_image_metadata.saturation_histogram) == around(
        [0.0, 0.0, 2.75]
    )
    assert histogram_image_metadata.sharpness == around(
        [5248.3, 5766.9, 5053.5, 5601.9, 4633.7]
    )
    assert histogram_image_metadata.vibrance == around(
        [14.34, 14.74, 14.50, 14.13, 13.95]
    )


def test_video_file_metadata_factory_animation():
    composite_metadata = FileMetadataFactory().create_metadata(VIDEO_FILE_ANIMATION)
    metadata = composite_metadata.get(VideoFileMetadata)
    assert metadata.duration == around(4.96666)
    assert metadata.frame_rate == around(30)
    assert metadata.width == 190
    assert metadata.height == 240
    file_metadata = composite_metadata.get(FileMetadata)
    assert file_metadata.checksum == "f664036f4e48430959ecd887194629f0"
    assert (
        file_metadata.path_with_checksum
        == VIDEO_FILE_ANIMATION.parent
        / f"{VIDEO_FILE_ANIMATION.stem}.f664036f4e48430959ecd887194629f0.mp4"
    )
    assert file_metadata.size == 245779
    histogram_image_metadata = file_metadata.histogram_image_metadata
    assert histogram_image_metadata.blurriness == around(
        [5434.26, 5436.27, 5484.63, 5418.03, 5400.01]
    )
    assert histogram_image_metadata.colourfulness == around(
        [51.521, 51.894, 51.180, 51.689, 51.222]
    )
    assert histogram_image_metadata.contrast == around(
        [-0.0514, -0.0491, -0.0548, -0.0551, -0.0606]
    )
    assert histogram_image_metadata.edge_intensity == around(
        [72.794, 74.764, 72.319, 71.538, 71.151]
    )
    assert histogram_image_metadata.entropy == around(
        [4.867, 4.997, 4.826, 4.841, 4.777]
    )
    assert histogram_image_metadata.exposure == around(
        [0.0182, 0.0173, 0.0184, 0.0184, 0.0189]
    )
    assert quantiles(histogram_image_metadata.fractal_dimension) == around(
        [0.54295, 1.7692, 1.943965]
    )
    assert histogram_image_metadata.noise == around([32.99, 67.81, 66.38, 66.81, 66.28])
    assert quantiles(histogram_image_metadata.rgb_histogram) == around([0, 0, 2.0])
    assert quantiles(histogram_image_metadata.saturation_histogram) == around([0, 0, 1])
    assert histogram_image_metadata.sharpness == around(
        [7305.9, 7768.2, 7056.6, 7438.5, 7153.3]
    )
    assert histogram_image_metadata.vibrance == around(
        [34.16, 34.40, 33.92, 34.28, 33.97]
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
    metadata = file_factory.create_metadata(sample_file).get(FileMetadata)
    assert isinstance(metadata, FileMetadata)
    assert metadata.path == sample_file
    assert metadata.size == 11


def test_image_metadata():
    mock_image_adapter = MagicMock(spec=ImageAdapter)
    mock_image = MagicMock(spec=Image)
    mock_image.size.return_value = (800, 600)
    type(mock_image).size = PropertyMock(return_value=(800, 600))
    assert mock_image.size == (800, 600)

    image_metadata = ImageMetadata(
        image=mock_image, image_adapter=mock_image_adapter, fractal_dimension=True
    )

    assert image_metadata.width == 800
    assert image_metadata.height == 600
