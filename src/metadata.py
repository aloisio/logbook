from abc import ABC
from functools import cached_property
from hashlib import blake2b
from pathlib import Path
from typing import (
    Optional,
    Type,
    TypeVar,
    TypedDict,
    Iterable,
)

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
    Image,
)


# noinspection PyPropertyDefinition, PyRedeclaration
class Metadata(ABC):
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

    def _compute_metadata(self):
        if hasattr(self, "_checksum"):
            return
        """
        Creates fields: _byte_entropy, _byte_histogram, _byte_size, _byte_thumbnail, _checksum
        """
        self._byte_size = self.path.stat().st_size
        histogram_image = self._image_adapter.histogram(self.path, self._digest)
        self._checksum = self._digest.hexdigest()
        self._histogram_image_metadata = ImageMetadata(
            histogram_image, self._image_adapter
        )

    @property
    def histogram_image_metadata(self) -> "ImageMetadata":
        return self._histogram_image_metadata


class ImageFileMetadata(Metadata):
    def __init__(self, path, image_adapter: ImageAdapter):
        self._path = path
        self._image_adapter = image_adapter

    @cached_property
    def image_metadata(self) -> "ImageMetadata":
        return ImageMetadata(self._image_adapter.load(self._path), self._image_adapter)


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
    def __init__(self, *metadata: T):
        super().__init__()
        self._aggregate = {type(m): m for m in metadata}

    def add(self, metadata: T, overwrite=False):
        if not isinstance(metadata, Metadata):
            raise ValueError(f"Parameter must be instance of {Metadata}")
        if (
            not overwrite
            and type(metadata) in self._aggregate
            and metadata is not self._aggregate[type(metadata)]
        ):
            raise ValueError(
                f"{type(metadata)} already added. Use overwrite=True to replace it."
            )
        self._aggregate.update({type(metadata): metadata})

    def metadata(self, cls: Type[T]) -> T:
        return self._aggregate[cls]

    @property
    def children(self) -> Iterable[Metadata]:
        return self._aggregate.values()


class ImageMetadata(Metadata):
    def __init__(self, image: Image, image_adapter: ImageAdapter):
        self._image_adapter = image_adapter
        thumbnail_image = image_adapter.thumbnail(image)
        self._width, self._height = image_adapter.last_size
        self._image_entropy = image_adapter.last_entropy
        self._image_histogram = image_adapter.rgb_histogram(thumbnail_image)
        self._image_thumbnail = image_adapter.to_grayscale(thumbnail_image)

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @cached_property
    def fractal_dimension(self) -> list[float]:
        return self._image_adapter.fractal_dimension(self._image_thumbnail)

    @property
    def histogram(self) -> list[int]:
        return self._image_histogram

    @property
    def entropy(self) -> float:
        return self._image_entropy


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
        metadata = CompositeMetadata()
        metadata.add(FileMetadata(path, self._image_adapter, self._digest))
        if self._file_type_adapter.is_image(path):
            metadata.add(ImageFileMetadata(path, self._image_adapter))
        if self._file_type_adapter.is_audio(path):
            metadata.add(AudioFileMetadata(path, self._audio_adapter))
        if self._file_type_adapter.is_video(path):
            metadata.add(VideoFileMetadata(path, self._video_adapter))
        return metadata
