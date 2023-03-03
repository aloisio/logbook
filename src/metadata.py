from functools import cached_property
from hashlib import blake2b
from pathlib import Path
from typing import Protocol, Tuple, Type

from adapters import (ImageAdapter, AudioAdapter, DefaultImageAdapter, DefaultAudioAdapter, FileTypeAdapter,
                      DefaultFileTypeAdapter, Digest, NullDigest)


# noinspection PyPropertyDefinition, PyRedeclaration
class Metadata(Protocol):
    ...


# noinspection PyAttributeOutsideInit
class FileMetadata(Metadata):
    def __init__(self, path, image_adapter: ImageAdapter, digest: Digest = None):
        self._image_adapter = image_adapter
        self._path = path
        self._digest = digest if digest is not None else NullDigest()
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
        return self.path.with_name(f'{self.path.stem}.{self.checksum}{self.path.suffix}')

    @property
    def checksum(self) -> str:
        return self._checksum

    @cached_property
    def fractal_dimension(self) -> list[float]:
        return self._image_adapter.fractal_dimension(self._byte_thumbnail)

    def _compute_metadata(self):
        if hasattr(self, '_checksum'):
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
        return self._audio_adapter.duration(self._path)


class FileMetadataFactory:
    def __init__(self, digest:Digest = None, image_adapter: ImageAdapter = None, audio_adapter: AudioAdapter = None, file_type_adapter: FileTypeAdapter = None):
        self._digest = digest if digest is not None else blake2b(digest_size=8)
        self._image_adapter = image_adapter if image_adapter else DefaultImageAdapter()
        self._audio_adapter = audio_adapter if audio_adapter is not None else DefaultAudioAdapter()
        self._file_type_adapter = file_type_adapter if file_type_adapter is not None else DefaultFileTypeAdapter()

    def create_metadata(self, path: Path) -> dict[Type[Metadata], Metadata]:
        file_metadata = FileMetadata(path, self._image_adapter, self._digest)
        metadata = {FileMetadata: file_metadata}
        if self._file_type_adapter.is_image(path):
            image_file_metadata = ImageFileMetadata(path, self._image_adapter)
            metadata[ImageFileMetadata] = image_file_metadata
        if self._file_type_adapter.is_audio(path):
            metadata[AudioFileMetadata] = AudioFileMetadata(path, self._audio_adapter)
        return metadata
