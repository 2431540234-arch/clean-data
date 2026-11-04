# Frontend (Streamlit)

Giao diện của Data Cleaning Platform: Streamlit 1.41.1 + Plotly + pandas, chỉ giao diện sáng, tiếng Việt.
Toàn bộ logic nghiệp vụ nằm ở backend; frontend chỉ gọi API qua `api_client.py`.

## Chạy demo trên máy mới (Windows hoặc Linux/macOS)

Cần Python 3.11 và Git. Không cần backend, database hay Docker để xem giao diện: dùng chế độ dữ liệu mẫu.

```bash
git clone <địa-chỉ-repo> && cd <repo>/data-cleaning-platform/frontend
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt

# Chế độ dữ liệu mẫu (không cần backend):
#   Windows (PowerShell):  $env:FRONTEND_MOCK="1"; streamlit run app.py
#   Linux/macOS:           FRONTEND_MOCK=1 streamlit run app.py
```

Mở <http://localhost:8501>. Trang đăng nhập hiện sẵn tài khoản thử:

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Người dùng | `user@example.com` | `User12345` |
| Quản trị viên | `admin@example.com` | `Admin123!` |

Trạng thái dữ liệu mẫu nằm trong phiên trình duyệt: tải lại trang (F5) sẽ đăng xuất và nạp lại dữ liệu ban đầu.

### Kịch bản demo gợi ý (khoảng 5 phút)
1. Đăng nhập bằng tài khoản người dùng, vào **Dashboard** → **Tạo project** → **Mở**.
2. **Tải lên** `sample_data/khach_hang_tieu_de_khac.csv` (tiêu đề khác chuẩn: "Họ và tên", "Số ĐT"...).
3. **Tổng quan dữ liệu**: thống kê cột, điểm chất lượng, biểu đồ.
4. **Mapping cột**: "Điền ví dụ" → "Gợi ý mapping" → "Xác nhận mapping".
5. **Làm sạch dữ liệu**: thêm bước từ Gợi ý AI, Quy tắc có sẵn hoặc Tự viết quy tắc vào cùng hàng đợi → sắp xếp → "Xem trước" → xác nhận "Áp dụng thay đổi".
   Bản xem trước có ba tab Thay đổi theo ô / Dữ liệu sau / Dữ liệu trước. Các bước đổi tên cột từ Mapping chạy **sau cùng**.
6. **Thư viện quy tắc**: chọn Quy tắc hệ thống hoặc Quy tắc của dự án; mở quy tắc để sửa luôn nạp vào trình soạn, mỗi lần lưu tạo một quy tắc mới.
7. **Lịch sử phiên bản**: Hoàn tác / Làm lại / Khôi phục. **Xuất dữ liệu**: gauge điểm chất lượng, tải CSV/Excel.
8. **Nhật ký hoạt động**, **Tài khoản** (đổi mật khẩu); đăng nhập admin để xem **Quản trị người dùng**, **Thống kê hệ thống**.

Dataset có sẵn trong chế độ mẫu: `sample_data/khach_hang_ban.csv` (nhiều lỗi cài sẵn). Dùng ô "Mở dataset theo ID" với ID 1.

## Chạy với backend thật

```bash
BACKEND_URL=http://localhost:8000 streamlit run app.py     # mặc định http://localhost:8000
```
Hoặc `docker compose up -d --build` ở thư mục gốc dự án. Khi backend chưa sẵn sàng, giao diện hiện
thông báo lỗi có nút thử lại thay vì lộ traceback.

## Biến môi trường

| Biến | Ý nghĩa |
|---|---|
| `BACKEND_URL` | Địa chỉ backend (mặc định `http://localhost:8000`) |
| `FRONTEND_MOCK=1` | Dùng backend giả (`mock_api.py`) thay vì gọi API thật; sidebar hiện nhãn "Chế độ dữ liệu mẫu" |
| `FRONTEND_MOCK_FAIL=suggestions,preview,...` | Chỉ ở chế độ mẫu: các nhóm API này luôn trả lỗi máy chủ (để thử trạng thái lỗi) |

## Kiểm tra

```bash
pip install pytest==8.3.4 ruff==0.8.4
ruff check . && ruff format --check .
pytest                      # AppTest của Streamlit + backend giả, khoảng 20 giây
```
CI chạy đúng các lệnh này (job `frontend` trong `.github/workflows/test.yml`).
Ảnh chụp kiểm tra giao diện: [docs/screenshots](../docs/screenshots/README.md).

## Cấu trúc

```
app.py            điểm vào: cấu hình trang, CSS, st.navigation theo quyền
views/            các trang (một file một trang)
components/       thành phần dùng chung (ui.py, navigation.py, biểu đồ, thẻ gợi ý, bảng diff, ...)
assets/styles.css design tokens + style (Minimal Ink, chỉ nền sáng)
.streamlit/       theme sáng cố định, giới hạn upload 200 MB (CSV theo từng phần)
api_client.py     gọi backend (httpx), xử lý lỗi kết nối/timeout/5xx, chọn mock bằng FRONTEND_MOCK
mock_*.py         backend giả có trạng thái (tài liệu tham khảo hành vi, KHÔNG phải đặc tả)
tests/            pytest + AppTest
```

## Rủi ro và việc nên làm sau
- **CSS phụ thuộc nội bộ Streamlit 1.41.1** (rà lại khi nâng phiên bản; `requirements.txt` ghim cứng 1.41.1):
  `.block-container`, `.stApp h1-h3`, `[data-testid="stMetricValue"]`, class nút/alert (`.stButton`, `.stAlert`...) và
  khối **Việt hóa ô tải file** (`stFileUploaderDropzone*`). Khối ô tải file có cơ chế an toàn khi hỏng:
  selector không khớp thì chữ tiếng Anh gốc hiện lại. Mọi chỗ đều có ghi chú trong `assets/styles.css`.
- **Đăng nhập không giữ sau F5** (token nằm trong `st.session_state`).
- Bảng `st.dataframe` vẽ bằng canvas (không chọn/copy chữ bằng DOM, trình đọc màn hình đọc hạn chế).
- Mock đọc Excel cần `openpyxl` (đã có trong `requirements.txt`, chỉ dùng cho chế độ mẫu).
- Các hạn chế do backend chưa có endpoint (danh sách dataset theo project, danh sách lỗi, đọc dòng dữ liệu, lưu mapping...)
  được liệt kê trong [docs/BACKEND_TODO.md](../docs/BACKEND_TODO.md).
