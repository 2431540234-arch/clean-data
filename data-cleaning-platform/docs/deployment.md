# Hướng dẫn triển khai (Deployment)

> TODO: hoàn thiện tài liệu này cho môi trường production thật.

## 1. Yêu cầu hạ tầng

- PostgreSQL (có thể dùng Supabase/Neon/RDS).
- Storage S3-compatible (Supabase Storage / Cloudflare R2).
- Server chạy Docker (VPS, Render, Railway, Fly.io...).

## 2. Biến môi trường cần cấu hình

- Xem đầy đủ trong [.env.example](../.env.example).

## 3. Triển khai bằng Docker Compose (tham khảo local)

- Xem hướng dẫn trong [README.md](../README.md).

## 4. TODO: triển khai production

- Tách riêng Postgres quản lý (không chạy trong container cùng app).
- Cấu hình HTTPS (reverse proxy Nginx/Caddy hoặc platform tự quản lý).
- Chiến lược backup database và storage.
- CI/CD: liên kết với `.github/workflows/deploy.yml`.

## 5. Giám sát & logging

- TODO: tích hợp công cụ giám sát (ví dụ Sentry, UptimeRobot) và log tập trung.
