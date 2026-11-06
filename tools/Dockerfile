# Моковый сервис Tasks API. Контекст сборки — каталог tools/:
#   docker build -t tasks-mock tools
FROM python:3.12-slim

# Без внешних зависимостей: только стандартная библиотека Python.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8090

WORKDIR /app

COPY mock_tasks_api.py /app/mock_tasks_api.py

# Мок не пишет на диск, поэтому работаем не от root.
RUN useradd --create-home --uid 1000 mock
USER mock

EXPOSE 8090

HEALTHCHECK --interval=5s --timeout=3s --start-period=2s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2)"

CMD ["python", "mock_tasks_api.py"]
