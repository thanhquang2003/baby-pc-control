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
- **Một tài khoản dùng chung:** bố mẹ và con dùng chung một tài khoản Windows. Bố mẹ nhập mật khẩu ở màn hình khoá
  để vào **chế độ bố mẹ** (dùng máy tự do vài giờ, không bị đếm giờ).
- **Service giám sát:** chạy nền bằng quyền SYSTEM, tự bật lại kiosk nếu bị tắt, chặn Task Manager (bật/tắt được).
- **Công cụ phụ huynh:** bảo vệ bằng mật khẩu; chỉnh cài đặt, lịch giờ học, cộng thêm giờ, xem nhật ký 60 ngày gần nhất.
- **Chống chỉnh đồng hồ:** chỉnh giờ hệ thống lùi lại không làm reset hạn mức trong ngày.

## Cách hoạt động

```
 Công cụ phụ huynh (có mật khẩu)        Màn hình kiosk (cùng tài khoản)
 ┌────────────────────────┐             ┌──────────────────────────────┐
 │ babycontrol-admin.exe  │             │ babycontrol-kiosk.exe        │
 │ cấu hình, mật khẩu,    │             │ bài tập, đếm giờ, màn hình   │
 │ cộng giờ, nhật ký      │             │ khoá / đồng hồ ở góc màn hình│
 └──────────┬─────────────┘             └───────────────▲──────────────┘
            │ ghi config.dat (mã hoá)                   │ bật lại nếu bị tắt
            ▼                                           │
   %PROGRAMDATA%\BabyControl ◄──── babycontrol-service.exe (SYSTEM)
   (chỉ admin ghi; usage\ cho kiosk ghi)       giám sát các phiên đăng nhập
```

Các bước mỗi lần con dùng máy:
1. Ai đăng nhập cũng được service bật kiosk trong phiên đó.
2. Ngoài khung giờ học: kiosk hiện bài tập. Làm đủ số câu đúng thì mở máy.
3. Khi đang dùng máy, kiosk đếm giờ. Hết hạn mức thì khoá lại và hiện "Hết giờ dùng máy hôm nay".
4. Trong khung giờ học: kiosk ẩn, không đếm giờ.
5. Bố mẹ nhập mật khẩu ở cuối màn hình khoá: **"Thêm 15 phút"** (bỏ qua bài tập) hoặc **"Bố mẹ dùng máy 2 giờ"**
   (chế độ bố mẹ: không khoá, không đếm giờ; bấm "Kết thúc" ở góc màn hình để quay lại giám sát sớm).

Tất cả các tài khoản, kể cả tài khoản quản trị, đều được giám sát. Bố mẹ dùng máy bằng cách vào chế độ bố mẹ.

## Yêu cầu

- Windows 10/11 và Python 3.10+ (bản từ python.org đã có Tkinter).
- Một tài khoản Windows là đủ (bố mẹ và con dùng chung). Có thể dùng tài khoản thường hoặc quản trị.
  Tài khoản thường an toàn hơn: con không tự cài hoặc gỡ được chương trình.

## Cài đặt

Chạy trong thư mục dự án, bằng PowerShell:

```powershell
# 1. Build các file .exe vào dist\ (không cần quyền admin)
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# 2. Cài service (mở PowerShell bằng "Run as administrator")
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1

# 3. Mở công cụ phụ huynh (sẽ hỏi quyền quản trị UAC)
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
| Cài đặt | Phút mỗi ngày (1–1440), lớp (1–12), số câu Toán, số câu Tiếng Anh mỗi lần (0–50, tổng ít nhất 1), chặn Task Manager |
| Giờ học | Thêm hoặc xoá khung giờ theo ngày trong tuần và giờ bắt đầu, kết thúc |
| Thời gian | Số phút đã dùng và còn lại hôm nay, cộng thêm giờ, nhật ký sử dụng |
| Mật khẩu | Đổi mật khẩu phụ huynh |

Thay đổi có hiệu lực trong khoảng 10 giây, không cần khởi động lại.

Dữ liệu nằm ở `%PROGRAMDATA%\BabyControl` (đổi bằng biến môi trường `BABYCONTROL_HOME`):
`config.dat` (cấu hình) và thư mục `usage\` (số liệu giờ). Cả hai được **mã hoá và có chữ ký** (Fernet),
khoá nằm trong `key.bin` được bọc bằng DPAPI của Windows, nên không sửa được bằng Notepad.
Mật khẩu phụ huynh lưu dạng băm PBKDF2. Mỗi file có một bản sao `.bak`.
Nếu file bị sửa, hỏng hoặc bị xoá sau khi đã cài đặt, kiosk **khoá máy** (không tự về mặc định) cho đến khi phụ huynh
mở công cụ phụ huynh và tạo lại cài đặt; số liệu giờ hỏng thì coi như hôm nay đã hết giờ.
Dữ liệu từ bản v1 (`config.json`, `usage.json`) được tự chuyển sang dạng mã hoá.

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

- Mã hoá chỉ chặn việc sửa file thông thường. Người dùng thành thạo kỹ thuật và có quyền quản trị vẫn có thể
  xoá cả file lẫn khoá (kiosk sẽ khoá máy nếu phát hiện, nhưng công cụ phụ huynh cho tạo lại cài đặt).
  Cách siết chặt hơn là chuyển việc đếm giờ vào service.
- Nếu `babycontrol-kiosk.exe` không chạy được trong phiên của con quá khoảng 30 giây, service đăng xuất phiên đó.
  Nếu thiếu file kiosk, service không làm gì để tránh đăng xuất liên tục khi cài lỗi.
- Ctrl+Alt+Del vẫn dùng được (đăng xuất, khoá máy). Task Manager bị tắt bằng chính sách người dùng.
- Danh sách từ vựng Tiếng Anh còn nhỏ (khoảng 16–18 từ mỗi nhóm lớp); bài Toán lớp 5 trở lên theo chương trình phổ thông ước lượng.
