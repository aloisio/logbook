from functools import cached_property
from hashlib import blake2b
from pathlib import Path
from typing import Optional, Protocol, Tuple, Type, TypeVar, TypedDict, Iterable

from adapters import (
    ImageAdapter,
    AudioAdapter,
    DefaultImageAdapter,
    DefaultAudioAdapter,
    FileTypeAdapter,
    DefaultFileTypeAdapter,
    Digest,
    VideoAdapter,
    DefaultVideoAdapter,
)


# noinspection PyPropertyDefinition, PyRedeclaration
class Metadata(Protocol):
    ...


# noinspection PyAttributeOutsideInit
class FileMetadata(Metadata):
    NAME = "FileMetadata"

    def __init__(self, path, image_adapter: ImageAdapter, digest: Digest):
        self._image_adapter = image_adapter
        self._path = path
        self._digest = digest
        self._compute_metadata()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def histogram(self) -> list[int]:
        return self._byte_histogram

    @property
    def entropy(self) -> float:
        return self._byte_entropy

    @property
    def size(self) -> int:
        return self._byte_size

    @cached_property
    def path_with_checksum(self) -> Path:
        return self.path.with_name(
            f"{self.path.stem}.{self.checksum}{self.path.suffix}"
        )

    @property
    def checksum(self) -> str:
        return self._checksum

    @cached_property
    def fractal_dimension(self) -> list[float]:
        return self._image_adapter.fractal_dimension(self._byte_thumbnail)

    def _compute_metadata(self):
        if hasattr(self, "_checksum"):
            return
        """
        Creates fields: _byte_entropy, _byte_histogram, _byte_size, _byte_thumbnail, _checksum
        """
        self._byte_size = self.path.stat().st_size
        histogram_image = self._image_adapter.histogram(self.path, self._digest)
        self._byte_entropy = self._image_adapter.last_entropy
        self._byte_histogram = self._image_adapter.rgb_histogram(histogram_image)
        self._byte_thumbnail = self._image_adapter.to_grayscale(histogram_image)
        self._checksum = self._digest.hexdigest()


class ImageFileMetadata(Metadata):
    def __init__(self, path, image_adapter: ImageAdapter):
        self.path = path
        self._image_adapter = image_adapter
        self._compute_metadata()

    @property
    def histogram(self) -> list[int]:
        return self._image_histogram

    @property
    def entropy(self) -> float:
        return self._image_entropy

    @property
    def size(self) -> Tuple[int, int]:
        return self._image_size

    @cached_property
    def fractal_dimension(self) -> list[float]:
        return self._image_adapter.fractal_dimension(self._image_thumbnail)

    def _compute_metadata(self):
        """
        Creates fields: _checksum, _image_entropy, _image_histogram, _image_size, _image_thumbnail
        """
        thumbnail_image = self._image_adapter.thumbnail(self.path)
        self._image_size = self._image_adapter.last_size
        self._image_entropy = self._image_adapter.last_entropy
        self._image_histogram = self._image_adapter.rgb_histogram(thumbnail_image)
        self._image_thumbnail = self._image_adapter.to_grayscale(thumbnail_image)


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


class VideoFileMetadata(Metadata):
    def __init__(self, path: Path, video_adapter: VideoAdapter):
        self._path = path
        self._video_adapter = video_adapter

    @property
    def duration(self) -> float:
        return self._metrics["duration"]

    @property
    def frame_rate(self) -> float:
        return self._metrics["frame_rate"]

    @property
    def width(self) -> int:
        return self._metrics["width"]

    @property
    def height(self) -> int:
        return self._metrics["height"]

    @cached_property
    def _metrics(self):
        return self._video_adapter.metrics(self._path)


T = TypeVar("T", bound=Metadata)


class CompositeMetadata(Metadata):
    def __init__(self, metadata_aggregate: "MetadataAggregate"):
        super().__init__()
        self._aggregate = {type(v): v for k, v in metadata_aggregate.items()}

    def metadata(self, cls: Type[T]) -> T:
        return self._aggregate[cls]

    @property
    def children(self) -> Iterable[Metadata]:
        return self._aggregate.values()


class MetadataAggregate(TypedDict, total=False):
    FileMetadata: FileMetadata
    ImageFileMetadata: ImageFileMetadata
    AudioFileMetadata: AudioFileMetadata
    VideoFileMetadata: VideoFileMetadata
    CompositeMetadata: CompositeMetadata


class FileMetadataFactory:
    class FileMetadataFactoryArgs(TypedDict, total=False):
        digest: Optional[Digest]
        image_adapter: Optional[ImageAdapter]
        audio_adapter: Optional[AudioAdapter]
        file_type_adapter: Optional[FileTypeAdapter]
        video_adapter: Optional[VideoAdapter]

    def __init__(self, **kwargs: FileMetadataFactoryArgs):
        self._file_type_adapter = kwargs.get(
            "file_type_adapter", DefaultFileTypeAdapter()
        )
        self._digest = kwargs.get("digest", blake2b(digest_size=8))
        self._image_adapter = kwargs.get("image_adapter", DefaultImageAdapter())
        self._audio_adapter = kwargs.get("audio_adapter", DefaultAudioAdapter())
        self._video_adapter = kwargs.get("video_adapter", DefaultVideoAdapter())

    def create_metadata(self, path: Path) -> CompositeMetadata:
        aggregate = MetadataAggregate()
        aggregate.update(
            FileMetadata=FileMetadata(path, self._image_adapter, self._digest)
        )
        if self._file_type_adapter.is_image(path):
            aggregate.update(
                ImageFileMetadata=ImageFileMetadata(path, self._image_adapter)
            )
        if self._file_type_adapter.is_audio(path):
            aggregate.update(
                AudioFileMetadata=AudioFileMetadata(path, self._audio_adapter)
            )
        if self._file_type_adapter.is_video(path):
            aggregate.update(
                VideoFileMetadata=VideoFileMetadata(path, self._video_adapter)
            )
        return CompositeMetadata(aggregate)
