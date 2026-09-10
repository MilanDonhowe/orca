from __future__ import annotations

import base64
import threading
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np


class Camera(Protocol):
    def read(self) -> np.ndarray: ...
    def close(self) -> None: ...


class OpenCVCamera:
    def __init__(self, source: int | str = 0):
        self.capture = cv2.VideoCapture(source)
        self._lock = threading.Lock()
        if not self.capture.isOpened():
            raise RuntimeError(f"Could not open camera {source}")

    def read(self) -> np.ndarray:
        with self._lock:
            ok, frame = self.capture.read()
        if not ok or frame is None:
            raise RuntimeError("Camera did not return an image")
        return frame

    def close(self) -> None:
        self.capture.release()


class DemoCamera:
    def __init__(self, text: str = "ORCA demo - product 20"):
        self.text = text

    def read(self) -> np.ndarray:
        frame = np.full((720, 1280, 3), (44, 54, 58), dtype=np.uint8)
        cv2.rectangle(frame, (110, 150), (1170, 570), (238, 232, 213), -1)
        cv2.putText(frame, self.text, (175, 390), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (36, 48, 52), 4, cv2.LINE_AA)
        return frame

    def close(self) -> None:
        pass


class OCR:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR()

    def read(self, image: np.ndarray) -> str:
        result, _ = self._engine(image)
        return "\n".join(str(item[1]) for item in (result or []))


class DemoOCR:
    def __init__(self, text: str = "ORCA demo product 20"):
        self.text = text

    def read(self, image: np.ndarray) -> str:
        return self.text


def image_data_url(image: np.ndarray, max_width: int = 960) -> str:
    if image.shape[1] > max_width:
        scale = max_width / image.shape[1]
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 78])
    if not ok:
        raise RuntimeError("Could not encode camera image")
    return "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")


def list_cameras(limit: int = 8) -> list[int]:
    available: list[int] = []
    for index in range(limit):
        capture = cv2.VideoCapture(index)
        if capture.isOpened():
            available.append(index)
        capture.release()
    return available

