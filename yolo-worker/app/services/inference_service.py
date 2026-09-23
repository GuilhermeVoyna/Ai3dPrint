import cv2
import numpy as np

from ultralytics import YOLO

from app.config import (
    MODEL_PATH,
    DEVICE,
    IMAGE_SIZE,
    CONFIDENCE_THRESHOLD,
)


class InferenceService:
    def __init__(self):
        print(f"Carregando modelo: {MODEL_PATH}")

        self.model = YOLO(
            str(MODEL_PATH),
            task="detect",
        )

        print(f"Modelo carregado. Classes: {self.model.names}")

    def predict(self, frame_bytes: bytes) -> dict:
        """
        Recebe uma imagem JPEG em bytes e retorna as detecções.
        """

        image_array = np.frombuffer(
            frame_bytes,
            dtype=np.uint8,
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR,
        )

        if frame is None:
            raise ValueError("Não foi possível decodificar o frame.")

        results = self.model.predict(
            source=frame,
            imgsz=IMAGE_SIZE,
            conf=CONFIDENCE_THRESHOLD,
            device=DEVICE,
            verbose=False,
        )

        result = results[0]
        detections = []

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                coordinates = box.xyxy[0].tolist()

                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": self.model.names[class_id],
                        "confidence": confidence,
                        "bbox": coordinates,
                    }
                )

        return {
            "detections": detections,
            "error_detected": len(detections) > 0,
        }