## Scope (MVP → Beta)

### MVP (shipping first)
- **Writing Task 2** (text input) với output:
  - Overall band + 4 tiêu chí: TaskResponse, CohesionCoherence, LexicalResource, GrammaticalRangeAccuracy
  - Danh sách lỗi theo taxonomy (có vị trí/đoạn + gợi ý sửa)
  - 3 ưu tiên cải thiện lớn nhất (“study plan”)
  - Trích dẫn bằng chứng (rubric + bài mẫu) từ RAG
- **Job-based async**: submit → nhận `job_id` → poll status → nhận kết quả
- **User accounts**: register/login (JWT), history submissions
- **Free-trial quota**: giới hạn theo ngày để kiểm soát chi phí LLM

### Beta (mở rộng)
- Writing Task 1
- Speaking (audio → ASR → feedback) **bật qua feature flag**
- Billing/Subscription (Stripe) + quota theo plan
- Admin review queue + feedback loop

