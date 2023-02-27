import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chksum import FileMetadataFactory, FileMetadata, ImageFileMetadata, Metadata


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
    metadata = file_factory.create_file_metadata(sample_file)
    assert metadata.path == sample_file
    assert metadata.size == 11


def test_create_file_metadata():
    mock_image_adapter = MagicMock()
    file_path = Path('/path/to/file.txt')

    with patch('src.chksum.ImageAdapter', return_value=mock_image_adapter):
        file_metadata = FileMetadataFactory(mock_image_adapter).create_file_metadata(file_path)

    assert isinstance(file_metadata, FileMetadata)
    assert file_metadata.path == file_path
    assert file_metadata._image_adapter == mock_image_adapter


def test_image_file_metadata():
    image_adapter = MagicMock()
    path = Path('/path/to/image.jpg')
    file_metadata = ImageFileMetadata(FileMetadata(path, image_adapter), image_adapter)

    assert file_metadata.path == path
    assert file_metadata._image_adapter == image_adapter

def test_image_file_metadata_fails_with_non_image_path():
    factory = FileMetadataFactory()
    with tempfile.TemporaryDirectory() as tmpdir:
        # create a non-image file in the temporary directory
        non_image_file = Path(tmpdir) / "not_an_image.txt"
        non_image_file.write_text("this is not an image")
        # make sure ImageFileMetadata fails when given the non-image file
        with pytest.raises(ValueError):
            factory.create_image_file_metadata(factory.create_file_metadata(non_image_file))