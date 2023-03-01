from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

from pytest import approx

from metadata import AudioFileMetadata, FileMetadataFactory


def test_audio_file_metadata():
    path = Path('/examples/audio.wav')
    checksum = 'bebacafe'
    duration = 13.33
    mock_audio_adapter = MagicMock()
    mock_audio_adapter.duration.return_value = duration
    mock_file_metadata = MagicMock()
    type(mock_file_metadata).path = PropertyMock(return_value=path)
    type(mock_file_metadata).path_with_checksum = PropertyMock(return_value=path)
    type(mock_file_metadata).checksum = PropertyMock(return_value=checksum)
    type(mock_file_metadata).size = PropertyMock(return_value=duration)

    audio_file_metadata = AudioFileMetadata(mock_file_metadata, mock_audio_adapter)

    assert audio_file_metadata.path == path
    assert audio_file_metadata.path_with_checksum == path
    assert audio_file_metadata.checksum == checksum
    assert audio_file_metadata.size == duration
    assert audio_file_metadata.metadata == [mock_file_metadata]
    mock_audio_adapter.duration.assert_called_once_with(path)


def test_audio_file_metadata_factory():
    path = Path(__file__).parent / '100Hz_44100Hz_16bit_05sec.mp3'
    audio_file_metadata = FileMetadataFactory().create_file_metadata(path)
    assert isinstance(audio_file_metadata, AudioFileMetadata)
    assert audio_file_metadata.size == approx(5.0, 0.01)
