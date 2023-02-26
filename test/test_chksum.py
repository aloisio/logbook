from pathlib import Path
from statistics import quantiles, stdev

from pytest import approx

from chksum import FileMetadata


def test_checksum_of_empty_file(tmp_path):
    empty_file = tmp_path / 'test.txt'
    empty_file.touch()
    metadata = FileMetadata(empty_file)
    assert metadata.file_size == 0
    assert not metadata.is_image
    assert metadata.image_histogram is None
    assert metadata.byte_histogram == ([256 * 256] + 255 * [0]) * 3
    assert metadata.byte_fractal_dimension == [approx(0)] * 256
    assert metadata.byte_entropy == approx(1.584962)
    assert metadata.path_with_checksum == tmp_path / 'test.700ccbe90581dc21.txt'


def test_checksum_of_text_file(tmp_path):
    text_file = tmp_path / 'test.txt'
    text_file.write_text('Hello World')
    metadata = FileMetadata(text_file)
    assert metadata.file_size == 11
    assert not metadata.is_image
    assert metadata.image_histogram is None
    assert metadata.byte_histogram == ([65526] + [0] * 254 + [10]) * 3
    assert metadata.byte_fractal_dimension == [approx(0.6097147)] * 255 + [approx(0)]
    assert metadata.byte_entropy == approx(1.587117)
    assert metadata.checksum == 'f8a5e764340d6f3e'
    assert metadata.path_with_checksum == tmp_path / 'test.f8a5e764340d6f3e.txt'


def test_checksum_of_greyscale_image_file():
    image_file = Path('sierpinski.jpg')
    metadata = FileMetadata(image_file)
    assert metadata.file_size == 127620
    assert stdev(metadata.byte_histogram) == approx(1851.915599)
    assert quantiles(metadata.byte_fractal_dimension) == list(map(approx, [0.4932759, 0.50088119, 0.7010070]))
    assert metadata.is_image
    assert metadata.image_size == (1018, 821)
    assert quantiles(metadata.byte_histogram) == [0, 0, 0]
    assert quantiles(metadata.image_histogram) == [27.0, 40.5, 73.0]
    assert quantiles(metadata.image_fractal_dimension) == [approx(1.5880126), approx(1.643898), approx(1.660302)]
    assert metadata.byte_entropy == approx(4.1861197)
    assert metadata.image_entropy == approx(3.0831189)
    assert metadata.checksum == '8b75f4bc101858f0'
    assert metadata.path_with_checksum == image_file.parent / 'sierpinski.8b75f4bc101858f0.jpg'


def test_checksum_of_colour_image_file():
    image_file = Path('brazil.png')
    metadata = FileMetadata(image_file)
    assert metadata.file_size == 19845
    assert stdev(metadata.byte_histogram) == approx(3309.278007)
    assert quantiles(metadata.byte_fractal_dimension) == list(map(approx, [0.21160032, 1.9942328, 1.9943503]))
    assert metadata.is_image
    assert metadata.image_size == (1187, 845)
    assert quantiles(metadata.image_histogram) == [5.0, 8.0, 15.0]
    assert quantiles(metadata.image_fractal_dimension) == list(map(approx, [0.99072488, 1.389666, 1.402276]))
    assert metadata.byte_entropy == approx(2.5157758)
    assert metadata.image_entropy == approx(1.278420)
    assert metadata.checksum == '65ba3ca674200803'
    assert metadata.path_with_checksum == image_file.parent / 'brazil.65ba3ca674200803.png'
