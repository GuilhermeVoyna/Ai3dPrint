import asyncio
import json
import logging

import websockets

logger = logging.getLogger(__name__)


class YoloClient:
    def __init__(self, url: str, connection_timeout: float = 10.0):
        self.url = url
        self.connection_timeout = connection_timeout
        self.connection = None

    @staticmethod
    def _decode_payload(payload):
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")

        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return payload

        return payload

    async def connect(self):
        """Establish a connection with the YOLO Worker."""
        logger.info("Conectando ao YOLO Worker: %s", self.url)
        self.connection = await websockets.connect(self.url)
        logger.info("Conexao com o YOLO Worker estabelecida")

    async def send_frame(self, frame: bytes):
        """Send a JPEG frame and receive the inference result."""
        while True:
            try:
                if self.connection is None:
                    try:
                        await asyncio.wait_for(
                            self.connect(), timeout=self.connection_timeout
                        )
                    except asyncio.TimeoutError as exc:
                        self.connection = None
                        raise RuntimeError(
                            "Timed out connecting to the YOLO Worker"
                        ) from exc

                connection = self.connection
                if connection is None:
                    continue

                await connection.send(frame)
                return self._decode_payload(await connection.recv())
            except asyncio.CancelledError:
                self.connection = None
                logger.info("Reconexao com o YOLO cancelada")
                raise
            except KeyboardInterrupt:
                self.connection = None
                logger.info("Video worker interrompido pelo usuario")
                raise
            except (OSError, websockets.exceptions.WebSocketException) as error:
                self.connection = None
                logger.warning(
                    "Falha na comunicacao com YOLO (%s). Tentando novamente em 1s",
                    error
                )
                await asyncio.sleep(1)

    async def close(self):
        """Close the connection with the YOLO Worker."""
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
            logger.info("Conexao com o YOLO Worker encerrada")