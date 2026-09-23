# Test3D

## Video source

The video worker supports either a network stream or a local webcam.

Choose one of these sources:

For Docker Desktop on Windows:

```env
VIDEO_SOURCE=webcam-windows
WEBCAM_INDEX=0
```

Then open `http://localhost:8090` and allow camera access when the browser
asks for permission. The browser captures the webcam and sends frames to the
video worker through `/ws/input`; the YOLO worker still performs inference in
the ROCm container.

When running the `video-worker` directly on Linux with a camera device, use:

```env
VIDEO_SOURCE=webcam-linux
WEBCAM_INDEX=0
```

For a 3D printer camera, use its stream URL:

```env
VIDEO_SOURCE=http://192.168.0.139:8080/?action=stream
```

You can also set `VIDEO_SOURCE=1` to select camera index 1. For a 3D printer
camera, keep using its MJPEG URL, for example:

```env
VIDEO_SOURCE=http://192.168.0.139:8080/?action=stream
```

When running the video worker inside Docker Desktop on Windows, the host
webcam is not automatically available inside the container. Run the
`video-worker` locally with Python for webcam capture, or expose a webcam
device through a Linux/WSL Docker environment.
