from pathlib import Path

import librosa
import numpy as np

from adapters import AudioAdapter


class LibrosaAudioAdapter(AudioAdapter):
    def metrics(self, path: Path) -> AudioAdapter.Metrics:
        y, sr = librosa.load(path.as_posix())
        duration = librosa.get_duration(y=y, sr=sr)
        return AudioAdapter.Metrics(duration=duration, entropy=self._compute_entropy(y))

    # noinspection PyPep8Naming
    @staticmethod
    def _compute_entropy(y):
        S = np.abs(librosa.stft(y))
        norm_S = librosa.util.normalize(S, norm=1, axis=0)
        entropy = -np.sum(norm_S * np.log2(norm_S), axis=0)
        entropy = float(np.mean(entropy))
        return entropy
