┌─────────────┐     POST /submissions/writing      ┌──────────────────┐
│   Client    │ ──────────────────────────────────►│  FastAPI API      │
│ (Frontend)  │     { prompt, text }                │  submissions      │
└─────────────┘                                    └────────┬─────────┘
                                                             │
                    1. Kiểm tra quota (DailyUsage)            │
                    2. Tạo Submission + Job (queued)          │
                    3. Đẩy task vào Redis                     │
                                                             ▼
┌─────────────┐     GET /jobs/{id}                  ┌──────────────────┐
│   Client    │ ◄────────────────────────────────── │  FastAPI API     │
│             │     { status, progress }            │  jobs            │
└─────────────┘                                    └──────────────────┘
                                                             ▲
                                                             │
┌─────────────┐     Celery lấy job từ Redis         ┌────────┴─────────┐
│  Postgres   │ ◄────────────────────────────────── │  Celery Worker   │
│  (kết quả)  │     Cập nhật Job + AssessmentResult │  tasks.process_job│
└─────────────┘                                    └────────┬─────────┘
                                                             │
                                                             │ Gọi assess_writing_task2()
                                                             ▼
                    ┌────────────────────────────────────────────────────┐
                    │  scoring/writing.py (RAG Pipeline)                  │
                    │  Phase 1: 37 descriptors → LLM → TR/CC/LR/GRA      │
                    │  Phase 2: Pinecone feedback → LLM → errors, plan   │
                    └────────────────────────────────────────────────────┘