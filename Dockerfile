FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE .python-version uv.lock ./
COPY src ./src
COPY examples ./examples
COPY tests ./tests
RUN pip install --no-cache-dir --no-deps .
ENV PORT=8080 CLONE_TO_CONFIDENCE_DEMO_PATH=/app/examples/broken-repo
EXPOSE 8080
ENTRYPOINT ["clone-to-confidence"]
CMD ["web", "--host", "0.0.0.0", "--public-demo"]
