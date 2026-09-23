#!/usr/bin/env python3
"""
Capture one frame from a video source and send it to the YOLO websocket.
Saves/prints the JSON response.

Usage examples:
  python tools/send_frame.py
  VIDEO_SOURCE='http://192.168.0.139:8080/?action=stream' YOLO_WS='ws://127.0.0.1:8002/inference' python tools/send_frame.py
  python tools/send_frame.py --source /path/to/video.mp4 --yolo ws://127.0.0.1:8002/inference
"""

import argparse
import asyncio
import json
import os
import sys
import time

try:
    import cv2
except Exception as e:
    print("Error importing OpenCV (cv2):", e, file=sys.stderr)
    raise

try:
    import websockets
except Exception as e:
    print("Error importing websockets:", e, file=sys.stderr)
    raise


def capture_frame(source, timeout=10.0):
    """Open source with OpenCV and capture one frame."""
    cap = cv2.VideoCapture(source)
    start = time.time()
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open video source: {source}")

    while True:
        ok, frame = cap.read()
        if ok and frame is not None:
            cap.release()
            return frame
        if time.time() - start > timeout:
            cap.release()
            raise RuntimeError(f"Timeout while reading frame from {source}")
        time.sleep(0.1)


def encode_jpeg(frame, quality=80):
    ok, enc = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise RuntimeError('Failed to encode frame to JPEG')
    return enc.tobytes()


async def send_to_yolo(yolo_ws, payload, timeout=10.0):
    try:
        async with websockets.connect(yolo_ws, ping_interval=20, ping_timeout=20) as ws:
            await ws.send(payload)
            # wait for response with timeout
            fut = asyncio.ensure_future(ws.recv())
            try:
                resp = await asyncio.wait_for(fut, timeout)
            except asyncio.TimeoutError:
                raise RuntimeError('Timed out waiting for response from YOLO websocket')

            # try to parse JSON
            try:
                return json.loads(resp)
            except Exception:
                return resp
    except Exception as e:
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', '-s', default=os.getenv('VIDEO_SOURCE', 'http://192.168.0.139:8080/?action=stream'), help='Video source for OpenCV (0 for webcam or URL/file)')
    parser.add_argument('--yolo', '-y', default=os.getenv('YOLO_WS', 'ws://127.0.0.1:8002/inference'), help='YOLO websocket URL')
    parser.add_argument('--quality', '-q', type=int, default=int(os.getenv('JPEG_QUALITY', '80')),
                        help='JPEG quality')
    parser.add_argument('--timeout', type=float, default=10.0, help='Timeout seconds for capture and websocket')
    parser.add_argument('--output', '-o', default=None, help='Optional path to save the JPEG file')
    args = parser.parse_args()

    print('Source =', args.source)
    print('YOLO WS =', args.yolo)

    frame = capture_frame(args.source, timeout=args.timeout)
    payload = encode_jpeg(frame, quality=args.quality)

    if args.output:
        with open(args.output, 'wb') as f:
            f.write(payload)
        print('Saved JPEG to', args.output)

    try:
        resp = asyncio.run(send_to_yolo(args.yolo, payload, timeout=args.timeout))
        print('Response from YOLO:')
        print(json.dumps(resp, ensure_ascii=False, indent=2))
    except Exception as e:
        print('Error sending frame to YOLO websocket:', e, file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
