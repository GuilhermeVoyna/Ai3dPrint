const processedFrame = document.querySelector('#processed-frame');
const frameContext = processedFrame.getContext('2d');
const streamFrame = document.querySelector('.stream-frame');
const detectionOverlay = document.querySelector('#detection-overlay');
const overlayContext = detectionOverlay.getContext('2d');
let processedFrameWidth = 0;
let processedFrameHeight = 0;
let latestResult = null;
const placeholder = document.querySelector('#stream-placeholder');
const streamPill = document.querySelector('#stream-pill');
const connectionLabel = document.querySelector('#connection-label');
const statusText = document.querySelector('#status-text');
const statusIcon = document.querySelector('#status-icon');
const lastUpdate = document.querySelector('#last-update');
const detectionList = document.querySelector('#detection-list');
const detectionCount = document.querySelector('#detection-count');
const frameCount = document.querySelector('#frame-count');
const resultTime = document.querySelector('#result-time');
const metricFrames = document.querySelector('#metric-frames');
const metricService = document.querySelector('#metric-service');
const metricSocket = document.querySelector('#metric-socket');
const streamState = document.querySelector('#stream-state');

const apiBase = window.TEST3D_API_URL || window.location.origin;
const apiOrigin = new URL(apiBase, window.location.origin);
const socketProtocol = apiOrigin.protocol === 'https:' ? 'wss:' : 'ws:';
const liveUrl = `${socketProtocol}//${apiOrigin.host}${apiOrigin.pathname.replace(/\/$/, '')}/ws/live`;
const inputUrl = `${socketProtocol}//${apiOrigin.host}${apiOrigin.pathname.replace(/\/$/, '')}/ws/input`;

function formatNumber(value) { return String(value || 0).padStart(6, '0'); }
function updateClock(element) { element.textContent = new Date().toLocaleTimeString('pt-BR'); }

function setOnline(online) {
  connectionLabel.textContent = online ? 'Online' : 'Sem conexão';
  statusText.textContent = online ? 'Sinal recebido' : 'Aguardando sinal';
  statusIcon.textContent = online ? '◉' : '◌';
  streamPill.textContent = online ? 'LIVE' : 'OFFLINE';
  streamPill.classList.toggle('online', online);
  streamState.textContent = online ? 'Sinal recebido' : 'Sinal não detectado';
}

function drawDetections(result = latestResult) {
  const detections = Array.isArray(result?.detections) ? result.detections : [];
  const width = streamFrame.clientWidth;
  const height = streamFrame.clientHeight;
  detectionOverlay.width = width;
  detectionOverlay.height = height;
  overlayContext.clearRect(0, 0, width, height);
  if (!processedFrameWidth || !processedFrameHeight) return;

  const scale = Math.min(width / processedFrameWidth, height / processedFrameHeight);
  const offsetX = (width - processedFrameWidth * scale) / 2;
  const offsetY = (height - processedFrameHeight * scale) / 2;
  overlayContext.font = '500 12px "DM Mono", monospace';
  overlayContext.lineWidth = 2;

  detections.forEach((detection) => {
    if (!Array.isArray(detection.bbox) || detection.bbox.length !== 4) return;
    const [x1, y1, x2, y2] = detection.bbox;
    const x = offsetX + x1 * scale;
    const y = offsetY + y1 * scale;
    const boxWidth = (x2 - x1) * scale;
    const boxHeight = (y2 - y1) * scale;
    const label = `${detection.class_name || 'Objeto'} ${Math.round((detection.confidence || 0) * 100)}%`;
    const labelWidth = overlayContext.measureText(label).width + 12;
    const labelY = Math.max(18, y);

    overlayContext.strokeStyle = '#c6f56b';
    overlayContext.strokeRect(x, y, boxWidth, boxHeight);
    overlayContext.fillStyle = '#c6f56b';
    overlayContext.fillRect(x, labelY - 18, labelWidth, 18);
    overlayContext.fillStyle = '#0b1117';
    overlayContext.fillText(label, x + 6, labelY - 5);
  });
}

function connectLive() {
  const socket = new WebSocket(liveUrl);
  socket.binaryType = 'blob';
  let pendingPacket = null;

  socket.addEventListener('message', async (event) => {
    if (typeof event.data === 'string') {
      try {
        pendingPacket = JSON.parse(event.data);
        metricFrames.textContent = formatNumber(pendingPacket.frames_processed);
        frameCount.textContent = `${formatNumber(pendingPacket.frames_processed)} frames`;
        metricService.textContent = 'ONLINE';
        renderDetections(pendingPacket.result);
        updateClock(resultTime);
        updateClock(lastUpdate);
        setOnline(true);
      } catch (error) {
        console.warn('Metadados inválidos recebidos do video-worker', error);
      }
      return;
    }

    const bitmap = await createImageBitmap(event.data);
    processedFrameWidth = bitmap.width;
    processedFrameHeight = bitmap.height;
    const width = streamFrame.clientWidth;
    const height = streamFrame.clientHeight;
    const scale = Math.min(width / bitmap.width, height / bitmap.height);
    const offsetX = (width - bitmap.width * scale) / 2;
    const offsetY = (height - bitmap.height * scale) / 2;
    processedFrame.width = width;
    processedFrame.height = height;
    frameContext.clearRect(0, 0, width, height);
    frameContext.drawImage(bitmap, offsetX, offsetY, bitmap.width * scale, bitmap.height * scale);
    bitmap.close();
    placeholder.classList.add('hidden');
    setOnline(true);
    drawDetections(latestResult);
  });
  socket.addEventListener('open', () => { metricSocket.textContent = 'OPEN'; });
  socket.addEventListener('close', () => { metricSocket.textContent = 'CLOSED'; setTimeout(connectLive, 3000); });
  socket.addEventListener('error', () => socket.close());
}

async function startBrowserCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    console.warn('A captura da webcam exige um navegador compatível.');
    return;
  }

  const cameraStream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: 'environment' },
    audio: false,
  });
  const camera = document.createElement('video');
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  camera.muted = true;
  camera.playsInline = true;
  camera.srcObject = cameraStream;
  await camera.play();

  const inputSocket = new WebSocket(inputUrl);
  let waitingForResult = false;

  const sendLatestFrame = () => {
    if (inputSocket.readyState !== WebSocket.OPEN || waitingForResult) return;
    if (!camera.videoWidth || !camera.videoHeight) return;

    canvas.width = camera.videoWidth;
    canvas.height = camera.videoHeight;
    context.drawImage(camera, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob || inputSocket.readyState !== WebSocket.OPEN) return;
      waitingForResult = true;
      inputSocket.send(blob);
    }, 'image/jpeg', 0.8);
  };

  inputSocket.addEventListener('open', sendLatestFrame);
  inputSocket.addEventListener('message', () => {
    waitingForResult = false;
    sendLatestFrame();
  });
  inputSocket.addEventListener('close', () => {
    cameraStream.getTracks().forEach((track) => track.stop());
  });
  inputSocket.addEventListener('error', () => inputSocket.close());
}

async function configureVideoSource() {
  try {
    const response = await fetch('/api/health');
    const health = await response.json();
    if (health.video_source === 'browser') await startBrowserCamera();
  } catch (error) {
    console.warn('Não foi possível descobrir a origem do vídeo', error);
  }
}

function renderDetections(result) {
  latestResult = result;
  const detections = Array.isArray(result?.detections) ? result.detections : [];
  drawDetections(result);
  detectionCount.textContent = String(detections.length).padStart(2, '0');
  if (!detections.length) {
    detectionList.innerHTML = '<div class="empty-state"><span>—</span><p>Nenhuma detecção<br />registrada ainda.</p></div>';
    return;
  }
  detectionList.innerHTML = detections.map((detection) => `
    <div class="detection-item">
      <div><span class="detection-name">${escapeHtml(detection.class_name || 'Objeto')}</span><span class="detection-id">ID ${String(detection.class_id ?? '--').padStart(2, '0')}</span></div>
      <span class="confidence">${Math.round((detection.confidence || 0) * 100)}%</span>
    </div>`).join('');
}

function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]); }

window.addEventListener('resize', () => drawDetections());
metricSocket.textContent = 'CONNECTING';
connectLive();
configureVideoSource();
