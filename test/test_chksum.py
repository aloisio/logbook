from pathlib import Path
from statistics import quantiles, stdev

import pytest
from pytest import approx

from chksum import FileMetadataFactory


def test_checksum_of_empty_file(tmp_path):
    empty_file = tmp_path / 'test.txt'
    empty_file.touch()
    metadata = FileMetadataFactory().create_file_metadata(empty_file)
    assert metadata.size == 0
    assert not metadata.is_image
    assert metadata.histogram == ([256 * 256] + 255 * [0]) * 3
    assert metadata.fractal_dimension == [approx(0)] * 256
    assert metadata.entropy == approx(1.584962)
    assert metadata.path_with_checksum == tmp_path / 'test.700ccbe90581dc21.txt'


def test_checksum_of_text_file(tmp_path):
    text_file = tmp_path / 'test.txt'
    text_file.write_text('Hello World')
    metadata = FileMetadataFactory().create_file_metadata(text_file)
    assert metadata.size == 11
    assert not metadata.is_image
    assert metadata.histogram == ([65526] + [0] * 254 + [10]) * 3
    assert metadata.fractal_dimension == [approx(0.6097147)] * 255 + [approx(0)]
    assert metadata.entropy == approx(1.587117)
    assert metadata.checksum == 'f8a5e764340d6f3e'
    assert metadata.path_with_checksum == tmp_path / 'test.f8a5e764340d6f3e.txt'


def test_checksum_of_text_file_as_image_file(tmp_path):
    text_file = tmp_path / 'test.txt'
    text_file.write_text('Hello World')
    with pytest.raises(ValueError):
        FileMetadataFactory().create_image_file_metadata(FileMetadataFactory().create_file_metadata(text_file))


def test_checksum_of_greyscale_image_file():
    image_file = Path(__file__).parent / 'sierpinski.jpg'
    factory = FileMetadataFactory()
    metadata = factory.create_image_file_metadata(factory.create_file_metadata(image_file))
    assert metadata.is_image
    assert metadata.size == (1018, 821)
    assert quantiles(metadata.histogram) == [27.0, 40.5, 73.0]
    assert quantiles(metadata.fractal_dimension) == [approx(1.5880126), approx(1.643898), approx(1.660302)]
    assert metadata.entropy == approx(3.0831189)
    assert metadata.checksum == '8b75f4bc101858f0'
    assert metadata.path_with_checksum == image_file.parent / 'sierpinski.8b75f4bc101858f0.jpg'


def test_checksum_of_greyscale_image_file_as_file():
    image_file = Path(__file__).parent / 'sierpinski.jpg'
    metadata = FileMetadataFactory().create_file_metadata(image_file)
    assert metadata.size == 127620
    assert stdev(metadata.histogram) == approx(1851.915599)
    assert quantiles(metadata.fractal_dimension) == list(map(approx, [0.4932759, 0.50088119, 0.7010070]))
    assert metadata.is_image
    assert quantiles(metadata.histogram) == [0, 0, 0]
    assert metadata.entropy == approx(4.1861197)
    assert metadata.checksum == '8b75f4bc101858f0'
    assert metadata.path_with_checksum == image_file.parent / 'sierpinski.8b75f4bc101858f0.jpg'


def test_checksum_of_colour_image_file():
    image_file = Path(__file__).parent / 'brazil.png'
    metadata = FileMetadataFactory().create_image_file_metadata(FileMetadataFactory().create_file_metadata(image_file))
    assert metadata.is_image
    assert metadata.size == (1187, 845)
    assert quantiles(metadata.histogram) == [5.0, 8.0, 15.0]
    assert quantiles(metadata.fractal_dimension) == list(map(approx, [0.99072488, 1.389666, 1.402276]))
    assert metadata.entropy == approx(1.278420)
    assert metadata.checksum == '65ba3ca674200803'
    assert metadata.path_with_checksum == image_file.parent / 'brazil.65ba3ca674200803.png'


def test_checksum_of_colour_image_file_as_file():
    image_file = Path(__file__).parent / 'brazil.png'
    metadata = FileMetadataFactory().create_file_metadata(image_file)
    assert metadata.size == 19845
    assert stdev(metadata.histogram) == approx(3309.278007)
    assert quantiles(metadata.fractal_dimension) == list(map(approx, [0.21160032, 1.9942328, 1.9943503]))
    assert metadata.is_image
    assert metadata.entropy == approx(2.5157758)
    assert metadata.checksum == '65ba3ca674200803'
    assert metadata.path_with_checksum == image_file.parent / 'brazil.65ba3ca674200803.png'
