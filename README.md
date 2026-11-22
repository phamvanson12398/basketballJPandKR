# 🎬 Shorts Maker – Tool làm video Shorts tự động (tiếng Nhật / tiếng Hàn)

**Ngôn ngữ video: 🇯🇵 tiếng Nhật hoặc 🇰🇷 tiếng Hàn.** Chọn tiếng nào thì tool đóng vai người viết / biên tập viên
nước đó, nói với khán giả nước đó: content, giọng đọc, sub, title và hashtag TikTok đều theo ngôn ngữ ấy.
Với tin tức: tiếng Nhật → phát thanh viên Nhật (quy đổi yên, giờ Nhật, liên hệ Nhật Bản);
tiếng Hàn → phát thanh viên Hàn kiểu KBS/MBC (합니다체, quy đổi won, giờ Hàn, liên hệ Hàn Quốc).

Làm được 5 thể loại: **⚾ Thể thao**, **👤 Tiểu sử người nổi tiếng**, **🏆 Top / Xếp hạng**, **📰 Tin tức mới nhất** (theo quốc gia hoặc thế giới), **💡 Chủ đề chung** (kiến thức, chuyện lạ...).

Tool tự làm video dọc kiểu “kể chuyện thể thao” giống video mẫu:
**nền trắng, ảnh/video 16:9 ở giữa, sub chữ đen đậm ở trên và dưới khung**, có giọng đọc AI.
Content viết bằng **tiếng Nhật chuẩn (標準語)** để người Nhật ở vùng nào cũng hiểu.

```
Nhập title + thời lượng
  → Claude CLI viết content (tiếng Nhật chuẩn 標準語)  → BẠN DUYỆT / sửa
  → OmniVoice đọc content (giọng mẫu / mô tả giọng / ủy quyền cho tool)
  → Tự tìm ảnh 16:9 (70%, ~3 giây đổi ảnh) + video (30%, tự cắt nhiều đoạn hay)  → BẠN XEM LẠI / đổi
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

> 🔔 **Bật thông báo**: bấm nút **🔔 Bật thông báo** ở thanh trên cùng (trình duyệt hỏi thì chọn *Cho phép*).
> Mỗi khi tool làm xong một việc (viết content, đọc giọng, tìm ảnh/video, xuất video, tạo hashtag, gợi ý ý tưởng, quét tin),
> bạn nhận **thông báo của Windows + tiếng "ting ting" + tên tab nhấp nháy "✅ Xong!"**, kể cả khi đang xem tab khác
> hoặc đang mở video khác. Bấm vào thông báo là mở đúng video, đúng bước.

### 🏅 Lĩnh vực: Bóng chày / Bóng rổ / 🤼 Sumo / Bóng đá / 🎤 Idol Nhật / 🎶 K-pop / 😂 Hài – M-1
Khi tạo video (trừ Tin tức), chọn **Lĩnh vực**. **🎤 Idol Nhật**: tên thành viên luôn có cách đọc, thứ hạng dựa trên
số lần center / tuyển chọn / tổng tuyển cử / phát ngôn chính thức, không viết tin đồn tình cảm hay scandal; nhạc nền riêng
**J-pop sôi động / Ballad**. Top có thêm Top 4, 6, 8.
**🎶 K-pop**: tên nhóm/thành viên đúng (hangul cho video tiếng Hàn, katakana cho video tiếng Nhật), số liệu từ
chương trình âm nhạc / Circle / Hanteo / MelOn / Billboard, không tin đồn hẹn hò hay suy đoán tranh chấp công ty;
nhạc nền riêng **Dance / Hip-hop**.
**😂 Hài / M-1**: tên nhóm hài/nghệ sĩ có cách đọc, số liệu từ M-1 / King of Conte (năm vô địch, điểm giám khảo,
năm cuối ラストイヤー, vòng phục hồi), không chép nguyên kịch bản tiết mục, không tin đồn scandal; nhạc nền riêng
**Vui nhộn / Hồi hộp M-1**.
**Idol Nhật và K-pop luôn dùng nền trắng** ở mọi thể loại (Top, Tiểu sử, Tin tức… đều đổi sang bản nền trắng, chữ tối). Mỗi môn có hướng dẫn riêng cho AI (thuật ngữ, cách tra số liệu,
từ khóa tìm ảnh/video). Riêng **Sumo**: dùng đúng thuật ngữ (横綱・大関・場所・決まり手…), tên võ sĩ (四股名) luôn được
viết cách đọc bằng hiragana / hangul để giọng đọc chuẩn, và có nhạc nền riêng **trống Taiko / Truyền thống** (shamisen, sáo).
Riêng **Bóng đá**: thuật ngữ chuẩn (ハットトリック・VAR・移籍金…), tin chuyển nhượng chưa chốt luôn ghi là "theo báo chí",
tên cầu thủ/CLB nước ngoài có cách đọc, ưu tiên góc cầu thủ Nhật/Hàn ở châu Âu, và nhạc nền riêng **Sân vận động / Hào hùng**
(vỗ tay cổ động, tiếng khán đài, kèn đồng).

### 🇰🇷 Bố cục kiểu Shorts Hàn Quốc (video tiếng Hàn, thể loại Thể thao)
Nền đen · tiêu đề 2 dòng cố định (vàng / đỏ) · ảnh lớn gần vuông (tự cắt vào chỗ có người) · phụ đề trắng viền đen
1 cụm ngắn đè giữa ảnh · hộp số liệu (타율… / 평균자책점…) khi nhắc tới thành tích · cảnh so sánh 2 người tự chia đôi khung.
Tự dùng cho video tiếng Hàn + Thể thao (trừ Idol/K-pop giữ nền trắng); chọn tay ở ô 🎨 Bố cục cho video khác.
Chiều cao khung (ảnh + video) chỉnh ở ⚙️ Cài đặt → **Chiều cao khung – bố cục Hàn Quốc** (mẫu 1140, tối đa 1500).

### 🤼⚽ Bố cục Sumo / Bóng đá (thể loại Thể thao)
Vẫn là bố cục bóng chày (kể chuyện, sub đen trên/dưới khung), thêm nhãn riêng **chỉ ở cảnh nói về trận đấu**:
- **Sumo**: nền giấy washi + vạch vàng, nhãn giải đấu (九州場所 13日目), thẻ cấp bậc (横綱…), biển tên + thành tích,
  con dấu đỏ ghi kỹ thuật thắng (寄り切り…) đóng xuống ở cảnh quyết định thắng thua.
- **Bóng đá**: nền sọc cỏ nhạt, nhãn giải đấu, bảng tỉ số kiểu truyền hình (tự đổi số), biển tên cầu thủ + CLB + số áo.
Cảnh kể tuổi thơ / hậu trường để trống → chỉ có ảnh + sub như bóng chày. Sửa nhãn ở khung 🖥️ và ô nhãn của từng cảnh.

### 💡 Chưa biết làm gì? Bấm "Gợi ý ý tưởng video"
Nút vàng ở góc trên bên trái. Chọn ngôn ngữ, thể loại, gõ ngách kênh (mặc định: bóng rổ Nhật – Hàn) → Claude tra cứu
chủ đề đang hot và đưa ra 5–15 ý tưởng (title, lý do nên làm, 🔥 đang hot hay ♻️ không lỗi thời).
Bấm **🎬 Làm video này** → form tạo video tự điền sẵn, chỉ cần bấm Tạo.

### 🏆 Top / Xếp hạng
Chọn thể loại Top, chọn Top 3 / 5 / 7 / 10. AI đếm ngược từ hạng cuối lên hạng 1, có số liệu cho từng hạng,
và giữ lại hạng 1 tới cuối video.

### 📋 Điểm tin
Ở thể loại Tin tức, chọn **Số tin trong 1 video: 3 hoặc 5**. Sau khi quét tin, bấm chọn nhiều tin (hoặc để trống → AI tự chọn).
Video có lời mở đầu, câu chuyển tin ("Tiếp theo là…", "Cuối cùng là…"), mỗi tin 2–3 cảnh.

### 🎨 Bố cục chuyển động theo thể loại
| Thể loại | Bố cục |
|---|---|
| ⚾ Thể thao | Bố cục gốc giống video mẫu (nền trắng, sub đen trên/dưới khung) |
| 📰 Tin tức | Nền navy, dải đỏ NEWS · quốc gia · ngày trượt vào, nhãn 速報 nhấp nháy, ô tiêu đề trắng, nguồn ở góc ảnh, phụ đề trong hộp trắng bật ra |
| 🏆 Top | Nền đen, tiêu đề TOP vàng, chữ "第N位" nảy ra giữa khung rồi thành huy hiệu vàng/bạc/đồng, dải tên vàng trượt vào, hạng 1 chớp vàng |
| 👤 Tiểu sử | Nền kem, ảnh viền trắng rơi nhẹ vào khung, năm chạy số, chương hiện từng chữ |
| 💡 Chủ đề chung | Câu hỏi có vệt bút dạ vàng quét, phụ đề trong hộp tối bật ra |

Chữ trên màn hình (tiêu đề tin, tên từng hạng, năm, chương…) do Claude viết, sửa được ở khung **🖥️ Chữ trên màn hình**
và ô nhãn của từng cảnh. Ô **🎨 Bố cục** ở bước Content cho phép đổi bố cục bằng tay. Mọi chữ đều nằm ngoài vùng bị
nút TikTok che.

### 🌐 Làm 1 lần ra 2 bản Nhật + Hàn
Mở một video đã có content, bấm **🌐 Tạo bản Tiếng Hàn** (hoặc Tiếng Nhật) ở góc trên.
Tool tạo video mới **dùng lại y nguyên ảnh/video** (không tốn thêm dung lượng), Claude viết lại content cho khán giả
nước kia (không dịch máy móc), giữ đúng số cảnh. Bạn chỉ cần duyệt → đọc giọng (giọng mẫu tiếng nước đó) → xuất video.


Bấm đúp **`run.bat`**, trình duyệt sẽ tự mở trang `http://127.0.0.1:7860`.

### Bước 1 – Content
- Ở cột trái, chọn **Ngôn ngữ video**, **Thể loại**, nhập **Title** (nếu có) và/hoặc **Chủ đề**, chọn **thời lượng** và **tỉ lệ ảnh/video**
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
- **Giọng mẫu**: upload file giọng 3–10 giây, **cùng ngôn ngữ với video** (rõ, không có nhạc). Giọng được lưu lại để dùng cho các video sau.
- **Mô tả giọng**: chọn giới tính, độ tuổi, cao độ.
- **Ủy quyền cho tool**: AI tự chọn giọng hợp với chủ đề.
- Bấm **🎙️ Đọc toàn bộ**, nghe thử từng cảnh, cảnh nào chưa hay thì bấm **Đọc lại**.

### Bước 3 – Ảnh & video
- Bấm **🔎 Tự tìm…**. Tool sẽ:
  - Tìm ảnh **miễn phí, không cần key**, tự chọn nguồn theo ngôn ngữ: video tiếng Nhật → **ảnh báo Nhật (Yahoo!ニュース)**
    + Yahoo! JAPAN + Bing + DuckDuckGo; video tiếng Hàn → **ảnh báo Hàn (Naver News)** + **Naver** + Bing + DuckDuckGo. **Chỉ lấy ảnh 16:9**, hiện nguyên vẹn,
    không cắt, không làm mờ. **Cứ ~3 giây đổi ảnh một lần** (mỗi cảnh dùng nhiều ảnh khác nhau, không lặp ảnh).
  - Nếu vẫn thiếu ảnh 16:9, tool tự chụp **khung hình nét nhất** từ video YouTube liên quan (luôn đúng 16:9).
  - Tìm video trên YouTube (**ưu tiên kênh chính thức**: パ・リーグTV, NPB, 日本相撲協会, Jリーグ, KBO, SPOTV…;
    video tiếng Hàn tìm thêm **Naver TV** – nơi có clip KBO), tải về, tự chấm điểm **chuyển động + tiếng khán giả + độ nét**,
    nhờ Claude xem các đoạn tốt nhất rồi chọn đoạn **hợp với câu đang đọc**.
- Click ảnh ứng viên để thêm hoặc bỏ. Với video, click khung hình để đổi sang đoạn khác.
- Có thể **dán link** YouTube / TikTok / X / Facebook / Instagram, hoặc **tải ảnh/video của bạn lên**.
- **✂️ Cắt ảnh**: rê chuột lên ảnh → bấm ✂️ → kéo khung chọn vùng giữ lại (bỏ chữ, logo, watermark).
  Khung mặc định khóa đúng tỉ lệ khung video nên không bị viền trắng; ảnh gốc được giữ, bấm "Về ảnh gốc" để hoàn tác.

### Bước 4 – Xuất video
- **Nhạc nền**: mặc định **🎵 Tự chọn theo thể loại**. Tool có sẵn 20 bài **do tool tự soạn bằng code, không bản quyền**
  (2 bài mỗi thể loại + 2 bài Sumo + 2 bài Bóng đá: Bóng đá – Sân vận động/Hào hùng, Thể thao – Sôi động/Kịch tính, Sumo – Trống Taiko/Truyền thống, Tin tức – Bản tin/Trầm tĩnh, Top – Đếm ngược/Vui nhộn,
  Tiểu sử – Cảm động/Truyền cảm hứng, Chủ đề chung – Lo-fi/Tò mò), dùng chung cho video tiếng Nhật và tiếng Hàn.
  Lần đầu mở tool, nhạc được soạn tự động trong ~2 phút. Muốn soạn lại: `python -m app.bgm_gen --force`.
- Bạn vẫn có thể chọn bài khác hoặc upload nhạc của bạn (được lưu lại để dùng cho video sau), chỉnh âm lượng,
  rồi bấm **🎬 Xuất video**.
- Video nằm ở `projects\<mã video>\render\<title>.mp4`, hoặc tải trực tiếp trên trang.

### Bước 5 – Đăng TikTok
- Bấm **✨ Tạo title & hashtag**. Claude đọc content của video rồi đưa ra **5 title** (mỗi cái một kiểu: câu hỏi, con số,
  sự thật bất ngờ…, có dịch tiếng Việt) và **10–12 hashtag** chia nhóm: rộng / chủ đề / cụ thể / đề xuất (#おすすめ #fyp).
- Bấm chọn title, bấm hashtag để bật/tắt, thêm hashtag của bạn, rồi bấm **📋 Copy tất cả** để dán vào TikTok.

### 📈 Giữ chân người xem (đã cài sẵn)
- **Thể thao & Tiểu sử** – AI viết theo kiểu "雑学・裏話" của các kênh nhiều view (học từ 3 video đối thủ):
  0. Chọn **1 góc khuất** của nhân vật nổi tiếng (không kể cả sự nghiệp).
  1. Hook: **so sánh với mốc ai cũng biết** (岩瀬407 → リベラ652) / **"có một người đã…"** rồi mới nói tên /
     **câu thoại thật** / **con số sốc**.
  2. Hình ảnh ai cũng biết → **「しかし実は」** lật ngược (giây 15–20).
  3. **Nói rõ nguồn** (phỏng vấn, báo chí) + chi tiết cụ thể + câu thoại thật (không bịa).
  4. Câu hỏi **「なぜ〜のか」** giữa video → giải thích, có thể so sánh với người khác.
  5. Kết bằng câu **định nghĩa lại hook** hoặc so sánh trước–sau (〜のだった), không hỏi khán giả.
- **📚 Thư viện kịch bản mẫu** (Cài đặt): dán kịch bản video nhiều view, AI đọc 3 kịch bản gần nhất để học
  bố cục & giọng văn (không chép câu chữ). Có sẵn 3 mẫu: 田畑一也 / マリアノ・リベラ / 落合博満.
- **Tin tức / Top / Chung** – câu đầu có con số / sự thật gây sốc, đưa kết luận lên trước, kết bằng câu hỏi.
- **Cảnh đầu ưu tiên video** (có chuyển động). Ảnh đổi ~3 giây/lần; cảnh video dài được cắt thành nhiều đoạn hay.
- Âm lượng video xuất ra được chuẩn hóa **-14 LUFS** như video trên TikTok/YouTube.
- **Giọng đọc đều nhau giữa các cảnh**: mỗi cảnh được cân âm lượng theo giọng nói (không theo tiếng lách tách),
  nên không còn cảnh bị "mất tiếng" khi ghép. Cảnh đọc lỗi (im lặng / đọc thiếu) được tự đọc lại tối đa 2 lần;
  nếu vẫn lỗi, nhật ký sẽ báo ⚠️ tên cảnh để bạn đọc lại.

### 🔎 Tìm ảnh / video đúng người
- AI ghi cho mỗi cảnh: **người trong cảnh** (tên đầy đủ), từ khóa chính (tên đầy đủ + đội lúc đó + năm/cảnh cụ thể,
  không dùng từ trừu tượng) và **từ khóa dự phòng**.
- Ảnh/video có tiêu đề **không nhắc tên người đó** bị xếp xuống cuối / bỏ (dễ sai người). Ít kết quả đúng → tự thử
  từ khóa dự phòng → tên người. Bạn sửa được "Người trong cảnh" và các từ khóa ở bước Content.
- **Thể thao: chỉ lấy video thi đấu** (bóng chày, bóng đá, bóng rổ, sumo): video có tiêu đề kiểu talkshow /
  phỏng vấn / đối đàm / kênh bình luận / 切り抜き bị bỏ; video highlight, trận đấu được ưu tiên.
  Riêng **bóng chày & bóng đá** còn kiểm tra hình: video có dưới 30% thời lượng là cảnh sân cỏ (phòng thu, trường quay)
  bị bỏ, và chỉ cắt những đoạn đang ở trên sân. Video bạn tự dán link / tự upload thì không bị lọc.
- **Nhận cả ảnh ngang 3:2 / 4:3** (ảnh báo chí, Google đa số là vậy) – tự phóng kín khung, cắt vào chỗ có người.
- **Lọc ảnh/video lạc đề** (thể thao): tiêu đề về chính trị, môn thể thao khác (VD đang làm bóng chày mà ra sumo),
  ảnh bài báo không nhắc tên người trong cảnh → bỏ. Nhật ký ghi số kết quả của từng nguồn (Google, Bing…) và số ảnh bị bỏ.
- **Google Images**: tool mở Chrome/Edge chạy ẩn (không hiện cửa sổ), tìm giống người dùng thật, lấy ảnh gốc
  (lọc sẵn ảnh ngang). Không cần khóa API. Từ khóa tiếng Nhật → google.co.jp, tiếng Hàn → google.co.kr.
  Nếu Google hỏi "Tôi không phải robot" thì tool nghỉ Google 15 phút, các nguồn khác vẫn chạy.
  Cần chạy lại `install.bat` một lần (cài Playwright + Chromium ~150MB; không cài được thì dùng Edge có sẵn).
- **Facebook**: tự tìm thêm *video công khai* (trang báo, đội bóng, đài TV) qua DuckDuckGo/Bing (Facebook không cho
  tìm khi chưa đăng nhập). Ảnh trên Facebook thì không lấy được (cần đăng nhập). Bạn cũng có thể dán link video
  Facebook vào ô "dán link" của cảnh. Tắt/bật trong Cài đặt.

## 3. Cài đặt thêm (⚙️ ở góc dưới bên trái)
- **Model Claude**: để trống hoặc ghi `opus` / `sonnet`.
- **Nguồn tìm ảnh**: bật/tắt DuckDuckGo, Bing, Yahoo! JAPAN, Naver, Ảnh từ báo (đều miễn phí).
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
