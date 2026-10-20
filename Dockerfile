FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE .python-version uv.lock ./
COPY src ./src
COPY tests ./tests
RUN pip install --no-cache-dir --no-deps .
ENTRYPOINT ["clone-to-confidence"]
CMD ["--help"]
