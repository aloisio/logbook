from pathlib import Path
from unittest.mock import MagicMock

from pytest import approx

from adapters import AudioAdapter, ImageAdapter
from metadata import (
    AudioFileMetadata,
    FileMetadataFactory,
    FileMetadata,
    MetadataAggregate,
    CompositeMetadata,
)


def test_audio_file_metadata():
    path = Path("/examples/audio.wav")
    duration = 13.33
    entropy = 0.87
    mock_audio_adapter = MagicMock()
    mock_audio_adapter.duration.return_value = duration
    mock_audio_adapter.entropy.return_value = entropy

    audio_file_metadata = AudioFileMetadata(path, mock_audio_adapter)

    assert audio_file_metadata.duration == duration
    assert audio_file_metadata.entropy == 0.87
    mock_audio_adapter.duration.assert_called_once_with(path)
    mock_audio_adapter.entropy.assert_called_once_with(path)


def test_audio_file_metadata_factory():
    path = Path(__file__).parent / "100Hz_44100Hz_16bit_05sec.mp3"
    audio_file_metadata = (
        FileMetadataFactory().create_metadata(path).metadata(AudioFileMetadata)
    )
    assert isinstance(audio_file_metadata, AudioFileMetadata)
    assert audio_file_metadata.duration == approx(5.0, 0.01)
    assert audio_file_metadata.entropy == approx(1.9632, 0.0001)


def test_metadata_aggregate():
    path = Path(__file__).parent / "100Hz_44100Hz_16bit_05sec.mp3"
    file_metadata = FileMetadata(path, MagicMock(spec=ImageAdapter))
    metadata = MetadataAggregate(FileMetadata=file_metadata)
    assert type(metadata["FileMetadata"]) == FileMetadata
    assert metadata["FileMetadata"] == file_metadata
    assert "AudioFileMetadata" not in metadata
    mock_audio_adapter = MagicMock(autospec=AudioAdapter)
    mock_audio_adapter.duration.return_value = 5
    audio_file_metadata = AudioFileMetadata(path, mock_audio_adapter)
    metadata = MetadataAggregate(
        FileMetadata=file_metadata, AudioFileMetadata=audio_file_metadata
    )
    assert metadata["FileMetadata"].size == 80666
    assert type(metadata["FileMetadata"]) == FileMetadata
    assert metadata["FileMetadata"] == file_metadata
    assert type(metadata["AudioFileMetadata"]) == AudioFileMetadata
    assert metadata["AudioFileMetadata"] == audio_file_metadata
    assert metadata["AudioFileMetadata"].duration == 5


def test_composite_metadata():
    mock_file_metadata = FileMetadata(MagicMock(), MagicMock())
    mock_audio_file_metadata = AudioFileMetadata(MagicMock(), MagicMock())
    type(mock_file_metadata).return_value = FileMetadata
    type(mock_audio_file_metadata).return_value = AudioFileMetadata
    metadata = CompositeMetadata(
        MetadataAggregate(
            FileMetadata=mock_file_metadata, AudioFileMetadata=mock_audio_file_metadata
        )
    )
    assert type(metadata.metadata(FileMetadata)) == FileMetadata
