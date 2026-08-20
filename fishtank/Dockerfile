FROM python:3.12-slim

WORKDIR /opt/antfarm
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/antfarm \
    IN_CONTAINER=1

RUN pip install --no-cache-dir httpx==0.28.1

COPY agent/ /opt/antfarm/agent/

WORKDIR /workspace
CMD ["python", "-m", "agent.harness"]
