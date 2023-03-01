from functools import cached_property
from hashlib import blake2b
from pathlib import Path
from typing import Protocol, Tuple, ForwardRef, Type

from adapters import ImageAdapter, AudioAdapter, DefaultImageAdapter, DefaultAudioAdapter, FileTypeAdapter, \
    DefaultFileTypeAdapter

Metadata = ForwardRef('Metadata')


# noinspection PyPropertyDefinition, PyRedeclaration
class Metadata(Protocol):
    ...


# noinspection PyAttributeOutsideInit
class FileMetadata(Metadata):
    def __init__(self, path, image_adapter: ImageAdapter):
        self._image_adapter = image_adapter
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @property
    def histogram(self) -> list[int]:
        if not hasattr(self, '_byte_histogram'):
            self._compute_metadata()
        return self._byte_histogram

    @property
    def entropy(self) -> float:
        if not hasattr(self, '_byte_entropy'):
            self._compute_metadata()
        return self._byte_entropy

    @property
    def size(self) -> int:
        if not hasattr(self, '_byte_size'):
            self._byte_size = self.path.stat().st_size
        return self._byte_size

    @cached_property
    def path_with_checksum(self) -> Path:
        return self.path.with_name(f'{self.path.stem}.{self.checksum}{self.path.suffix}')

    @property
    def checksum(self) -> str:
        if not hasattr(self, '_checksum'):
            self._compute_metadata()
        return self._checksum

    @property
    def fractal_dimension(self) -> list[float]:
        if not hasattr(self, '_byte_thumbnail'):
            self._compute_metadata()
        return self._image_adapter.fractal_dimension(self._byte_thumbnail)

    def _compute_metadata(self):
        """
        Initializes fields: _byte_histogram, _byte_thumbnail, _checksum, _histogram_entropy,
        _image_entropy, _image_histogram, _image_size, _image_thumbnail, _is_image_
        """
        digest = blake2b(digest_size=8)
        histogram_image = self._image_adapter.histogram(self.path, digest)
        self._byte_entropy = self._image_adapter.last_entropy
        self._byte_histogram = self._image_adapter.rgb_histogram(histogram_image)
        self._byte_thumbnail = self._image_adapter.to_grayscale(histogram_image)
        # noinspection PyBroadException
        try:
            thumbnail_image = self._image_adapter.thumbnail(self.path, digest)
            self._image_size = self._image_adapter.last_size
            self._image_entropy = self._image_adapter.last_entropy
            self._image_histogram = self._image_adapter.rgb_histogram(thumbnail_image)
            self._image_thumbnail = self._image_adapter.to_grayscale(thumbnail_image)
            self._is_image = True
        except Exception:
            self._image_size = None
            self._image_entropy = None
            self._image_histogram = None
            self._image_thumbnail = None
            self._is_image = False
        self._checksum = digest.hexdigest()


class ImageFileMetadata(FileMetadata):
    def __init__(self, path, image_adapter: ImageAdapter):
        super().__init__(path, image_adapter)

    @property
    def histogram(self) -> list[int]:
        if not hasattr(self, '_image_histogram'):
            self._compute_metadata()
        return self._image_histogram

    @property
    def entropy(self) -> float:
        if not hasattr(self, '_image_entropy'):
            self._compute_metadata()
        return self._image_entropy

    @property
    def size(self) -> Tuple[int, int]:
        if not hasattr(self, '_image_size'):
            self._compute_metadata()
        return self._image_size

    @property
    def fractal_dimension(self) -> list[float]:
        if not hasattr(self, '_image_thumbnail'):
            self._compute_metadata()
        return self._image_adapter.fractal_dimension(self._image_thumbnail)


class AudioFileMetadata(Metadata):
    def __init__(self, path: Path, audio_adapter: AudioAdapter):
        self._path = path
        self._audio_adapter = audio_adapter

    @property
    def duration(self) -> float:
        return self._audio_adapter.duration(self._path)


class FileMetadataFactory:
    def __init__(self, image_adapter: ImageAdapter = None, audio_adapter: AudioAdapter = None,
                 file_type_adapter: FileTypeAdapter = None):
        self.image_adapter = DefaultImageAdapter() if image_adapter is None else image_adapter
        self.audio_adapter = DefaultAudioAdapter() if audio_adapter is None else audio_adapter
        self.file_type_adapter = DefaultFileTypeAdapter() if file_type_adapter is None else file_type_adapter

    def create_metadata(self, path: Path) -> dict[Type[Metadata], Metadata]:
        metadata = {FileMetadata: FileMetadata(path, self.image_adapter)}
        if self.file_type_adapter.is_image(path):
            metadata[ImageFileMetadata] = ImageFileMetadata(path, self.image_adapter)
        if self.file_type_adapter.is_audio(path):
            metadata[AudioFileMetadata] = AudioFileMetadata(path, self.audio_adapter)
        return metadata
