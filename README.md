# 🎬 Shorts Maker – Tool làm video Shorts tự động (tiếng Nhật)

Tool tự làm video dọc kiểu “kể chuyện thể thao” giống video mẫu:
**nền trắng, ảnh/video ở giữa, sub chữ đen đậm ở trên và dưới khung**, có giọng đọc AI.

```
Nhập title + thời lượng
  → Claude CLI viết content (tiếng Nhật)  → BẠN DUYỆT / sửa
  → OmniVoice đọc content (giọng mẫu / mô tả giọng / ủy quyền cho tool)
  → Tự tìm ảnh (70%, mỗi ảnh 4–5 giây) + video (30%, tự cắt đoạn hay)  → BẠN XEM LẠI / đổi
  → Chọn nhạc nền → Xuất video 1080x1920
```

---

## 1. Cài đặt (chỉ làm 1 lần)

Cần: **Windows 10/11 + card NVIDIA** (nên có VRAM 8GB trở lên).

1. **Cập nhật driver NVIDIA** mới nhất: https://www.nvidia.com/Download/index.aspx
2. **Cài Python 3.11**: https://www.python.org/downloads/release/python-3119/
   → khi cài nhớ tick ô **“Add python.exe to PATH”**.
3. **Cài Claude CLI** (dùng gói Claude của bạn, không cần API key). Mở **PowerShell** và chạy:
   ```
   irm https://claude.ai/install.ps1 | iex
   ```
   Sau đó gõ `claude`, rồi đăng nhập tài khoản Claude một lần.
4. **Tải tool này về**. Bấm nút *Code → Download ZIP* trên GitHub, rồi giải nén
   (đặt ở thư mục **không có dấu**, ví dụ `D:\ShortsMaker`).
5. Bấm đúp **`install.bat`** và đợi khoảng 10–20 phút (tải PyTorch, OmniVoice, font).
   Nếu máy chưa có FFmpeg thì tool tự cài. Cài xong thì đóng cửa sổ và chạy lại `install.bat` một lần nữa cho chắc.

> Lần đầu đọc giọng, tool sẽ tự tải model OmniVoice (vài GB) nên sẽ chờ lâu hơn một chút.

## 2. Sử dụng

Bấm đúp **`run.bat`**, trình duyệt sẽ tự mở trang `http://127.0.0.1:7860`.

### Bước 1 – Content
- Ở cột trái, nhập **Title** (nếu có) và/hoặc **Chủ đề**, chọn **thời lượng**, rồi bấm **Tạo & viết content**.
- Claude sẽ tra cứu web và viết kịch bản tiếng Nhật, chia sẵn từng cảnh.
- Bạn sửa trực tiếp nội dung:
  - **Ô Sub**: mỗi dòng là một lần hiện chữ, dấu `/` là xuống dòng.
    Lần hiện thứ 1, 3, 5… nằm *trên* khung, lần 2, 4, 6… hiện thêm *dưới* khung (giống video mẫu).
  - **Câu để đọc**: câu OmniVoice sẽ đọc. Tên người và số nên viết bằng hiragana để đọc chuẩn.
  - Bấm nhãn **🖼 Ảnh / 🎞 Video** để đổi loại cảnh. Nút **⚖️** tự chia lại tỉ lệ 70/30.
  - Nếu chưa ưng, nhập góp ý (tiếng Việt cũng được) rồi bấm **Viết lại theo góp ý**.
- Bấm **✅ Duyệt content**.

### Bước 2 – Giọng đọc
- **Giọng mẫu**: upload file giọng 3–10 giây (tiếng Nhật, rõ, không có nhạc). Giọng được lưu lại để dùng cho các video sau.
- **Mô tả giọng**: chọn giới tính, độ tuổi, cao độ.
- **Ủy quyền cho tool**: AI tự chọn giọng hợp với chủ đề.
- Bấm **🎙️ Đọc toàn bộ**, nghe thử từng cảnh, cảnh nào chưa hay thì bấm **Đọc lại**.

### Bước 3 – Ảnh & video
- Bấm **🔎 Tự tìm…**. Tool sẽ:
  - Tìm ảnh (DuckDuckGo, hoặc Google nếu bạn nhập key trong Cài đặt). Mỗi ảnh hiện 4–5 giây và có zoom nhẹ.
  - Tìm video trên YouTube, tải về, tự chấm điểm **chuyển động + tiếng khán giả + độ nét**,
    nhờ Claude xem các đoạn tốt nhất rồi chọn đoạn **hợp với câu đang đọc**.
- Click ảnh ứng viên để thêm hoặc bỏ. Với video, click khung hình để đổi sang đoạn khác.
- Có thể **dán link** YouTube / TikTok / X / Facebook / Instagram, hoặc **tải ảnh/video của bạn lên**.

### Bước 4 – Xuất video
- Upload nhạc nền (được lưu lại để dùng cho video sau), chỉnh âm lượng, rồi bấm **🎬 Xuất video**.
- Video nằm ở `projects\<mã video>\render\<title>.mp4`, hoặc tải trực tiếp trên trang.

## 3. Cài đặt thêm (⚙️ ở góc dưới bên trái)
- **Model Claude**: để trống hoặc ghi `opus` / `sonnet`.
- **Google API key + cx**: tìm ảnh qua Google (tùy chọn).
- **Bộ mã hóa**: mặc định tự dùng card NVIDIA (NVENC) cho nhanh.
- **Cỡ chữ / font sub**, số bước tạo giọng (16 = nhanh, 32 = hay).

## 4. Lỗi thường gặp
| Lỗi | Cách sửa |
|---|---|
| “Không thấy GPU” | Cập nhật driver NVIDIA. Nếu card đời cũ (GTX 10xx), sửa `cu128` thành `cu126` trong `install.bat` rồi cài lại |
| “Không tìm thấy Claude CLI” | Làm lại bước 3 phần cài đặt, rồi mở lại `run.bat` |
| Không tìm được video | Sửa từ khóa ngắn gọn hơn, hoặc dán link trực tiếp. Có thể chạy `.venv\Scripts\pip install -U yt-dlp` để cập nhật |
| Đọc sai tên người | Sửa ô “Câu để đọc” thành hiragana rồi bấm Đọc lại |

## Cấu trúc code
```
app/
  main.py        server web + API
  script_gen.py  viết content bằng Claude CLI
  tts.py         đọc giọng OmniVoice (clone / design / auto)
  media.py       tìm & tải ảnh, video
  highlight.py   tự tìm đoạn video hay
  render.py      ghép video bằng FFmpeg (layout + sub ASS + nhạc nền)
  static/        giao diện web
library/voices   giọng mẫu đã upload
library/bgm      nhạc nền đã upload
projects/        mỗi video một thư mục
```
