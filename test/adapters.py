from pathlib import Path
from typing import Protocol

import magic


class FileTypeAdapter(Protocol):
    def is_image(self, path: Path) -> bool:
        ...

    def is_audio(self, path: Path) -> bool:
        ...


class DefaultFileTypeAdapter(FileTypeAdapter):
    def is_image(self, path: Path) -> bool:
        return (mime := magic.from_file(path, mime=True)) and mime.startswith('image')

    def is_audio(self, path: Path) -> bool:
        return (mime := magic.from_file(path, mime=True)) and mime.startswith('audio')

