# Build context is the repository root (see docker-compose.yml).
# One image definition, two flavours selected by EXTRAS:
#   api: --build-arg EXTRAS=ml,pii,data   (models + redaction + embedding job)  [default]
#   ui:  --build-arg EXTRAS=ui
FROM python:3.11-slim

ARG EXTRAS="ml,pii,data"
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/home/app/.cache/huggingface

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /home/app
WORKDIR /app

# Dependencies first, so source changes don't invalidate the (large) install layer.
COPY pyproject.toml readme.md LICENSE ./
COPY src ./src
# CPU-only torch keeps the image far smaller than the default CUDA build.
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -e ".[${EXTRAS}]" \
    && if echo "${EXTRAS}" | grep -q "pii"; then python -m spacy download en_core_web_lg; fi

COPY scripts ./scripts
USER app

EXPOSE 8000 8501
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
