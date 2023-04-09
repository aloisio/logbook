import math
import sys
import time
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Protocol, Optional

import PIL
import cv2
import ffmpeg

from adapter import Image

DEFAULT_TIMEOUT = 60
DEFAULT_SIZE = 256
DEFAULT_START_PERCENTAGE = 2.5


class VideoAdapter(Protocol):
    @dataclass
    class Metrics:
        duration: float
        frame_rate: float
        width: int
        height: int
        number_of_frames: int

    @dataclass
    class FrameSpec:
        metrics: "VideoAdapter.Metrics"
        size: tuple[int, int]
        frame_numbers: list[int]

        @property
        def duration(self) -> float:
            return self.metrics.duration

        @property
        def total_number_of_frames(self) -> int:
            return self.metrics.number_of_frames

    def metrics(self, path: Path) -> Metrics:
        ...

    def frames(self, path: Path, frame_spec: FrameSpec) -> list[tuple[Image, float]]:
        ...


class DefaultVideoAdapter(VideoAdapter):
    def __init__(self):
        self._opencv_adapter = OpencvVideoAdapter()
        self._ffmpeg_adapter = FfmpegVideoAdapter()

    def metrics(self, path: Path) -> VideoAdapter.Metrics:
        try:
            return self._ffmpeg_adapter.metrics(path)
        except Exception as exc:
            print(exc)
            return self._opencv_adapter.metrics(path)

    def frames(
        self, path: Path, frame_spec: Optional[VideoAdapter.FrameSpec] = None
    ) -> list[tuple[Image, float]]:
        if not frame_spec:
            frame_spec = self.frame_spec(path)
        try:
            capture = self._opencv_adapter.frames(path, frame_spec)
            if capture:
                return capture
        except Exception as exc:
            print(exc, file=sys.stderr)
        return self._ffmpeg_adapter.frames(path, frame_spec)

    def frame_spec(
        self,
        path: Path,
        min_sample_size: int = 3,
        start_percentage: float = DEFAULT_START_PERCENTAGE,
        end_percentage: float = 100 - DEFAULT_START_PERCENTAGE,
    ) -> VideoAdapter.FrameSpec:
        metrics = self.metrics(path)
        print(f"{metrics=}")
        print(f"{start_percentage=} {end_percentage=}")
        start_frame = math.ceil((metrics.number_of_frames * start_percentage) / 100)
        end_frame = math.ceil((metrics.number_of_frames * end_percentage) / 100)
        frames_in_range = end_frame - start_frame + 1
        log_frames = int(min_sample_size * (math.log(frames_in_range + 1, 10) + 1))
        target_number_of_frames = (
            min([log_frames, int(frames_in_range)])
            if log_frames > min_sample_size
            else min_sample_size
        )
        step_size = math.ceil(frames_in_range / target_number_of_frames)
        frame_numbers = list(range(start_frame, end_frame + 1, step_size))
        aspect = metrics.width / metrics.height
        width = int(DEFAULT_SIZE * aspect) if aspect < 1 else DEFAULT_SIZE
        height = DEFAULT_SIZE if aspect < 1 else int(DEFAULT_SIZE / aspect)
        return VideoAdapter.FrameSpec(
            metrics=metrics,
            size=(width, height),
            frame_numbers=frame_numbers,
        )


class OpencvVideoAdapter(VideoAdapter):
    # noinspection PyUnresolvedReferences
    def metrics(self, path: Path) -> VideoAdapter.Metrics:
        cap = cv2.VideoCapture(str(path))
        try:
            if not cap.isOpened():
                raise IOError("Failed to open video file")

            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_rate = cap.get(cv2.CAP_PROP_FPS)
            return VideoAdapter.Metrics(
                duration=frame_count / frame_rate,
                frame_rate=frame_rate,
                width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                number_of_frames=frame_count,
            )
        except Exception as e:
            raise e
        finally:
            cap.release()

    # noinspection PyUnresolvedReferences
    def frames(
        self, path: Path, spec: VideoAdapter.FrameSpec
    ) -> list[tuple[Image, float]]:
        print(f"Target number of frames: {len(spec.frame_numbers)}")
        frames = []
        width, height = spec.size
        # open the video file using OpenCV VideoCapture
        cap = cv2.VideoCapture(str(path))
        try:
            if not cap.isOpened():
                raise IOError(f"opencv open {path=}")
            # set the position to the start frame
            if not cap.set(cv2.CAP_PROP_POS_FRAMES, spec.frame_numbers[0]):
                raise IOError(f"opencv set {spec.frame_numbers[0]=}")
            missed_frames: list[int] = []
            start = time.monotonic()
            progress = 0
            # read and process frames
            for frame_number in spec.frame_numbers:
                progress += 1
                if not cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number):
                    raise IOError(f"opencv set {frame_number=}")
                # read the next frame
                ret, frame = cap.read()
                if (time.monotonic() - start) > DEFAULT_TIMEOUT and progress < len(
                    spec.frame_numbers
                ) * 3 / 4:
                    raise IOError(
                        f"opencv read timeout at {DEFAULT_TIMEOUT} s, progress {int((progress * 100) / len(spec.frame_numbers))}%"
                    )
                if not ret:
                    if len(missed_frames) >= 3:
                        raise IOError(f"opencv read third strike {missed_frames=}")
                    missed_frames.append(frame_number)
                    continue
                # resize the frame to DEFAULT_SIZExDEFAULT_SIZE
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                # convert the frame from BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # convert the frame to a PIL Image
                img = PIL.Image.fromarray(frame)
                # calculate position from frame number
                position = frame_number / spec.total_number_of_frames
                # append the image and its position to the list of frames
                frames.append((img, position))
        except Exception as exc:
            raise exc
        finally:
            cap.release()

        return frames


class FfmpegVideoAdapter(VideoAdapter):
    def metrics(self, path: Path) -> VideoAdapter.Metrics:
        probe = self._probe(path)
        video_stream = self._get_first_video_stream(path)
        try:
            frame_rate = float(Fraction(video_stream["avg_frame_rate"]))
        except ZeroDivisionError:
            frame_rate = float(Fraction(video_stream["r_frame_rate"]))
        # Get video stream duration
        if "duration" in video_stream:
            duration = float(video_stream["duration"])
        else:
            duration = float(self._get_vn_stream(path).get("duration", -1))
        if duration == -1:
            duration = float(probe["format"]["duration"])
        width = int(video_stream["width"])
        height = int(video_stream["height"])
        return VideoAdapter.Metrics(
            duration=duration,
            frame_rate=frame_rate,
            width=width,
            height=height,
            number_of_frames=int(duration * frame_rate),
        )

    def frames(
        self, path: Path, spec: VideoAdapter.FrameSpec
    ) -> list[tuple[Image, float]]:
        frames = []
        width, height = spec.metrics.width, spec.metrics.height

        # extract the duration and average frame rate
        duration = spec.metrics.duration
        total_number_of_frames = spec.metrics.number_of_frames

        # calculate the start and end frames based on the adjusted start and end times
        start_frame = spec.frame_numbers[0]
        end_frame = spec.frame_numbers[-1]
        number_of_frames = end_frame - start_frame
        print(f"{start_frame=}")
        print(f"{end_frame=}")
        print(f"{number_of_frames=}")
        target_number_of_frames = len(spec.frame_numbers)
        print(f"{target_number_of_frames=}")
        duration = (end_frame - start_frame) / spec.metrics.frame_rate
        target_fps = target_number_of_frames / (duration + 1)
        print(f"Sampling frame rate: {target_fps} fps")

        # create input stream
        stream = ffmpeg.input(path.as_posix())

        # extract frames within the desired range
        stream = stream.filter("trim", start_frame=start_frame, end_frame=end_frame)

        stream = stream.filter("fps", target_fps)

        # scale each frame to DEFAULT_SIZExDEFAULT_SIZE
        stream = stream.filter("scale", width, height)

        # create output stream
        stream = ffmpeg.output(stream, "pipe:", format="rawvideo", pix_fmt="rgb24")

        # capture output and process frames
        out, _ = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        for i in range(target_number_of_frames):
            # calculate the frame number based on the loop index and target frame rate
            frame_number = int(start_frame + i * spec.metrics.frame_rate / target_fps)
            position = frame_number / total_number_of_frames
            # read one frame (width * height * 3 bytes) at a time
            frame = out[: width * height * 3]
            if not frame:
                break
            # convert bytes to image
            img = PIL.Image.frombuffer(data=frame, mode="RGB", size=(width, height))
            # append the image and its frame number to the list of frames
            frames.append((img, position))
            # remove the frame bytes from the output bytes
            out = out[width * height * 3 :]
        return frames

    @lru_cache
    def _probe(self, path: Path) -> dict:
        # probe the video file to get test_metadata
        try:
            return ffmpeg.probe(path)
        except Exception as e:
            raise ValueError(f"Probe error in {path}: {e}")

    def _get_first_video_stream(self, path: Path):
        video_stream = next(
            (
                stream
                for stream in self._probe(path)["streams"]
                if stream["codec_type"] == "video"
            ),
            None,
        )
        if video_stream is None:
            raise ValueError(f"No video stream in {path}")
        return video_stream

    def _get_vn_stream(self, path: Path):
        try:
            return ffmpeg.probe(
                str(path),
                select_streams=f"v:{self._get_first_video_stream(path)['index']}",
            ).get("streams", [{}])[0]
        except Exception as e:
            raise ValueError(f"Probe error in {path}: {e}")
