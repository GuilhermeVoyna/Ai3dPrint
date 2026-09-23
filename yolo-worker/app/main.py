import asyncio
import json

import websockets
import uvicorn

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import HOST, PORT
from app.services.inference_service import InferenceService


inference_service = InferenceService()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "alive",
        "service": "yolo-worker"
    }


@app.post("/infer-image")
async def infer_image(file: UploadFile = File(...)):
    result = await asyncio.to_thread(
        inference_service.predict,
        await file.read(),
    )
    return {"result": result}


async def inference_handler(websocket):
    """
    Recebe frames JPEG e retorna os resultados da inferência em JSON.
    """

    print("Cliente conectado ao websocket da inferência.")

    try:
        frames_received = 0
        async for frame_bytes in websocket:
            try:
                frames_received += 1
                result = await asyncio.to_thread(
                    inference_service.predict,
                    frame_bytes,
                )

                await websocket.send(
                    json.dumps(result)
                )

                if frames_received == 1 or frames_received % 30 == 0:
                    print(
                        f"Frames recebidos e processados: {frames_received}"
                    )

            except Exception as error:
                error_response = {
                    "error": str(error),
                    "error_detected": False,
                    "detections": [],
                }

                await websocket.send(
                    json.dumps(error_response)
                )

                print(f"Erro ao processar frame: {error}")

    except websockets.exceptions.ConnectionClosed:
        print("Cliente desconectado do websocket.")


async def websocket_server():
    print(
        f"Iniciando YOLO Worker em "
        f"ws://{HOST}:{PORT}/inference"
    )

    async with websockets.serve(
        inference_handler,
        HOST,
        PORT,
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()


async def http_server():
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8003,
        log_level="info",
    )

    server = uvicorn.Server(config)

    await server.serve()


async def main():
    print("Health check: http://localhost:8003/health")

    await asyncio.gather(
        websocket_server(),
        http_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())