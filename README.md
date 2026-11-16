# BabyControl

Công cụ quản lý giờ dùng máy Windows cho trẻ:
- Mỗi ngày chỉ được dùng số phút do phụ huynh đặt (mặc định 30).
- Trước khi vào máy phải làm bài Toán + Tiếng Anh (tự sinh theo lớp). Số câu mỗi môn cấu hình được.
- Có các khung giờ "mở thả để học": dùng tự do, không cần làm bài, không trừ giờ.
- Phụ huynh cấu hình mọi thứ từ tài khoản admin.

## Yêu cầu

- Windows 10/11, Python 3.10+ (có Tkinter, mặc định có trong bản cài từ python.org).
- **2 tài khoản Windows**: tài khoản admin của phụ huynh và một tài khoản *người dùng chuẩn* (Standard) cho con.
  Nếu con dùng tài khoản admin thì công cụ không chặn được.

## Cài đặt (PowerShell, chạy trong thư mục dự án)

```powershell
# 1. Build (không cần quyền admin)
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# 2. Cài service (mở PowerShell bằng "Run as administrator")
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1

# 3. Chạy công cụ phụ huynh (tài khoản admin, sẽ hỏi quyền UAC)
dist\babycontrol-admin.exe
```

Lần đầu mở `babycontrol-admin.exe` sẽ yêu cầu tạo mật khẩu phụ huynh. Sau đó đặt phút/ngày, lớp, số câu, khung giờ học.

Khi con đăng nhập, service tự bật màn hình bài tập trong phiên của con. Tài khoản admin không bị khoá.

## Gỡ cài đặt

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall_service.ps1   # as administrator
```

## Lưu ý

- Dữ liệu ở `%PROGRAMDATA%\BabyControl` (cấu hình chỉ admin sửa được; thư mục `usage` con ghi được vì kiosk cần đếm giờ).
- Nếu `babycontrol-kiosk.exe` không chạy được trong phiên của con quá ~30 giây, service sẽ đăng xuất phiên đó.
  Nếu thiếu file kiosk.exe, service không làm gì (tránh đăng xuất liên tục khi cài lỗi).
- Mật khẩu phụ huynh trên màn hình khoá cho thêm 15 phút và bỏ qua bài tập.
- Task Manager bị tắt cho tài khoản của con (chính sách người dùng).

## Phát triển

```bash
bash init.sh --verify    # tạo .venv, chạy pytest
```
