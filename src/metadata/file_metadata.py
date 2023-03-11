from functools import cached_property
from hashlib import blake2b
from pathlib import Path
from typing import TypedDict, Type, Iterable, TypeVar

from typing_extensions import Unpack, NotRequired

from adapter import (
    ImageAdapter,
    Digest,
    AudioAdapter,
    FileTypeAdapter,
    VideoAdapter,
    DefaultFileTypeAdapter,
    DefaultVideoAdapter,
)
from adapter.audio_adapter import LibrosaAudioAdapter
from adapter.image_adapter import DefaultImageAdapter
from .audio_metadata import AudioFileMetadata
from .image_metadata import ImageMetadata, ImageFileMetadata
from .metadata_base import Metadata
from .video_metadata import VideoFileMetadata


class FileMetadata(Metadata):
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
        """
        Creates fields: _byte_size, _checksum, _histogram_image_metadata
        """
        self._byte_size = self.path.stat().st_size
        histogram_image = self._image_adapter.histogram(self.path, self._digest)
        self._checksum = self._digest.hexdigest()
        self._histogram_image_metadata = ImageMetadata(
            image=histogram_image,
            image_adapter=self._image_adapter,
            fractal_dimension=True,
        )

    @property
    def histogram_image_metadata(self) -> ImageMetadata:
        return self._histogram_image_metadata


T = TypeVar("T", bound=Metadata)


class CompositeMetadata(Metadata):
    def __init__(self, *metadata: T):
        super().__init__()
        self._aggregate = {type(m): m for m in metadata}

    def add(self, metadata: T, overwrite=False) -> None:
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

    def get(self, cls: Type[T]) -> T:
        return self._aggregate[cls]

    @property
    def children(self) -> Iterable[Metadata]:
        return self._aggregate.values()


class FileMetadataFactory:
    class Arguments(TypedDict):
        digest: NotRequired[Digest]
        image_adapter: NotRequired[ImageAdapter]
        audio_adapter: NotRequired[AudioAdapter]
        file_type_adapter: NotRequired[FileTypeAdapter]
        video_adapter: NotRequired[VideoAdapter]

    def __init__(self, **kwargs: Unpack[Arguments]):
        self._file_type_adapter = kwargs.get(
            "file_type_adapter", DefaultFileTypeAdapter()
        )
        self._digest = kwargs.get("digest", blake2b(digest_size=8))
        self._image_adapter = (
            kwargs["image_adapter"]
            if "image_adapter" in kwargs
            else DefaultImageAdapter()
        )
        self._audio_adapter = (
            kwargs["audio_adapter"]
            if "audio_adapter" in kwargs
            else LibrosaAudioAdapter()
        )
        self._video_adapter = (
            kwargs["video_adapter"]
            if "video_adapter" in kwargs
            else DefaultVideoAdapter()
        )

    def create_metadata(self, path: Path) -> CompositeMetadata:
        metadata = CompositeMetadata()
        metadata.add(FileMetadata(path, self._image_adapter, self._digest))
        if self._file_type_adapter.is_image(path):
            metadata.add(ImageFileMetadata(path, self._image_adapter))
        if self._file_type_adapter.is_audio(path):
            metadata.add(AudioFileMetadata(path, self._audio_adapter))
        if self._file_type_adapter.is_video(path):
            metadata.add(
                VideoFileMetadata(
                    path=path,
                    video_adapter=self._video_adapter,
                    image_adapter=self._image_adapter,
                )
            )
        return metadata
