# Test3D frontend

Microfrontend estático do sistema Test3D. O Nginx serve a interface e encaminha para o `video-worker`:

- `WS /ws/live`: metadados da previsão e JPEG do mesmo frame, em tempo real

O frontend não consulta status por polling. O WebSocket envia primeiro os metadados e depois o JPEG do mesmo `frame_id`; assim cada caixa é desenhada no frame que originou a previsão.

## Executar

A partir de `Test3D/`:

```bash
docker compose up --build frontend video-worker yolo-worker
```

Abra `http://localhost:8090`. Para desenvolvimento rápido sem Docker, execute `python -m http.server 8090 --directory frontend` (ou outra porta); em hosts locais a interface aponta automaticamente para `http://localhost:8010` e o backend já permite CORS.
