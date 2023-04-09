from functools import cached_property
from pathlib import Path
from typing import TypedDict

from typing_extensions import Required, Unpack

from adapter import VideoAdapter, ImageAdapter
from .metadata_base import Metadata


class VideoFileMetadata(Metadata):
    class Arguments(TypedDict):
        path: Required[Path]
        video_adapter: Required[VideoAdapter]
        image_adapter: Required[ImageAdapter]

    def __init__(self, **kwargs: Unpack[Arguments]):
        args = self.Arguments(**kwargs)
        self._path = args["path"]
        self._video_adapter = args["video_adapter"]
        self._image_adapter = args["image_adapter"]

    @property
    def duration(self) -> float:
        return self._metrics.duration

    @property
    def frame_rate(self) -> float:
        return self._metrics.frame_rate

    @property
    def width(self) -> int:
        return self._metrics.width

    @property
    def height(self) -> int:
        return self._metrics.height

    @cached_property
    def _metrics(self):
        return self._video_adapter.metrics(self._path)
