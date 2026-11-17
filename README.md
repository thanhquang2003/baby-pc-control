# BabyControl

Công cụ quản lý giờ dùng máy tính Windows cho trẻ em, viết bằng Python.

> **Trạng thái:** phần logic (cấu hình, sinh bài, đếm giờ, giám sát) đã có test tự động.
> Phần chạy trên Windows (màn hình kiosk, service, giao diện phụ huynh, script cài đặt)
> mới được kiểm tra cú pháp, **chưa được chạy thử trên máy Windows thật**. Hãy test kỹ trước khi tin cậy.

## Tính năng

- **Giới hạn giờ mỗi ngày:** mặc định 30 phút, phụ huynh chỉnh được. Chỉ tính khi con đang dùng máy.
- **Làm bài trước khi vào máy:** Toán và Tiếng Anh tự sinh theo lớp (1–12), không cần nhập ngân hàng câu hỏi.
  Số câu Toán và số câu Tiếng Anh mỗi lần cấu hình riêng. Mỗi môn phải đủ số câu **đúng** đã đặt; trả lời sai thì không tính
  và được bù ngay bằng một câu khác **cùng môn**, nên con không học lệch. Màn hình hiện tiến độ từng môn (ví dụ "Toán 1/3 · Tiếng Anh 0/2").
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
5. Bố mẹ nhập mật khẩu và **tự chọn số phút** (1–720, mặc định 30) ở cuối màn hình khoá, rồi bấm:
   **"Thêm giờ cho con"** (cộng số phút đó cho con và bỏ qua bài tập) hoặc **"Bố mẹ dùng máy"**
   (chế độ bố mẹ trong số phút đã chọn: không khoá, không đếm giờ; bấm "Kết thúc" ở góc màn hình để quay lại giám sát sớm).

Tất cả các tài khoản, kể cả tài khoản quản trị, đều được giám sát. Bố mẹ dùng máy bằng cách vào chế độ bố mẹ.

## Cài đặt (dành cho người không rành máy tính)

Cần máy Windows 10/11 (64-bit). Không cần cài gì trước.

**Cách nhanh (khuyên dùng): bản build sẵn, cài trong khoảng 1 phút, không cần Internet hay Python.**

1. Vào trang **Releases** của dự án trên GitHub, tải file `BabyControl-<phiên bản>-windows-x64.zip` ở mục *Assets*
   (không phải "Source code"). Các bản này do GitHub Actions tự build trên Windows; có kèm file `.sha256` để đối chiếu nếu muốn.

*Cách chậm: tự build trên máy (khoảng 5–10 phút, cần Internet).* Bấm nút xanh **Code** → **Download ZIP** ở trang chính
của dự án; trình cài đặt sẽ tự cài Python và tự build.

2. Mở thư mục *Downloads*, bấm chuột phải file ZIP vừa tải → **Extract All** (Giải nén) → **Extract**.
3. Mở thư mục vừa giải nén, **nhấp đúp file `CAI_DAT.bat`**.
   - Nếu Windows báo "Windows protected your PC": bấm **More info** → **Run anyway**.
   - Khi hộp thoại xin quyền hiện ra, bấm **Yes** (Có). Nếu máy hỏi mật khẩu quản trị thì nhập mật khẩu quản trị.
4. Chờ đến khi thấy chữ **HOÀN TẤT CÀI ĐẶT** (chữ xanh), **đừng tắt cửa sổ** trong lúc chờ. Cách nhanh mất khoảng 1 phút, cách chậm 5–10 phút.
5. Cửa sổ **BabyControl** tự mở ra: tạo **mật khẩu phụ huynh**, rồi đặt số phút mỗi ngày, lớp của con,
   số câu hỏi mỗi môn và các khung giờ học tự do. Xong là máy đã được bảo vệ.
   Trước khi tạo mật khẩu, máy **không bị khoá** (chỉ hiện dòng nhắc nhỏ ở góc màn hình). Trong lúc cửa sổ
   BabyControl còn mở, máy cũng không bị khoá (góc màn hình ghi "Chế độ bố mẹ"). **Khi bạn đóng cửa sổ**, bảo vệ mới bắt đầu
   và màn hình bài tập hiện ra. Nếu cửa sổ bị tắt đột ngột, bảo vệ tự bật lại sau tối đa 3 phút.

Sau này, mở lại cài đặt bằng biểu tượng **BabyControl - Phu huynh** trên màn hình nền.
Cài lại lên bản mới chỉ cần chạy lại
`CAI_DAT.bat`: cài đặt và nhật ký cũ được giữ nguyên.

Nếu có lỗi, cửa sổ sẽ hiện chữ đỏ và ghi chi tiết vào file `install.log` cạnh `CAI_DAT.bat`; gửi file đó cho người hỗ trợ.

**Gỡ cài đặt:** nhấp đúp `GO_CAI_DAT.bat` (hoặc Start → BabyControl → Gỡ cài đặt). Cần nhập mật khẩu phụ huynh
nên con không tự gỡ được.

> Lưu ý: phần mềm diệt virus đôi khi cảnh báo nhầm file `.exe` tạo bằng PyInstaller. Nếu bị chặn, hãy cho phép
> thư mục `C:\Program Files\BabyControl`.

### Cài đặt thủ công (cho người rành kỹ thuật)

Cần Python 3.10+ có Tkinter. Trong PowerShell, thư mục dự án:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1            # tạo .exe vào dist\
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1  # Run as administrator
dist\babycontrol-admin.exe                                            # công cụ phụ huynh (UAC)
```

Giữ cả ba file `.exe` trong cùng một thư mục vì service tìm kiosk cạnh nó.
Gỡ thủ công: `scripts\uninstall_service.ps1` (Run as administrator).

## Yêu cầu

- Windows 10/11 64-bit. Cần Internet khi cài chỉ với "cách chậm" (tự build); bản build sẵn thì không.
- Một tài khoản Windows là đủ (bố mẹ và con dùng chung). Có thể dùng tài khoản thường hoặc quản trị.
  Tài khoản thường an toàn hơn: con không tự cài hoặc gỡ được chương trình.

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
| `CAI_DAT.bat`, `GO_CAI_DAT.bat` | Nhấp đúp để cài hoặc gỡ (gọi `scripts/setup.ps1`, `scripts/remove.ps1`) |
| `scripts/` | Trình cài đặt PowerShell, build PyInstaller, cài và gỡ service, file entry |
| `tests/` | Test tự động (pytest) |

## Phát triển

```bash
bash init.sh --verify    # tạo .venv, cài phụ thuộc, chạy pytest
```

Test chạy được trên macOS và Linux. Các module gọi API Windows (`service.py`, phần giao diện Tk) chỉ được
kiểm tra cú pháp ở đó. Dự án dùng lean-ai-harness (`lah`) để quản lý hàng đợi công việc trong `state/`;
xem `AGENTS.md`.

### GitHub Actions

- **CI** (`.github/workflows/ci.yml`): chạy toàn bộ test trên `windows-latest` cho mỗi push và pull request vào `main`.
- **Release build** (`.github/workflows/release.yml`): build 3 file `.exe` bằng PyInstaller trên Windows, đóng gói
  `BabyControl-<phiên bản>-windows-x64.zip` (gồm `.exe`, `CAI_DAT.bat`, `GO_CAI_DAT.bat`, trình cài và `HUONG_DAN.txt`)
  cùng file `.sha256`.
  - Đẩy tag `v*` (ví dụ `git tag -a v2.2.0 -m "..." && git push origin v2.2.0`): ZIP được đính vào GitHub Release của tag đó
    (tạo Release mới nếu chưa có).
  - Chạy tay (*Actions → Release build → Run workflow*): chỉ chạy thử, ZIP nằm trong *Artifacts* của lần chạy, không công bố gì.

## Hạn chế đã biết

- Mã hoá chỉ chặn việc sửa file thông thường. Người dùng thành thạo kỹ thuật và có quyền quản trị vẫn có thể
  xoá cả file lẫn khoá (kiosk sẽ khoá máy nếu phát hiện, nhưng công cụ phụ huynh cho tạo lại cài đặt).
  Cách siết chặt hơn là chuyển việc đếm giờ vào service.
- Nếu `babycontrol-kiosk.exe` không chạy được trong phiên của con quá khoảng 30 giây, service đăng xuất phiên đó.
  Nếu thiếu file kiosk, service không làm gì để tránh đăng xuất liên tục khi cài lỗi.
- Ctrl+Alt+Del vẫn dùng được (đăng xuất, khoá máy). Task Manager bị tắt bằng chính sách người dùng.
- Danh sách từ vựng Tiếng Anh còn nhỏ (khoảng 16–18 từ mỗi nhóm lớp); bài Toán lớp 5 trở lên theo chương trình phổ thông ước lượng.
