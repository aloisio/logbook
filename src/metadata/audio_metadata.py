from functools import cached_property
from pathlib import Path

from adapter import AudioAdapter
from .metadata_base import Metadata


class AudioFileMetadata(Metadata):
    def __init__(self, path: Path, audio_adapter: AudioAdapter):
        self._path = path
        self._audio_adapter = audio_adapter

    @property
    def duration(self) -> float:
        return self._metrics["duration"]

    @property
    def entropy(self) -> float:
        return self._metrics["entropy"]

    @cached_property
    def _metrics(self):
        return self._audio_adapter.metrics(self._path)
