from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest import approx

from adapters import AudioAdapter, VideoAdapter
from metadata import (
    AudioFileMetadata,
    FileMetadataFactory,
    FileMetadata,
    CompositeMetadata,
    VideoFileMetadata,
)

FIXTURES = Path(__file__).parent / "fixtures"
AUDIO_FILE = FIXTURES / "100Hz_44100Hz_16bit_05sec.mp3"
VIDEO_FILE = FIXTURES / "valid.mp4"


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


def test_audio_file_metadata_factory():
    path = AUDIO_FILE
    audio_file_metadata = (
        FileMetadataFactory().create_metadata(path).metadata(AudioFileMetadata)
    )
    assert isinstance(audio_file_metadata, AudioFileMetadata)
    assert audio_file_metadata.duration == approx(5.0, 0.01)
    assert audio_file_metadata.entropy == approx(1.9632, 0.0001)


def test_composite_metadata():
    existing_file_metadata = FileMetadata(MagicMock(), MagicMock(), MagicMock())
    new_file_metadata = FileMetadata(MagicMock(), MagicMock(), MagicMock())
    audio_file_metadata = AudioFileMetadata(MagicMock(), MagicMock())

    composite_metadata = CompositeMetadata(existing_file_metadata)

    composite_metadata.add(audio_file_metadata)
    with pytest.raises(ValueError):
        # noinspection PyTypeChecker
        composite_metadata.add("33")
    with pytest.raises(ValueError):
        composite_metadata.add(new_file_metadata)
    composite_metadata.add(new_file_metadata, overwrite=True)
    assert composite_metadata.metadata(FileMetadata) is new_file_metadata
    composite_metadata.add(existing_file_metadata, overwrite=True)
    assert type(composite_metadata.metadata(FileMetadata)) == FileMetadata
    assert composite_metadata.metadata(FileMetadata) == existing_file_metadata
    assert composite_metadata.metadata(AudioFileMetadata) == audio_file_metadata
    assert list(composite_metadata.children) == [
        existing_file_metadata,
        audio_file_metadata,
    ]


def test_video_file_metadata():
    mock_video_adapter = MagicMock(spec=VideoAdapter)
    mock_video_adapter.metrics.return_value = VideoAdapter.Metrics(
        duration=4.0, frame_rate=30
    )
    metadata = VideoFileMetadata(MagicMock(spec=Path), mock_video_adapter)
    assert metadata.duration == approx(4.0)
    assert metadata.frame_rate == approx(30)


def test_video_file_metadata_factory():
    metadata = (
        FileMetadataFactory().create_metadata(VIDEO_FILE).metadata(VideoFileMetadata)
    )
    assert metadata.duration == approx(4.96666, 0.00001)
    assert metadata.frame_rate == approx(30)
    assert metadata.width == 190
    assert metadata.height == 240
