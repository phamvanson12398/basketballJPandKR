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

### 🏯 Video Lịch sử: kiểu "kể chuyện với bạn" (theo video mẫu 島流し)
Thể loại **🏯 Lịch sử** giờ làm theo video mẫu nhiều view:
- **Bố cục**: nền trắng, ảnh lớn 1080×824 ở giữa, **không có sub phía trên**; mỗi lần chỉ hiện **1 cụm sub ngắn** (1–2 dòng,
  chữ đen đậm, tên nhân vật màu đỏ) ngay dưới ảnh, đổi theo từng câu đọc (~1,3 giây). Vị trí và cỡ chữ đo từ video mẫu.
- **Giọng văn タメ口** như kể cho bạn nghe ("〜って知ってる？", "ヤバい", "マジで"): 1 chủ đề (島流し, 切腹, 参勤交代…)
  đi qua các thời đại và ngày càng "ghê" hơn; câu đầu hỏi thẳng; **hé lộ chuyện buồn cười nhất ngay đầu rồi để dành tới cuối**;
  thỉnh thoảng chen câu bình luận ngắn; kết bằng 1 câu cảm thán. Vẫn phải đúng sử liệu.
- **Ảnh**: tranh cổ / ukiyo-e / chân dung / ảnh cũ, **xen hình minh họa đồ vật** được nhắc tới (con quạ, bát cơm, bản đồ…).
- **Ảnh làm giống video mẫu**: ~6 phần tranh cổ (chân dung cho nhân vật, ukiyo-e / cuộn tranh cho sự kiện), ~2 phần
  hình minh họa kiểu いらすとや cho đồ vật / con vật / cảm xúc (khoảng 1/4 số cảnh), ~2 phần ảnh chụp (chùa, tượng Phật,
  ảnh cũ, đồ vật). **Ảnh đứng yên** (không zoom/lia); tranh phóng kín khung, **hình minh họa nền trắng hiện trọn ở giữa**
  (PNG trong suốt tự đặt lên nền trắng).
- **Không ra ảnh người thời nay**: video lịch sử tìm ảnh ở **Wikipedia / Wikimedia Commons trước** (tranh chân dung, cuộn tranh,
  sử liệu, lâu đài – phần lớn là tài liệu công cộng), bỏ nguồn ảnh báo; ảnh có tiêu đề kiểu diễn viên / idol / tuyển thủ /
  tin tức / game… bị loại; ảnh có tiêu đề không nhắc tới chủ đề (VD 甲陽軍鑑) bị loại; không chụp khung hình YouTube;
  AI xem ảnh được dặn loại mọi ảnh thời nay. Thiếu ảnh thì tool thử thêm "tên nhân vật + 肖像画".
- **Đổi ảnh nhanh như video mẫu**: ~2,5 giây/ảnh (thể loại khác ~3 giây), và ảnh đổi **đúng lúc đổi cụm sub** nên hình
  và chữ luôn khớp nhau. Tool tự tìm thêm ảnh cho đủ.
- **100% ảnh** (video lịch sử rất khó tìm): chọn thể loại Lịch sử hoặc lĩnh vực Lịch sử là thanh tỉ lệ tự về 0% video
  (đổi sang thể loại khác thì trả lại tỉ lệ cũ). Video cũ đổi sang Lịch sử thì các cảnh video tự chuyển thành ảnh.
  Vẫn có thể tự kéo thanh hoặc bấm 🎞 ở từng cảnh nếu bạn có video hay.
- Kịch bản mẫu **島流しの刑の実態** đã có trong 📚 Thư viện kịch bản mẫu; video Lịch sử chỉ học từ mẫu lịch sử.
- Bố cục này cũng dùng cho Lĩnh vực 🏯 Lịch sử ở Chủ đề chung. Top và Tiểu sử giữ bố cục riêng.

### 🏯 Lĩnh vực Lịch sử / Samurai (cho Top, Tiểu sử, Chủ đề chung)
Muốn làm **"Top 5 võ tướng mạnh nhất thời Chiến Quốc"** hay **tiểu sử một samurai**: chọn thể loại Top / Tiểu sử như bình thường,
rồi chọn **Lĩnh vực = 🏯 Lịch sử / Samurai**. Video giữ bố cục của thể loại (Top vẫn đếm ngược, huy hiệu vàng),
nhưng content theo quy tắc lịch sử: dẫn sử liệu, chuyện chưa chắc ghi 「諸説ある」, không lấy phim/giai thoại làm sự thật,
Top phải nêu tiêu chí xếp hạng, tránh chủ đề nhạy cảm Nhật–Hàn; tên nhân vật chữ đỏ, tên khó đọc tự chuyển hiragana;
ảnh tìm tranh chân dung / bình phong / lâu đài / giáp trụ, video tìm cảnh lâu đài, di tích, phim Taiga.
Nhạc nền tự chọn nhạc cổ truyền (Chiến quốc / Edo; bản tiếng Hàn: Cung đình / Chiến trận). Chủ đề chung dùng bố cục lịch sử (nền trắng, sub dưới ảnh);
Top giữ nền đen, Tiểu sử giữ nền kem. Gợi ý ý tưởng / tìm chuyện đời có chữ "samurai, 戦国, lịch sử…" sẽ tự chọn lĩnh vực này.

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

### 📱 Bố cục toàn màn hình – kiểu Shorts Nhật (theo video mẫu 「井上尚弥 オリンピックを一晩で諦めた」)
Tự dùng cho **🥊 Boxing**; video khác chọn ở ô 🎨 Bố cục → "Toàn màn hình – Shorts Nhật".
- **Cảnh 1 = thẻ tiêu đề**: 1 ảnh đứng yên kín màn hình + 3 dòng chữ rất to giữa màn hình — tên (vàng cam) /
  chuyện gì (trắng) / kết cục sốc (đỏ), viền đen dày; giọng đọc đọc đúng tiêu đề. Sửa ở 🖥️ Chữ trên màn hình.
  Chữ tiêu đề dùng font Minh triều đậm (Noto Serif CJK JP Black, install.bat tự tải; không có thì dùng chữ thường).
- **Ảnh / video phủ kín màn hình dọc**, ~80% video (thanh tỉ lệ tự đặt 80% khi chọn Boxing), cắt cảnh thẳng không chớp.
- **Phụ đề giữa màn hình**: 1–2 dòng chữ trắng viền đen dày, đổi theo từng cụm ~1 giây; `〈chữ〉` = **vàng**
  (tên, giải, con số), `〔chữ〕` = **đỏ** (thua, vô địch, kết quả sốc) – vị trí, cỡ chữ đo từ video mẫu.
- **Kịch bản theo đúng mạch video mẫu**: câu nói thật của nhân vật → "これは〜の言葉だ" → bối cảnh (năm, giải, đối thủ) →
  đảo chiều "しかし本人が明かした〜は〜ではなかった" → quyết định → dồn dập thành tích bằng con số → phản ứng SNS →
  câu đối lập trước/sau → **kết bằng câu hỏi giả định + 「〜と思う人はいいねで教えて」**. Kịch bản mẫu đã có trong thư viện
  (video boxing chỉ học từ mẫu boxing).

### 🥊 Boxing
Chọn **Lĩnh vực = 🥊 Boxing** (hoặc bấm preset 🥊 Boxing ở Gợi ý ý tưởng). AI dùng đúng thuật ngữ (hạng cân, WBA/WBC/IBF/WBO,
bảo vệ đai, KO/TKO/thắng điểm, thành tích 〇戦〇勝〇KO), tra số liệu ở BoxRec / JBC / báo lớn, tên võ sĩ có cách đọc,
không thổi phồng chuyện chảy máu / chấn thương, không đồn thổi bán độ. Video chỉ lấy **cảnh thi đấu** (bỏ họp báo, cân ký,
face-off, talkshow); AI xem hình nhận võ sĩ theo **màu quần** (uniform) và tên bình luận viên gọi. Khán giả 35+: nối với các
trận kinh điển xưa (Tatsuyoshi, Gushiken, Hasegawa, Hong Soo-hwan "4전5기"…), hashtag `#昭和ボクシング #平成ボクシング #伝説の一戦`.
Nhạc nền riêng **Boxing – Tập luyện** (trống rock, kèn đồng, chuông võ đài) và **Boxing – Ra võ đài** (trống trầm, dây, piano),
tự soạn khi mở tool lần sau.

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
- **✂️ Cắt khung video**: rê chuột lên đoạn video → bấm ✂️ → kéo khung chọn vùng giữ lại (bỏ logo kênh, chữ, viền đen,
  khán giả hai bên…). Lúc xuất video, tool cắt đúng vùng đó rồi phóng kín khung hình. Áp dụng cho mọi đoạn của cùng video
  trong cảnh; file video gốc không bị sửa, bấm "Bỏ cắt" để dùng lại cả khung.

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

### 👥 Khán giả 35+ (chọn khi tạo video, hoặc đổi ở phần thông tin video)
- **Đề tài & góc nhìn**: ưu tiên nhân vật / sự kiện / sản phẩm thời 1980–2000 (Showa cuối – Heisei; Hàn 80–2000),
  chuyện mới thì so với huyền thoại ngày xưa; cảm xúc "hoài niệm, sức nặng cuộc đời"; 1–2 câu gợi ký ức
  ("あの頃、テレビで見た…"). Không tiếng lóng, giọng kể chín chắn như phim tài liệu.
- **Giọng đọc** tự chọn trung niên, trầm; **tốc độ 0.94** và mỗi cảnh ít chữ hơn → chữ hiện lâu hơn một chút.
- **Nhạc nền** piano / hoài niệm thay cho EDM, nhạc sôi động (lịch sử, sumo, đua ngựa vẫn giữ nhạc riêng).
- **Tiêu đề & hashtag** kiểu #昭和 #平成 #懐かしい #あの頃 / #그시절 #추억 #레전드. **Gợi ý ý tưởng** có chọn khán giả 35+.
- **Bước TikTok** có thêm: **bình luận ghim** (câu hỏi gợi ký ức: "1995年、あなたは何歳でしたか？"), **chữ ảnh bìa**
  (to, ngắn: "1995年 / あの背中") và **giờ đăng gợi ý** (35+: 21–23h, 12–13h, 7–8h30; cuối tuần 9–11h).

### 🎯 Giây đầu tiên & kéo đúng khán giả 35+ (từ số liệu TikTok: người xem rời đi nhiều nhất ở 0:01, 72% dưới 35 tuổi)
- **Cảnh đầu luôn là ẢNH** (mọi thể loại), không còn ưu tiên video. Clip trận đấu hiện đại ở giây đầu làm TikTok xếp video
  vào nhóm "highlight bóng chày" (người trẻ, cả fan Mỹ Latinh).
- Bố cục bóng chày/thể thao: cảnh đầu là **1 ảnh đứng yên của đúng thời đó** + **nhãn năm to màu đỏ** ở góc trên trái
  (VD "1985年 阪神"), hiện suốt cảnh đầu. Claude tự ghi nhãn (35+: luôn có; chuyện bây giờ thì lấy năm của chuyện xưa liên
  quan, VD 1985 Hanshin vô địch); sửa ở ô **Nhãn năm (cảnh đầu)** của cảnh 1. Câu sub đầu phải tự đứng được, không cắt đôi câu hook.
- **Hashtag 35+**: bỏ `#おすすめ #fyp` (kéo video vào luồng đại trà toàn người trẻ), thay bằng tag thời đó
  (bóng chày: `#昭和プロ野球 #平成プロ野球 #懐かしの名選手 #プロ野球OB`).
- **Khán giả mặc định = 35+** (⚙️ Cài đặt → Khán giả mặc định): form tạo video và gợi ý ý tưởng chọn sẵn 35+.

### ✨ Biên tập giữ chân người xem (tự chạy sau khi viết content)
- Một lượt Claude đóng vai **biên tập viên Shorts**: chấm 6 tiêu chí (hook 2 giây đầu, câu mồi, nhịp đảo chiều,
  gọn không thừa, cụ thể, cái kết) → **thi 5 câu mở đầu** chọn câu mạnh nhất → sửa cảnh yếu (cắt câu thừa, thêm câu mồi,
  đảo chiều mỗi 10–15 giây, kết trả lời đúng hook). **Không thêm sự thật mới**; sau đó mới kiểm tra sự thật.
- Bước Content hiện **điểm trước → sau** và 5 câu mở đầu đã thử – bấm "Dùng câu này" để đổi hook.
- Nút **✨ Biên tập giữ chân** để chạy lại (VD sau khi bạn tự sửa nhiều). Tắt được trong Cài đặt.

### 🔍 Kiểm tra sự thật (tự chạy sau khi viết content)
- Một lượt Claude riêng đóng vai **biên tập viên kiểm chứng**: tra lại trên mạng **từng chi tiết** – tên, năm, con số, kỷ lục,
  câu trích dẫn, diễn biến, cả tiêu đề.
  - ✅ đúng → giữ nguyên + link nguồn · 🛠 sai → **tự sửa** (ghi rõ sửa gì) · ⚠️ không xác minh được → đổi sang cách nói
    không khẳng định ("tương truyền", "được cho là"); trích dẫn không có nguồn → bỏ ngoặc, chuyển thành lời kể.
- Mỗi cảnh hiện huy hiệu kết quả + ghi chú + link nguồn; bạn sửa chữ thì cảnh đó chuyển ✏️ "nên kiểm tra lại".
- Nút **🔍 Kiểm tra sự thật** để chạy lại bất cứ lúc nào. Bấm Duyệt mà còn cảnh ⚠️/✏️/❔ → tool nhắc trước.
- Thêm ~2–5 phút mỗi video; tắt được trong Cài đặt (không khuyến khích).

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
- **Nhận mọi tỉ lệ ảnh** (ngang, vuông, dọc) – tự phóng kín khung, cắt vào chỗ có người (ưu tiên ảnh ngang vì ít bị cắt). Muốn giữ vùng khác thì dùng ✂️ Cắt ảnh.
- **Lọc ảnh/video lạc đề** (thể thao): tiêu đề về chính trị, môn thể thao khác (VD đang làm bóng chày mà ra sumo),
  ảnh bài báo không nhắc tên người trong cảnh → bỏ. Nhật ký ghi số kết quả của từng nguồn (Google, Bing…) và số ảnh bị bỏ.
- **Video đúng nhân vật** (2 lớp thông minh):
  1. **Phụ đề**: tải phụ đề tự động của video YouTube, tìm lúc bình luận viên gọi tên nhân vật (田畑、タバタ…)
     → ưu tiên cắt đoạn quanh lúc đó.
  2. **Claude xem hình**: AI ghi đội + số áo của nhân vật lúc đó; tool đưa khung hình các đoạn ứng viên + 1 ảnh chân dung
     cho Claude xác nhận đoạn nào có đúng người (số áo, màu áo, khuôn mặt). Không có đoạn nào đúng → thử video khác.
     Thêm ~20–40 giây mỗi cảnh video, tắt được trong Cài đặt. Link bạn tự dán thì không bị loại.
- **🤖 AI xem ảnh / video** (Cài đặt): chọn AI làm phần *chọn ảnh, chọn đoạn video, xác nhận đúng người* –
  **Antigravity CLI** (`agy`, tài khoản Google, không tốn lượt Claude) / **Gemini API key** (Google AI Studio, có gói miễn phí
  theo ngày) / **Claude** / **Tắt** (chỉ thuật toán). **Viết content vẫn luôn là Claude.** Nút **🧪 Kiểm tra AI xem ảnh**
  vẽ 1 ảnh thử rồi hỏi AI để biết đã chạy chưa. Lệnh gọi Antigravity sửa được (mặc định `agy -p {prompt}`).
- **🧠 AI chọn ảnh hợp nội dung** (mọi thể loại): xem lưới ảnh ứng viên, xếp ảnh khớp lời đọc lên trước, đánh dấu
  "AI loại" cho ảnh sai người / không liên quan (đồ chơi, tranh hoạt hình, ảnh toàn chữ…). Thêm ~15–30 giây mỗi cảnh ảnh,
  tắt được trong Cài đặt.
- **Google Images**: tool mở Chrome/Edge chạy ẩn (không hiện cửa sổ), tìm giống người dùng thật, lấy ảnh gốc
  (lọc sẵn ảnh ngang). Không cần khóa API. Từ khóa tiếng Nhật → google.co.jp, tiếng Hàn → google.co.kr.
  Nếu Google hỏi "Tôi không phải robot" thì tool nghỉ Google 15 phút, các nguồn khác vẫn chạy.
- **🔑 Đăng nhập Google** (⚙️ Cài đặt, cạnh ô Google Images): mở trang đăng nhập Google ngay trên cửa sổ Chrome mà tool
  dùng để tìm ảnh → bạn đăng nhập như bình thường, xong cửa sổ tự ẩn, tool nhớ đăng nhập cho các lần sau
  (nút đổi thành ✅ Đã đăng nhập Google). Đang tìm ảnh mà Google bắt đăng nhập → cửa sổ tự hiện lên, chờ bạn
  đăng nhập tối đa 6 phút rồi tự tìm tiếp. Nếu Google báo "trình duyệt có thể không an toàn" thì nên dùng tài khoản phụ.
  Cần chạy lại `install.bat` một lần (cài Playwright + Chromium ~150MB; không cài được thì dùng Edge có sẵn).
- **Facebook**: tự tìm thêm *video công khai* (trang báo, đội bóng, đài TV) qua DuckDuckGo/Bing (Facebook không cho
  tìm khi chưa đăng nhập). Ảnh trên Facebook thì không lấy được (cần đăng nhập). Bạn cũng có thể dán link video
  Facebook vào ô "dán link" của cảnh. Tắt/bật trong Cài đặt.

### 🏇 Đua ngựa (競馬) – chọn Thể loại: Thể thao → Môn: 🏇 Đua ngựa
- **Bố cục giống video mẫu**: nền trắng, khung ảnh/video kín ngang (y=490, cao 724), chữ trên & dưới khung.
- **Chữ nhấn mạnh**: AI tự đánh dấu – `〔tên ngựa〕` chữ đỏ · `【điểm nhấn】` đỏ + to · `《từ nhấn》` đen + to.
  Bạn sửa được ngay trong ô chữ ở bước Content (giọng đọc tự bỏ qua ký hiệu).
- **Hình minh họa (sticker)**: mỗi cảnh 1 emoji (🍎 ❤️ 🐐…) hiện dần ở góc khung (tải hình Noto Emoji 512px lần đầu,
  lưu ở `library/stickers`). Sửa / xóa ở "Tùy chọn" của cảnh.
- **Content kiểu "tuyển tập chuyện vui"**: 1 chủ đề (đồ ăn, tật xấu, sau giải nghệ…), 6–9 con ngựa nổi tiếng, mỗi con 2–3 câu
  + câu bình luận vui, kết bằng con "lầy" nhất (Gold Ship…). Có sẵn kịch bản mẫu trong Thư viện kịch bản mẫu.
- **Ảnh khớp nội dung**: từ khóa = tên ngựa + 競走馬 + đúng cảnh của câu chuyện (bó hoa, ăn cỏ…), kèm **ảnh đồ vật**
  của chuyện (ふじりんご, ギネスビール…) xen kẽ với ảnh ngựa như video mẫu.
- **Nhạc nền riêng**: "Fanfare phi nước đại" và "Chuyện vui". Video ưu tiên kênh JRA / グリーンチャンネル; Claude nhận ngựa
  theo màu lông, đốm trắng trên mặt, màu áo nài.

### 🏢 Thương hiệu / Doanh nghiệp (🇯🇵 🇰🇷) – chọn Thể loại: 🏢 Thương hiệu / Doanh nghiệp
- Kiểu "雑学・裏話" về công ty: **1 góc khuất** – khởi nguồn bất ngờ, nguồn gốc tên/logo, suýt phá sản rồi lội ngược dòng,
  sản phẩm ra đời do tình cờ… (VD: 任天堂 từng làm hoa bài; 신라면 và họ của chủ tịch).
- Hook: "có một công ty từng…" rồi mới nói tên / tương phản hiện tại – quá khứ / con số sốc / câu nói của nhà sáng lập.
  → 「しかし実は」 quay về quá khứ → bước ngoặt → 「なぜ」 → kết bằng câu định nghĩa lại hook. Không quảng cáo, không tin đồn.
- **Tên thương hiệu chữ đỏ** (〔〕) trong phụ đề. Bố cục chữ trên/dưới khung, nền trắng.
- Ảnh: logo, sản phẩm đời đầu, nhà sáng lập, nhà máy, quảng cáo xưa; video: CM, kênh chính thức, dây chuyền sản xuất.
- Nhạc nền riêng: "Khởi nghiệp" (piano tươi sáng) và "Hoài niệm" (piano điện kiểu phim tài liệu ngày xưa).

### 🏯 Lịch sử (🇯🇵 Chiến quốc, Mạc mạt, Edo… / 🇰🇷 Joseon, Goryeo, Tam quốc) – Thể loại: 🏯 Lịch sử
- Kiểu "雑学・裏話": **1 góc khuất** của nhân vật / sự kiện ai cũng biết (VD: lá thư Nobunaga gọi Hideyoshi là "chuột hói";
  Sejong không có thịt thì không ăn được cơm).
- Hook: nói thẳng sự thật bất ngờ / "có một vị tướng / vua…" rồi mới nói tên / câu nói còn ghi trong sử liệu / con số sốc.
  → 「しかし実は」 → **dẫn sử liệu** (『信長公記』, 『조선왕조실록』…) → 「なぜ」 → kết bằng câu định nghĩa lại hook.
- Chuyện không chắc chắn → "tương truyền / có thuyết cho rằng", không lấy chuyện trong phim/truyện làm sự thật.
  **Tránh** vấn đề lịch sử Nhật–Hàn, trách nhiệm chiến tranh, lãnh thổ, thời thuộc địa.
- Ảnh: tranh chân dung, bình phong chiến trận, thư tịch cổ, thành quách, di tích, giáp trụ (thời chưa có ảnh chụp).
- **Nền trắng, ảnh lớn giữa, 1 cụm sub dưới ảnh** (xem mục "kể chuyện với bạn"), tên nhân vật chữ đỏ. Nhạc nền tự chọn theo nước: 🇯🇵 Chiến quốc (taiko, shakuhachi) / Edo (koto);
  🇰🇷 Cung đình (gayageum, janggu nhịp 3) / Chiến trận.

### 🎮 eSports (LoL / LCK / Worlds, đối kháng / EVO, VALORANT…) – Thể thao → Môn: 🎮 eSports
- Viết kiểu "góc khuất" như các môn khác (VD: lý do Faker từ chối hợp đồng 20 triệu USD), tên tuyển thủ/đội/giải đọc đúng
  (Faker→페이커/フェイカー, T1→티원, LCK→엘씨케이…), thuật ngữ game có giải thích ngắn. Không tin đồn, không bôi nhọ.
- Video tiếng Hàn tự dùng **bố cục Shorts Hàn**; tiếng Nhật dùng bố cục chữ trên/dưới khung.
- Tìm video: ưu tiên kênh giải chính thức (LoL Esports, LCK, Riot, EVO), bỏ video nói chuyện/reaction; vì video eSports
  phần lớn là cảnh trong game nên không dùng Claude soi số áo, mà dựa vào **phụ đề bình luận viên gọi tên** để cắt đúng pha.
- Nhạc nền riêng: "EDM sôi động" và "Hùng tráng kiểu Worlds".

### 💡 Gợi ý ý tưởng & 📖 Tìm chuyện đời nhân vật (trang 💡 Ý tưởng)
- **Gợi ý ý tưởng không trùng**: tool nhớ các ý tưởng đã gợi ý (`library/idea_history.json`) và các video đã làm → lần sau
  không gợi ý lại; mỗi ý tưởng là **một nhân vật khác nhau**; mỗi lần đổi ngẫu nhiên hướng (thời 80–90, 2000, gần đây,
  sau giải nghệ, thầy trò, vấp ngã…) cho đa dạng. Ví dụ trong prompt không còn bị lặp lại.
- **📖 Tìm chuyện đời**: nhập tên 1 người → Claude đọc phỏng vấn, báo, tiểu sử… → 5–12 **chuyện ít ai biết**, mỗi chuyện có
  tiêu đề, câu mở đầu, tóm tắt tiếng Việt, thời điểm, mức độ "ít người biết", **link nguồn** và nút **🎬 Làm video này**
  (điền sẵn tiêu đề + ghi chú + nguồn cho AI viết). Tìm lại lần nữa → ra chuyện **khác**.

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
