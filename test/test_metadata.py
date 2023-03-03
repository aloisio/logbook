from pathlib import Path
from unittest.mock import MagicMock

from pytest import approx

from metadata import AudioFileMetadata, FileMetadataFactory


def test_audio_file_metadata():
    path = Path("/examples/audio.wav")
    duration = 13.33
    mock_audio_adapter = MagicMock()
    mock_audio_adapter.duration.return_value = duration

    audio_file_metadata = AudioFileMetadata(path, mock_audio_adapter)

    assert audio_file_metadata.duration == duration
    mock_audio_adapter.duration.assert_called_once_with(path)


def test_audio_file_metadata_factory():
    path = Path(__file__).parent / "100Hz_44100Hz_16bit_05sec.mp3"
    audio_file_metadata = FileMetadataFactory().create_metadata(path)[AudioFileMetadata]
    assert isinstance(audio_file_metadata, AudioFileMetadata)
    assert audio_file_metadata.duration == approx(5.0, 0.01)
