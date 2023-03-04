from pathlib import Path
from unittest.mock import MagicMock

from pytest import approx

from adapters import AudioAdapter, ImageAdapter
from metadata import AudioFileMetadata, FileMetadataFactory, Metadata, FileMetadata


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
    audio_file_metadata = FileMetadataFactory().create_metadata(path)[AudioFileMetadata]
    assert isinstance(audio_file_metadata, AudioFileMetadata)
    assert audio_file_metadata.duration == approx(5.0, 0.01)
    assert audio_file_metadata.entropy == approx(1.9632, 0.0001)


class CompositeMetadata(Metadata):
    def __init__(self, **metadata: Metadata):
        for key, value in metadata.items():
            setattr(self, key, value)


def test_composite_metadata():
    path = Path(__file__).parent / "100Hz_44100Hz_16bit_05sec.mp3"
    file_metadata = FileMetadata(path, MagicMock(autospec=ImageAdapter))
    metadata = CompositeMetadata(**{FileMetadata.__name__: file_metadata})
    assert type(metadata.FileMetadata) == FileMetadata
    assert metadata.FileMetadata == file_metadata
    assert not hasattr(metadata, "AudioFileMetadata")
    mock_audio_adapter = MagicMock(autospec=AudioAdapter)
    mock_audio_adapter.duration.return_value = 5
    audio_file_metadata = AudioFileMetadata(path, mock_audio_adapter)
    metadata = CompositeMetadata(
        **{
            FileMetadata.__name__: file_metadata,
            AudioFileMetadata.__name__: audio_file_metadata,
        },
    )
    assert metadata.FileMetadata.size == 80666
    assert type(metadata.FileMetadata) == FileMetadata
    assert metadata.FileMetadata == file_metadata
    assert type(metadata.AudioFileMetadata) == AudioFileMetadata
    assert metadata.AudioFileMetadata == audio_file_metadata
    assert metadata.AudioFileMetadata.duration == 5
