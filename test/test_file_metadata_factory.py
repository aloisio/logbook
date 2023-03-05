from pathlib import Path
from unittest.mock import MagicMock

import pytest

from metadata import (
    FileMetadata,
    ImageFileMetadata,
    FileMetadataFactory,
)

FIXTURES = Path(__file__).parent / "fixtures"


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


def test_create_file_metadata():
    mock_image_adapter = MagicMock()
    mock_file_type_adapter = MagicMock()
    file_path = Path(FIXTURES / "sierpinski.jpg")
    mock_image_adapter.is_image.return_value = True
    factory = FileMetadataFactory(
        image_adapter=mock_image_adapter, file_type_adapter=mock_file_type_adapter
    )
    metadata = factory.create_metadata(file_path).metadata(ImageFileMetadata)
    assert isinstance(metadata, ImageFileMetadata)
    assert metadata.path == file_path
    assert metadata._image_adapter == mock_image_adapter


def test_image_file_metadata():
    image_adapter = MagicMock()
    path = Path(FIXTURES / "sierpinski.jpg")
    file_metadata = ImageFileMetadata(path, image_adapter)

    assert file_metadata.path == path
    assert file_metadata._image_adapter == image_adapter
