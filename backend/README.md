# Smart IELTS Mentor - Backend

## Vì sao `pip` không chạy?

Trên macOS, Python 3 thường chỉ cài `pip3` (hoặc `python3 -m pip`), không có lệnh `pip` trong PATH.

**Giải pháp**: Dùng `python3 -m pip` thay vì `pip`:

```bash
python3 -m pip install -r backend/requirements.txt
```

## Thiết lập môi trường

### 1. Cài đặt dependencies

```bash
# Cách 1: Dùng python3 -m pip (không cần venv)
python3 -m pip install -r backend/requirements.txt

# Cách 2: Trong venv (khuyến nghị)
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
python -m pip install -r backend/requirements.txt
```

### 2. Tạo virtual environment (khuyến nghị)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

python -m pip install -r requirements.txt
```

### 3. Chạy API server

Từ **project root** (Smart_IELTS_Mentor):

```bash
cd Smart_IELTS_Mentor
# PYTHONPATH: . = project root (rag), backend = backend (app)
PYTHONPATH=".:backend" python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Hoặc từ **backend**:

```bash
cd backend
# PYTHONPATH: . = backend (app), .. = project root (rag)
PYTHONPATH=".:.." python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Docker Compose (Postgres + Redis)

```bash
# Từ project root
docker compose up -d

# Chỉ Postgres + Redis (mặc định)
# Nếu lỗi "port 5432 already allocated": đổi POSTGRES_PORT=5433 trong .env
# Thêm MinIO (S3): docker compose --profile s3 up -d
```

### 5. Migration

```bash
cd backend
source ../.venv/bin/activate
PYTHONPATH=".:.." alembic upgrade head
```

### 6. Biến môi trường

Copy `.env.example` → `.env` và điền giá trị. Cần ít nhất:

- `JWT_SECRET`
- `POSTGRES_*` (dùng `localhost` khi chạy API trên host)
- `REDIS_URL`
- `OPENAI_API_KEY`, `PINECONE_*` (cho scoring)
