# Task 1: Phân tích bài toán và kiến trúc công nghệ

**Đề tài nhóm 12 – Đề tài AI 2:** Nền tảng Data Cleaning Excel/CSV có AI gợi ý chuẩn hóa
**Người soạn:** Châu Nhựt Tân – MSSV 2431540234 – Lớp 24DHTT04 (Nhóm trưởng)
**Tên file nộp:** `2431540234_ChauNhutTan.ppt` (nộp vào thư mục Google Drive của giảng viên)

Cấu trúc theo quy ước chung: mỗi slide gồm tiêu đề, 3–5 ý chính (mỗi ý ≤ 15 từ), gợi ý hình minh họa và ghi chú thuyết trình 2–3 câu.

> Nội dung Task 1 do tôi soạn dựa trên đề tài và cấu trúc dự án hiện có. Bạn cần đọc lại, diễn đạt bằng lời của mình
> và hiểu để giải thích được khi bị hỏi (quy ước của giảng viên).

---

## Slide 1 – Bìa

**Ý chính**
- Tên task: Phân tích bài toán và kiến trúc công nghệ
- Đề tài: Nền tảng Data Cleaning Excel/CSV có AI gợi ý chuẩn hóa
- Họ tên: Châu Nhựt Tân (nhóm trưởng)
- MSSV 2431540234 – Lớp 24DHTT04 – Nhóm 12 (3 thành viên)

**Gợi ý hình:** logo trường, ảnh nền là bảng dữ liệu "bẩn" chuyển thành "sạch" (trước/sau).

**Ghi chú thuyết trình:** Em xin giới thiệu phần việc của em là phân tích bài toán và thiết kế kiến trúc công nghệ cho nền tảng làm sạch dữ liệu của nhóm 12. Phần này là nền tảng để hai bạn còn lại cài đặt chức năng.

---

## Slide 2 – Đặt vấn đề và mục tiêu của phần việc

**Ý chính**
- Dữ liệu Excel/CSV từ biểu mẫu, hệ thống cũ thường có nhiều lỗi.
- Làm sạch thủ công chậm, khó lặp lại, không lưu vết thay đổi.
- Người dùng không chuyên cần công cụ bán tự động, có AI gợi ý.
- Mục tiêu: phân tích bài toán, use case và chọn kiến trúc phù hợp.
- Ràng buộc đề: web deploy online, có đăng nhập, phân quyền, UI hoàn chỉnh.

**Gợi ý hình:** bảng "Đề bài và yêu cầu tối thiểu" (Lĩnh vực: Data + AI – Data Quality; Hướng tiếp cận: Data Cleaning + Rule Engine + AI Suggestions).

**Ghi chú thuyết trình:** Đề tài yêu cầu một sản phẩm web hoàn chỉnh chứ không phải notebook hay script chạy localhost. Vì vậy phần của em là xác định rõ bài toán rồi chọn kiến trúc đủ đơn giản để cả nhóm làm xong và deploy được.

---

## Slide 3 – Phân tích vấn đề: các loại lỗi dữ liệu bẩn

**Ý chính**
- Trùng lặp bản ghi, thiếu giá trị, ngoại lai (outlier).
- Sai định dạng ngày, số điện thoại, email.
- Giá trị không nhất quán: "TP. Hồ Chí Minh", "HCM", "TP.HCM".
- Sai kiểu dữ liệu, tên cột không thống nhất giữa các file.
- Mỗi nhóm lỗi có phương pháp phát hiện riêng.

**Gợi ý bảng:** (nhóm lỗi | ví dụ trong `sample_data/khach_hang_ban.csv` | cách phát hiện)
| Nhóm lỗi | Ví dụ | Cách phát hiện |
|---|---|---|
| Trùng lặp | "Tran Thi Binh" lặp 2 dòng | So khớp chính xác và gần đúng (rapidfuzz) |
| Thiếu giá trị | Ô trống, "N/A", "-" | Danh sách null token |
| Sai ngày | `1995-03-12` lẫn `15/04/1990` | python-dateutil |
| Sai điện thoại | `0912 345 678`, `+84 933 445 566` | phonenumbers (E.164) |
| Sai email | ` TranThiBinh@GMAIL.com ` | email-validator, trim, lowercase |
| Ngoại lai | Tuổi bất thường | IQR, Z-score (NumPy) |

**Ghi chú thuyết trình:** Em dùng chính file dữ liệu mẫu của nhóm để minh họa từng loại lỗi. Mỗi loại lỗi sẽ có một detector riêng trong hệ thống, nên việc phân loại này quyết định cách chia module ở backend.

---

## Slide 4 – Tác nhân và use case

**Ý chính**
- Ba tác nhân: người dùng, quản trị viên, AI Provider (OpenAI/Claude).
- Người dùng: upload, xem lỗi, nhận gợi ý, preview, áp dụng, undo.
- Người dùng: xem điểm chất lượng, audit log, xuất dữ liệu sạch.
- Admin: quản lý user, đổi quyền, xem thống kê hệ thống.
- AI chỉ gợi ý rule; người dùng luôn là người xác nhận.

**Gợi ý hình:** sơ đồ use case UML (User → UC1…UC11, Admin → UC11, UC12, AI Provider nối với UC5).

| Mã | Use case |
|---|---|
| UC1 | Đăng ký / đăng nhập |
| UC2 | Tạo project, upload CSV/Excel |
| UC3–UC4 | Xem profiling và các lỗi phát hiện |
| UC5 | Nhận gợi ý rule, giải thích lỗi, mapping cột từ AI |
| UC6–UC8 | Preview trước/sau, áp dụng rule, undo/redo |
| UC9–UC10 | Xem điểm chất lượng, xuất dữ liệu sạch |
| UC11–UC12 | Xem audit log; admin quản lý user |

**Ghi chú thuyết trình:** Use case chia theo hai vai trò để khớp với yêu cầu phân quyền của đề. AI xuất hiện như một tác nhân ngoài, chỉ được đề xuất chứ không tự sửa dữ liệu.

---

## Slide 5 – Luồng xử lý chính

**Ý chính**
- Upload file, tự dò encoding, dấu phân cách và dòng tiêu đề.
- Profiling schema rồi các detector phát hiện lỗi.
- AI sinh rule dạng JSON; validator kiểm tra trước khi lưu.
- Preview (dry-run) trước/sau, người dùng xác nhận mới áp dụng.
- Mỗi lần áp dụng tạo phiên bản mới, ghi audit log, tính điểm.

**Gợi ý hình:** sơ đồ luồng (flowchart) từ trái sang phải.
```
Upload → Ingestion → Profiling → Detectors → AI gợi ý rule (JSON)
 → Validator → Preview (dry-run) → Xác nhận → Rule Engine
 → Phiên bản mới → Audit log / Quality score / Export (Undo bất kỳ lúc nào)
```

**Ghi chú thuyết trình:** Điểm an toàn quan trọng nhất là AI chỉ sinh rule JSON, không bao giờ sinh code để chạy. Chỉ Rule Engine dùng Pandas mới sửa dữ liệu thật, và người dùng xem preview trước khi xác nhận.

---

## Slide 6 – Kiến trúc tổng thể

**Ý chính**
- Frontend Streamlit tách riêng, gọi backend FastAPI qua REST API.
- Backend nhiều lớp: api, services, repositories, models.
- PostgreSQL lưu user, project, rule, audit log, metadata phiên bản.
- Object Storage lưu file gốc và các phiên bản Parquet.
- AI Provider được gọi từ backend, dữ liệu nhạy cảm được che.

**Gợi ý hình:** sơ đồ kiến trúc các khối.
```
Trình duyệt ──► Streamlit + Plotly ──HTTP/JSON──► FastAPI
                                                   ├─► PostgreSQL (Neon/Supabase)
                                                   ├─► Object Storage (file gốc + Parquet)
                                                   ├─► AI Provider (OpenAI/Claude)
                                                   └─► Rule Engine + Detectors (Pandas)
```

**Ghi chú thuyết trình:** Em tách frontend và backend để mỗi bên phát triển và deploy độc lập. Toàn bộ chạy được bằng Docker Compose ở máy local, và dùng cùng image đó để đưa lên nền tảng cloud.

---

## Slide 7 – Công nghệ sử dụng và lý do chọn

**Ý chính**
- Python 3.11 dùng chung cho cả backend và frontend.
- Backend: FastAPI, Pydantic, SQLAlchemy 2.0, Alembic quản lý migration.
- Dữ liệu: Pandas, NumPy, openpyxl, PyArrow (Parquet), rapidfuzz.
- Bảo mật: JWT (PyJWT), bcrypt, phân quyền admin/user.
- Chất lượng: pytest, ruff, black, Docker, GitHub Actions.

**Gợi ý bảng:** (tầng | công nghệ | lý do)
| Tầng | Công nghệ | Lý do chọn |
|---|---|---|
| Backend | FastAPI, Uvicorn | Nhanh, tự sinh tài liệu Swagger |
| Database | PostgreSQL, SQLAlchemy, Alembic | Quan hệ rõ ràng, có migration |
| Lưu phiên bản | Parquet + S3-compatible (boto3) | Gọn, giữ kiểu dữ liệu, dễ undo |
| AI | OpenAI hoặc Claude, tenacity | Trả JSON, tự thử lại khi lỗi |
| Frontend | Streamlit, Plotly | Dựng giao diện và biểu đồ nhanh bằng Python |

**Ghi chú thuyết trình:** Em chọn Streamlit thay vì Dash vì viết giao diện nhiều trang nhanh hơn và cùng ngôn ngữ Python với backend. Các thư viện đều được ghim phiên bản trong file requirements để môi trường giống nhau giữa các thành viên.

---

## Slide 8 – Mô hình dữ liệu (ERD), phân quyền và bảo mật

**Ý chính**
- 9 bảng: users, projects, datasets, dataset_versions, schema_profiles.
- Còn lại: suggestions, rules, audit_logs, quality_reports.
- Quan hệ: user 1–n project, project 1–n dataset, dataset 1–n phiên bản.
- Đăng nhập bằng JWT; mật khẩu băm bằng bcrypt.
- Phân quyền admin/user bằng dependency của FastAPI.

**Gợi ý hình:** sơ đồ ERD 9 bảng (vẽ từ `backend/app/models/` và migration `0001_initial_schema.py`).

**Ghi chú thuyết trình:** Mọi thay đổi dữ liệu đều có thể truy vết qua audit_logs và quay lại qua dataset_versions. Quyền được kiểm tra ở tầng backend nên người dùng thường không thể gọi các API của admin.

---

## Slide 9 – Kết quả, demo và liên kết với sản phẩm nhóm

**Ý chính**
- Đã dựng khung dự án backend, frontend, database chạy bằng Docker Compose.
- Migration tạo đủ 9 bảng; `/health` và Swagger `/docs` hoạt động.
- Kiểm thử và lint: pytest 8 test đạt, ruff và black đều đạt.
- Phần phân tích này là cơ sở để các bạn cài detector, rule, giao diện.
- Việc còn lại: hoàn thiện chức năng và deploy có URL công khai.

**Gợi ý hình (ảnh chụp màn hình thật cần chụp):** (1) `docker compose ps` với 3 service healthy; (2) trang Swagger `/docs`; (3) kết quả `pytest`; (4) URL deploy khi đã có.

**Ghi chú thuyết trình:** Đây là kết quả của phần hạ tầng và thiết kế mà em phụ trách. Phần chức năng chi tiết sẽ do các thành viên khác trình bày, còn sản phẩm cuối sẽ chạy online theo yêu cầu của đề.

> Lưu ý khi nộp: chỉ ghi vào slide những gì đã thật sự chạy được. Nếu đến lúc nộp đã deploy xong, thay ý cuối bằng URL công khai.

---

## Slide 10 – Khó khăn, hướng cải thiện và nguồn tham khảo

**Ý chính**
- Khó khăn: lệch phiên bản Python (3.13 so với 3.11 của dự án).
- Khó khăn: cổng Postgres 5432 trùng project khác; passlib cần ghim bcrypt 4.0.1.
- Cải thiện: hoàn thiện deploy online (Render/Railway/Fly.io, Neon/Supabase).
- Cải thiện: xử lý nền bằng BackgroundTasks hoặc RQ/Celery cho file lớn.
- Cải thiện: bổ sung thêm test và hỗ trợ thêm AI provider.

**Gợi ý hình:** bảng 2 cột (Khó khăn | Cách xử lý) và danh sách nguồn ở cuối slide.

**Ghi chú thuyết trình:** Khó khăn lớn nhất là đồng bộ môi trường giữa các máy, nên em dùng Docker và ghim phiên bản thư viện. Hướng tiếp theo là đưa hệ thống lên cloud để có URL công khai.

**Nguồn tham khảo**
1. Pandas – https://pandas.pydata.org/docs/
2. FastAPI – https://fastapi.tiangolo.com/
3. Pydantic – https://docs.pydantic.dev/
4. SQLAlchemy 2.0 – https://docs.sqlalchemy.org/en/20/
5. Alembic – https://alembic.sqlalchemy.org/
6. PostgreSQL – https://www.postgresql.org/docs/
7. Streamlit – https://docs.streamlit.io/
8. Plotly Python – https://plotly.com/python/
9. Apache Arrow / Parquet – https://arrow.apache.org/docs/python/parquet.html
10. RapidFuzz – https://rapidfuzz.github.io/RapidFuzz/
11. phonenumbers – https://pypi.org/project/phonenumbers/
12. Anthropic API – https://docs.anthropic.com/
13. OpenAI API – https://platform.openai.com/docs/
14. Docker Compose – https://docs.docker.com/compose/
15. GitHub Actions – https://docs.github.com/actions
16. Tài liệu nội bộ: `docs/architecture.md`, `docs/rule_dsl.md`, `docs/quality_score.md`, `docs/permissions.md`
