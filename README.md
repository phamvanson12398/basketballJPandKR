# 🎬 Shorts Maker – Tool làm video Shorts tự động (tiếng Nhật)

Làm được 4 thể loại: **⚾ Thể thao**, **👤 Tiểu sử người nổi tiếng**, **📰 Tin tức mới nhất** (theo quốc gia hoặc thế giới), **💡 Chủ đề chung** (kiến thức, chuyện lạ...).

Tool tự làm video dọc kiểu “kể chuyện thể thao” giống video mẫu:
**nền trắng, ảnh/video 16:9 ở giữa, sub chữ đen đậm ở trên và dưới khung**, có giọng đọc AI.
Content viết bằng **tiếng Nhật chuẩn (標準語)** để người Nhật ở vùng nào cũng hiểu.

```
Nhập title + thời lượng
  → Claude CLI viết content (tiếng Nhật chuẩn 標準語)  → BẠN DUYỆT / sửa
  → OmniVoice đọc content (giọng mẫu / mô tả giọng / ủy quyền cho tool)
  → Tự tìm ảnh 16:9 (70%, mỗi ảnh 4–5 giây) + video (30%, tự cắt đoạn hay)  → BẠN XEM LẠI / đổi
  → Chọn nhạc nền → Xuất video 1080x1920
  → Tạo title + hashtag TikTok → copy đi đăng
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
- Ở cột trái, chọn **Thể loại**, nhập **Title** (nếu có) và/hoặc **Chủ đề**, chọn **thời lượng** và **tỉ lệ ảnh/video**
  (kéo thanh trượt, mặc định 70% ảnh / 30% video; tool nhớ lựa chọn lần trước), rồi bấm **Tạo & viết content**.
- Claude sẽ tra cứu web và viết kịch bản tiếng Nhật, chia sẵn từng cảnh.
- **Tin tức**: chọn **quốc gia** (hoặc 🌍 Thế giới, hoặc tự nhập tên nước), **trong vòng** (24 giờ / 3 ngày / 1 tuần / 1 tháng)
  và **lĩnh vực**. Bấm **🔎 Quét tin mới nhất** để Claude đọc báo (cả báo tiếng địa phương lẫn Nhật/Anh) và đưa ra 8 tin nóng
  kèm tóm tắt tiếng Việt → bấm chọn 1 tin. Hoặc để trống chủ đề, AI tự chọn tin nóng nhất.
  Sau khi viết, mục **📎 Nguồn tin** hiện các bài báo AI đã dùng để bạn bấm vào kiểm tra.
  Ảnh/video cho tin tức được ưu tiên tìm loại **mới đăng gần đây**.
- Bạn sửa trực tiếp nội dung:
  - **Ô Sub**: mỗi dòng là một lần hiện chữ, dấu `/` là xuống dòng.
    Lần hiện thứ 1, 3, 5… nằm *trên* khung, lần 2, 4, 6… hiện thêm *dưới* khung (giống video mẫu).
  - **Câu để đọc**: câu OmniVoice sẽ đọc. Tên người và số nên viết bằng hiragana để đọc chuẩn.
  - Bấm nhãn **🖼 Ảnh / 🎞 Video** để đổi loại cảnh. Kéo thanh **Mục tiêu** để đổi tỉ lệ ảnh/video, tool tự chia lại ngay.
  - Nếu chưa ưng, nhập góp ý (tiếng Việt cũng được) rồi bấm **Viết lại theo góp ý**.
- Bấm **✅ Duyệt content**.

### Bước 2 – Giọng đọc
- **Giọng mẫu**: upload file giọng 3–10 giây (tiếng Nhật, rõ, không có nhạc). Giọng được lưu lại để dùng cho các video sau.
- **Mô tả giọng**: chọn giới tính, độ tuổi, cao độ.
- **Ủy quyền cho tool**: AI tự chọn giọng hợp với chủ đề.
- Bấm **🎙️ Đọc toàn bộ**, nghe thử từng cảnh, cảnh nào chưa hay thì bấm **Đọc lại**.

### Bước 3 – Ảnh & video
- Bấm **🔎 Tự tìm…**. Tool sẽ:
  - Tìm ảnh **miễn phí, không cần key** từ DuckDuckGo + Bing + Yahoo! JAPAN. **Chỉ lấy ảnh 16:9**, hiện nguyên vẹn,
    không cắt, không làm mờ. Mỗi ảnh hiện 4–5 giây.
  - Nếu vẫn thiếu ảnh 16:9, tool tự chụp **khung hình nét nhất** từ video YouTube liên quan (luôn đúng 16:9).
  - Tìm video trên YouTube, tải về, tự chấm điểm **chuyển động + tiếng khán giả + độ nét**,
    nhờ Claude xem các đoạn tốt nhất rồi chọn đoạn **hợp với câu đang đọc**.
- Click ảnh ứng viên để thêm hoặc bỏ. Với video, click khung hình để đổi sang đoạn khác.
- Có thể **dán link** YouTube / TikTok / X / Facebook / Instagram, hoặc **tải ảnh/video của bạn lên**.

### Bước 4 – Xuất video
- Upload nhạc nền (được lưu lại để dùng cho video sau), chỉnh âm lượng, rồi bấm **🎬 Xuất video**.
- Video nằm ở `projects\<mã video>\render\<title>.mp4`, hoặc tải trực tiếp trên trang.

### Bước 5 – Đăng TikTok
- Bấm **✨ Tạo title & hashtag**. Claude đọc content của video rồi đưa ra **5 title** (mỗi cái một kiểu: câu hỏi, con số,
  sự thật bất ngờ…, có dịch tiếng Việt) và **10–12 hashtag** chia nhóm: rộng / chủ đề / cụ thể / đề xuất (#おすすめ #fyp).
- Bấm chọn title, bấm hashtag để bật/tắt, thêm hashtag của bạn, rồi bấm **📋 Copy tất cả** để dán vào TikTok.

## 3. Cài đặt thêm (⚙️ ở góc dưới bên trái)
- **Model Claude**: để trống hoặc ghi `opus` / `sonnet`.
- **Nguồn tìm ảnh**: bật/tắt DuckDuckGo, Bing, Yahoo! JAPAN (đều miễn phí).
- **Bộ mã hóa**: mặc định tự dùng card NVIDIA (NVENC) cho nhanh.
- **Chiều cao khung ảnh & video** (dùng chung cho cả ảnh và video; 608 = đúng 16:9) và **khoảng cách chữ ↔ khung**.
- **Cỡ chữ / font sub**, số bước tạo giọng (16 = nhanh, 32 = hay).
- **Zoom nhẹ ảnh**: mặc định tắt (bật thì ảnh sẽ bị che mất một chút mép).

## 4. Lỗi thường gặp
| Lỗi | Cách sửa |
|---|---|
| “Không thấy GPU” | Cập nhật driver NVIDIA. Nếu card đời cũ (GTX 10xx), sửa `cu128` thành `cu126` trong `install.bat` rồi cài lại |
| “Không tìm thấy Claude CLI” | Làm lại bước 3 phần cài đặt, rồi mở lại `run.bat` |
| Không tìm được ảnh 16:9 | Đổi từ khóa rộng hơn (VD: chỉ tên cầu thủ + đội), tool cũng sẽ tự chụp ảnh từ video YouTube |
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
