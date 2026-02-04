FROM python:3.14.2-slim

# Системные зависимости для PyTorch и huggingface
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Запускаем API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]