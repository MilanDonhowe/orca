from __future__ import annotations

import base64
import threading
from dataclasses import dataclass
from typing import Protocol


import cv2
import cv2.utils.logging as cv2_log
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


@dataclass(frozen=True)
class TextRegion:
    text: str
    confidence: float
    polygon: list[list[int]]


@dataclass(frozen=True)
class OCRResult:
    text: str
    regions: list[TextRegion]


class OCRBackend(Protocol):
    def read(self, image: np.ndarray) -> OCRResult: ...


class OCR:
    """Default local OCR engine backed by RapidOCR's Paddle-derived ONNX models."""

    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR()

    def read(self, image: np.ndarray) -> OCRResult:
        result, _ = self._engine(image)
        regions = [
            TextRegion(text=str(item[1]), confidence=float(item[2]), polygon=np.asarray(item[0], dtype=int).tolist())
            for item in (result or [])
        ]
        return OCRResult("\n".join(region.text for region in regions), regions)


class DemoOCR:
    def __init__(self, text: str = "ORCA demo product 20"):
        self.text = text

    def read(self, image: np.ndarray) -> OCRResult:
        height, width = image.shape[:2]
        region = TextRegion(self.text, 1.0, [[150, 290], [width - 150, 290], [width - 150, 430], [150, 430]])
        return OCRResult(self.text, [region])


def annotate_regions(image: np.ndarray, regions: list[TextRegion]) -> np.ndarray:
    annotated = image.copy()
    for region in regions:
        points = np.asarray(region.polygon, dtype=np.int32)
        cv2.polylines(annotated, [points], True, (152, 219, 206), 3, cv2.LINE_AA)
        anchor = tuple(points[np.argmin(points[:, 1])])
        label = f"{region.text}  {region.confidence:.0%}"
        cv2.putText(annotated, label, (int(anchor[0]), max(24, int(anchor[1]) - 8)), cv2.FONT_HERSHEY_SIMPLEX, .65, (7, 54, 66), 4, cv2.LINE_AA)
        cv2.putText(annotated, label, (int(anchor[0]), max(24, int(anchor[1]) - 8)), cv2.FONT_HERSHEY_SIMPLEX, .65, (152, 219, 206), 1, cv2.LINE_AA)
    return annotated


def image_data_url(image: np.ndarray, max_width: int = 960) -> str:
    if image.shape[1] > max_width:
        scale = max_width / image.shape[1]
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 78])
    if not ok:
        raise RuntimeError("Could not encode camera image")
    return "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")


def list_cameras(limit: int = 8) -> list[int]:
    # silence annoying cv2 "out of index" logs
    log_level = cv2_log.getLogLevel()
    cv2_log.setLogLevel(cv2_log.LOG_LEVEL_SILENT)

    available: list[int] = []
    for index in range(limit):
        capture = cv2.VideoCapture(index)
        if capture.isOpened():
            available.append(index)
        capture.release()
    # restore logging
    cv2_log.setLogLevel(log_level)
    return available
