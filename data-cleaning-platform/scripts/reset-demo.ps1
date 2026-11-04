# Đưa hệ thống demo về trạng thái sạch: xóa DB và file đã lưu, tạo lại bảng, nạp lại tài khoản demo.
#
# CẢNH BÁO: lệnh `docker compose down -v` XÓA VĨNH VIỄN dữ liệu Postgres và thư mục lưu file của
# compose project này (mọi dự án, dataset, phiên bản, nhật ký). Chỉ dùng cho máy demo.
#
# Cách dùng (chạy ở thư mục gốc của repo):
#   powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1          # hỏi xác nhận
#   powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1 -Yes     # không hỏi
param([switch]$Yes)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not $Yes) {
    $answer = Read-Host "Việc này XÓA SẠCH dữ liệu demo rồi nạp lại 2 tài khoản mẫu. Gõ RESET để tiếp tục"
    if ($answer -ne "RESET") {
        Write-Host "Đã hủy, chưa thay đổi gì."
        exit 1
    }
}

$env:PYTHONUTF8 = "1"
docker compose down -v
docker compose up -d --build
Write-Host "Chờ backend sẵn sàng..."
for ($i = 0; $i -lt 60; $i++) {
    try {
        if ((Invoke-WebRequest -UseBasicParsing http://localhost:8000/health).StatusCode -eq 200) { break }
    } catch { Start-Sleep -Seconds 2 }
}
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
Write-Host "Xong. Đăng nhập: user@example.com / User12345, admin@example.com / Admin123!"
