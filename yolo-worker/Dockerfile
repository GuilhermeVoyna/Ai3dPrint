FROM rocm/pytorch:rocm10.0_ubuntu24.04_py3.12_pytorch_release_2.11.0

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libxcb1 libgl1 libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /opt/venv/lib/python3.12/site-packages/_rocm_sdk_core/lib/librocdxg.so.1 /opt/venv/lib/python3.12/site-packages/_rocm_sdk_core/lib/librocdxg.so && \
    ln -sf /opt/venv/lib/python3.12/site-packages/_rocm_sdk_core/lib/libhsa-runtime64.so.1 /opt/venv/lib/python3.12/site-packages/_rocm_sdk_core/lib/libhsa-runtime64.so

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    python -m pip install --no-cache-dir --no-deps ultralytics==8.4.155

COPY . .

EXPOSE 8002 8003

CMD ["python", "-m", "app.main"]
