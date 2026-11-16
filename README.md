# BabyControl

Công cụ quản lý giờ dùng máy tính Windows cho trẻ em, viết bằng Python.

> **Trạng thái:** phần logic (cấu hình, sinh bài, đếm giờ, giám sát) đã có test tự động.
> Phần chạy trên Windows (màn hình kiosk, service, giao diện phụ huynh, script cài đặt)
> mới được kiểm tra cú pháp, **chưa được chạy thử trên máy Windows thật**. Hãy test kỹ trước khi tin cậy.

## Tính năng

- **Giới hạn giờ mỗi ngày:** mặc định 30 phút, phụ huynh chỉnh được. Chỉ tính khi con đang dùng máy.
- **Làm bài trước khi vào máy:** Toán và Tiếng Anh tự sinh theo lớp (1–12), không cần nhập ngân hàng câu hỏi.
  Số câu Toán và số câu Tiếng Anh mỗi lần cấu hình riêng. Trả lời sai thì được câu mới.
- **Khung giờ mở thả để học:** lịch theo tuần (ví dụ T2–T6 19:00–20:30). Trong khung này con dùng máy tự do,
  không phải làm bài và không bị trừ giờ.
- **Màn hình kiosk:** phủ toàn màn hình khi cần làm bài hoặc hết giờ; có đồng hồ đếm ngược và cảnh báo còn 5 phút, 1 phút.
- **Service giám sát:** chạy nền bằng quyền SYSTEM, tự bật lại kiosk nếu con tắt, tắt Task Manager cho tài khoản của con.
- **Công cụ phụ huynh:** bảo vệ bằng mật khẩu; chỉnh cài đặt, lịch giờ học, cộng thêm giờ, xem nhật ký 60 ngày gần nhất.
- **Chống chỉnh đồng hồ:** chỉnh giờ hệ thống lùi lại không làm reset hạn mức trong ngày.

## Cách hoạt động

```
 Tài khoản admin (phụ huynh)            Tài khoản con (Standard)
 ┌────────────────────────┐             ┌──────────────────────────────┐
 │ babycontrol-admin.exe  │             │ babycontrol-kiosk.exe        │
 │ cấu hình, mật khẩu,    │             │ bài tập, đếm giờ, màn hình   │
 │ cộng giờ, nhật ký      │             │ khoá / đồng hồ ở góc màn hình│
 └──────────┬─────────────┘             └───────────────▲──────────────┘
            │ ghi config.json                           │ bật lại nếu bị tắt
            ▼                                           │
   %PROGRAMDATA%\BabyControl ◄──── babycontrol-service.exe (SYSTEM)
   (chỉ admin ghi; usage\ cho kiosk ghi)       giám sát các phiên đăng nhập
```

Các bước mỗi lần con dùng máy:
1. Con đăng nhập, service bật kiosk trong phiên của con.
2. Ngoài khung giờ học: kiosk hiện bài tập. Làm đủ số câu đúng thì mở máy.
3. Khi đang dùng máy, kiosk đếm giờ. Hết hạn mức thì khoá lại và hiện "Hết giờ dùng máy hôm nay".
4. Trong khung giờ học: kiosk ẩn, không đếm giờ.
5. Phụ huynh nhập mật khẩu ở cuối màn hình khoá để cho thêm 15 phút và bỏ qua bài tập.

Tài khoản thuộc nhóm Administrators không bao giờ bị khoá hoặc đăng xuất.

## Yêu cầu

- Windows 10/11 và Python 3.10+ (bản từ python.org đã có Tkinter).
- **Hai tài khoản Windows:** tài khoản admin của phụ huynh và một tài khoản *người dùng chuẩn (Standard)* cho con.
  Nếu con dùng tài khoản admin thì công cụ không chặn được.

## Cài đặt

Chạy trong thư mục dự án, bằng PowerShell:

```powershell
# 1. Build các file .exe vào dist\ (không cần quyền admin)
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# 2. Cài service (mở PowerShell bằng "Run as administrator")
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1

# 3. Mở công cụ phụ huynh (tài khoản admin, sẽ hỏi quyền UAC)
dist\babycontrol-admin.exe
```

Lần đầu mở công cụ phụ huynh sẽ yêu cầu tạo mật khẩu. Sau đó đặt phút mỗi ngày, lớp, số câu mỗi môn và khung giờ học.
Giữ cả ba file `.exe` trong cùng một thư mục `dist\`, vì service tìm kiosk cạnh nó.

### Gỡ cài đặt

```powershell
# Run as administrator
powershell -ExecutionPolicy Bypass -File scripts\uninstall_service.ps1
```

## Cấu hình

Tất cả chỉnh qua `babycontrol-admin.exe`, gồm bốn tab:

| Tab | Nội dung |
|---|---|
| Cài đặt | Phút mỗi ngày (1–1440), lớp (1–12), số câu Toán, số câu Tiếng Anh mỗi lần (0–50, tổng ít nhất 1) |
| Giờ học | Thêm hoặc xoá khung giờ theo ngày trong tuần và giờ bắt đầu, kết thúc |
| Thời gian | Số phút đã dùng và còn lại hôm nay, cộng thêm giờ, nhật ký sử dụng |
| Mật khẩu | Đổi mật khẩu phụ huynh |

Thay đổi có hiệu lực trong khoảng 10 giây, không cần khởi động lại.

Dữ liệu nằm ở `%PROGRAMDATA%\BabyControl` (đổi bằng biến môi trường `BABYCONTROL_HOME`):
`config.json` (chỉ admin ghi được, mật khẩu lưu dạng băm PBKDF2) và thư mục `usage\` (số liệu giờ).

## Cấu trúc mã nguồn

| Đường dẫn | Vai trò |
|---|---|
| `babycontrol/config.py` | Cấu hình, khung giờ học, mật khẩu, quyền thư mục |
| `babycontrol/exercises.py` | Sinh bài Toán, Tiếng Anh và phiên làm bài |
| `babycontrol/timer.py` | Đếm giờ theo ngày, nhật ký, quyết định quyền truy cập |
| `babycontrol/controller.py` | Logic điều khiển kiosk, tách khỏi giao diện |
| `babycontrol/kiosk.py` | Giao diện Tkinter toàn màn hình cho tài khoản con |
| `babycontrol/watchdog.py` | Logic quyết định của service (bật lại kiosk, đăng xuất) |
| `babycontrol/service.py` | Windows service (pywin32) |
| `babycontrol/admin.py` | Logic và giao diện công cụ phụ huynh |
| `scripts/` | Build PyInstaller, cài và gỡ service, file entry |
| `tests/` | Test tự động (pytest) |

## Phát triển

```bash
bash init.sh --verify    # tạo .venv, cài phụ thuộc, chạy pytest
```

Test chạy được trên macOS và Linux. Các module gọi API Windows (`service.py`, phần giao diện Tk) chỉ được
kiểm tra cú pháp ở đó. Dự án dùng lean-ai-harness (`lah`) để quản lý hàng đợi công việc trong `state/`;
xem `AGENTS.md`.

## Hạn chế đã biết

- Kiosk chạy bằng tài khoản của con và ghi số liệu giờ vào `usage\usage.json`, nên một đứa trẻ rành kỹ thuật
  có thể sửa file này. Cách siết chặt hơn là chuyển việc đếm giờ vào service.
- Nếu `babycontrol-kiosk.exe` không chạy được trong phiên của con quá khoảng 30 giây, service đăng xuất phiên đó.
  Nếu thiếu file kiosk, service không làm gì để tránh đăng xuất liên tục khi cài lỗi.
- Ctrl+Alt+Del vẫn dùng được (đăng xuất, khoá máy). Task Manager bị tắt bằng chính sách người dùng.
- Danh sách từ vựng Tiếng Anh còn nhỏ (khoảng 16–18 từ mỗi nhóm lớp); bài Toán lớp 5 trở lên theo chương trình phổ thông ước lượng.
