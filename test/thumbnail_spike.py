from pathlib import Path

import PIL.Image
import ffmpeg

from adapters import DefaultImageAdapter

IMAGE_ADAPTER = DefaultImageAdapter()
from metadata import ImageMetadata

VIDEO_PATH = Path(__file__).parent / "fixtures" / "valid.mp4"

if __name__ == "__main__":
    width = height = 256
    process1 = (
        ffmpeg.input(VIDEO_PATH)
        .filter("scale", width, height)
        .output("pipe:", format="rawvideo", pix_fmt="rgb24")
        .run_async(pipe_stdout=True)
    )

    metadata = []
    while True:
        in_bytes = process1.stdout.read(width * height * 3)
        if not in_bytes:
            break
        # in_frame = np.frombuffer(in_bytes, np.uint8).reshape([height, width, 3])
        in_image = PIL.Image.frombuffer(data=in_bytes, size=(width, height), mode="RGB")
        metadata.append(ImageMetadata(image=in_image, image_adapter=IMAGE_ADAPTER))
    process1.wait()
    print(len(metadata))
