FROM python:3.12-slim

WORKDIR /srv
COPY pyproject.toml VERSION ./
COPY app ./app
COPY vendor/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
