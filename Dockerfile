FROM python:3.11-slim

# 將環境變數設為不寫出 .pyc 及不緩衝標準輸出
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝系統依賴並安裝 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 設定工作目錄
WORKDIR /app

# 複製專案檔案
COPY pyproject.toml uv.lock ./
COPY . .

# 使用 uv 安裝依賴 (不建立虛擬環境，直接安裝至系統，適合容器環境)
RUN uv sync --frozen

# Cloud Run 會提供 $PORT (預設 8080)
# 透過 uv run 啟動 FastAPI 服務
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
