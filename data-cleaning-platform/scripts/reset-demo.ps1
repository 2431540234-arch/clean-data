# Đưa dữ liệu demo về trạng thái sạch, KHÔNG build lại image, KHÔNG đụng frontend.
#
# Việc script làm (chỉ trong compose project của repo này):
#   1. Dừng container backend (không xóa).
#   2. Trong container Postgres, database data_cleaning:  DROP SCHEMA public CASCADE; CREATE SCHEMA public;
#      -> xóa mọi bảng và dữ liệu (người dùng, dự án, dataset, phiên bản, nhật ký). Không xóa volume Postgres.
#   3. Xóa NỘI DUNG volume lưu file dataset (dcp_storage, gắn vào /app/data/storage của backend).
#      Không xóa volume nào khác và không xóa chính volume.
#   4. Bật lại backend, chạy `alembic upgrade head`, rồi `scripts/seed.py` (2 tài khoản demo + dự án mẫu).
#
# Tùy chọn -HostStorage (chỉ khi backend chạy NGOÀI Docker): xóa nội dung backend\data\storage trên máy,
# có câu xác nhận riêng (gõ XOA-FILE). Chỉ động tới đúng thư mục đó trong repo.
#
# Cách dùng (chạy ở bất kỳ đâu, script tự về thư mục gốc dự án):
#   powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1                 # hỏi xác nhận RESET
#   powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1 -Yes            # bỏ qua câu hỏi RESET
#   powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1 -HostStorage    # thêm dọn backend\data\storage
#   -Project dcp-test -ComposeFile docker-compose.dcp-test.yml                      # chạy trên project khác
param(
    [switch]$Yes,
    [switch]$HostStorage,
    [switch]$HostStorageYes,
    [string]$Project = "",
    [string]$ComposeFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Compose = @("compose")
if ($ComposeFile) { $Compose += @("-f", $ComposeFile) }
if ($Project) { $Compose += @("-p", $Project) }

function Invoke-Docker {
    docker @Compose @args
    if ($LASTEXITCODE -ne 0) { throw "Lệnh docker $($args -join ' ') thất bại (mã $LASTEXITCODE)." }
}

if (-not $Yes) {
    $answer = Read-Host "Việc này XÓA SẠCH dữ liệu demo (DB data_cleaning và file dataset) rồi nạp lại 2 tài khoản mẫu. Gõ RESET để tiếp tục"
    if ($answer -ne "RESET") {
        Write-Host "Đã hủy, chưa thay đổi gì."
        exit 1
    }
}

if ($HostStorage -and -not $HostStorageYes) {
    $hostAnswer = Read-Host "Cũng XÓA NỘI DUNG thư mục backend\data\storage trên máy này? Gõ XOA-FILE để đồng ý"
    if ($hostAnswer -ne "XOA-FILE") {
        Write-Host "Đã hủy, chưa thay đổi gì."
        exit 1
    }
}

Write-Host "1/4 Dừng backend..."
Invoke-Docker stop backend

Write-Host "2/4 Xóa schema public trong database data_cleaning (Postgres trong Docker)..."
Invoke-Docker exec -T postgres psql -U postgres -d data_cleaning -v ON_ERROR_STOP=1 `
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

Write-Host "3/4 Xóa nội dung volume lưu file dataset (/app/data/storage)..."
Invoke-Docker run --rm --no-deps --entrypoint sh backend `
    -c "find /app/data/storage -mindepth 1 -delete"

if ($HostStorage) {
    $HostDir = Join-Path $ProjectRoot "backend\data\storage"
    $Resolved = (Resolve-Path -LiteralPath $HostDir -ErrorAction SilentlyContinue)
    if ($Resolved -and $Resolved.Path.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        Write-Host "     Dọn nội dung $($Resolved.Path)"
        Get-ChildItem -LiteralPath $Resolved.Path -Force | Remove-Item -Recurse -Force
    } else {
        Write-Host "     Không có thư mục backend\data\storage, bỏ qua."
    }
}

Write-Host "4/4 Bật lại backend, chạy migration và nạp tài khoản demo..."
Invoke-Docker up -d backend
# Windows PowerShell 5.1 coi stderr của lệnh ngoài là lỗi khi $ErrorActionPreference = "Stop", nên tạm nới lỏng.
$PreviousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$Ready = $false
for ($i = 0; $i -lt 60; $i++) {
    docker @Compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" *> $null
    if ($LASTEXITCODE -eq 0) { $Ready = $true; break }
    Start-Sleep -Seconds 2
}
$ErrorActionPreference = $PreviousPreference
if (-not $Ready) { throw "Backend không sẵn sàng sau 2 phút; xem docker compose logs backend." }
Invoke-Docker exec -T backend alembic upgrade head
Invoke-Docker exec -T backend python scripts/seed.py
Write-Host "Xong. Đăng nhập: user@example.com / User12345, admin@example.com / Admin123!"
