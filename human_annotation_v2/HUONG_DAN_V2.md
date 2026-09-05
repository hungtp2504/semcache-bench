# Hướng dẫn gán nhãn — vòng 2 (dành cho người gán, đọc kỹ trước khi bắt đầu)

Cảm ơn bạn tham gia. Khác với vòng 1, lần này mỗi cặp câu hỏi có kèm **một câu
trả lời cho sẵn**. Câu trả lời này **đúng và đầy đủ cho MỘT trong hai câu hỏi**
(không nói trước là câu nào). Nhiệm vụ của bạn là trả lời đúng một câu duy nhất:

> **"Nếu đem câu trả lời cho sẵn này phục vụ CẢ HAI câu hỏi, nó có đầy đủ và
> đúng cho cả hai không?"**

Không cần biết gì về đề tài nghiên cứu. Không cần tra cứu thêm — mọi thứ bạn cần
đều nằm trong ba cột: hai câu hỏi và câu trả lời cho sẵn.

---

## 1. Đọc ở đâu, ghi vào đâu

- Mở file của riêng bạn trong thư mục `human_annotation_v2/sheets/`:
  - Người 1: `annotator_1.csv` · Người 2: `annotator_2.csv` · Người 3: `annotator_3.csv`
- File mở được bằng **Excel, Numbers, LibreOffice hoặc Google Sheets** (đã lưu
  UTF-8 có BOM nên tiếng Việt hiển thị đúng; nếu dùng Google Sheets: File →
  Import → Upload).
- Mỗi dòng là một cặp: cột `cau_hoi_A`, `cau_hoi_B`, và `cau_tra_loi` (câu trả
  lời cho sẵn).
- Bạn **chỉ điền cột `nhan`** với đúng một trong ba giá trị (viết hoa):
  `SAME` · `DIFFERENT` · `UNSURE`
- Cột `ghi_chu` là tùy chọn — ghi khi bạn thấy cặp đó khó hoặc thú vị.
- **Không sửa, không xóa, không sắp xếp lại** các cột/dòng khác (cột `stt` và
  `gid` dùng để ghép kết quả, phải giữ nguyên).
- Tổng cộng **1.500 cặp**. Khoảng 300 cặp là **tiếng Việt** — nếu bạn không đọc
  được tiếng Việt, báo lại người điều phối ngay, KHÔNG đoán.

## 2. Ba nhãn — định nghĩa và cách quyết định

### SAME — câu trả lời phục vụ được cả hai
Chọn `SAME` khi câu trả lời cho sẵn là câu trả lời **đầy đủ và đúng cho cả hai
câu hỏi**. Những khác biệt sau giữa hai câu hỏi **KHÔNG** làm thay đổi nhãn:
- lỗi chính tả, viết tắt, teencode ("assignment 1 deadline khi nao v")
- khác cách diễn đạt, đảo cấu trúc câu
- thiếu dấu tiếng Việt, khác văn phong

Lưu ý quan trọng: đôi khi hai câu hỏi **hỏi về hai thứ khác nhau** nhưng câu trả
lời cho sẵn vẫn tình cờ đúng và đủ cho cả hai (ví dụ hai bài tập khác nhau nhưng
cùng chung một hạn nộp, và câu trả lời chỉ nêu mốc hạn đó). Trường hợp này vẫn
là `SAME` — bạn đánh giá **câu trả lời**, không đánh giá hai câu hỏi có "giống
nhau" hay không.

### DIFFERENT — câu trả lời không phục vụ được một trong hai
Chọn `DIFFERENT` khi dùng câu trả lời cho sẵn cho một trong hai câu hỏi sẽ
**sai, thiếu, hoặc gây hiểu lầm**. Dấu hiệu thường gặp (chỉ cần MỘT cái là đủ):
- một câu hỏi về thực thể/phiên bản khác mà câu trả lời không nói tới
- một câu hỏi bị đảo chiều/phủ định so với điều câu trả lời khẳng định
- một câu hỏi về lượng/mốc khác (sớm nhất ↔ muộn nhất, tối đa ↔ tối thiểu)
- một câu hỏi về khía cạnh khác (hạn nộp ↔ tiêu chí chấm) mà câu trả lời không đề cập
- một câu hỏi về phạm vi hẹp/rộng hơn mà câu trả lời không phủ được
- một câu hỏi giả định một sự việc khác mà câu trả lời không xác nhận

### UNSURE — thật sự không chắc
Chỉ chọn `UNSURE` khi bạn đã suy nghĩ kỹ mà vẫn thấy **người hợp lý có thể bất
đồng chính đáng**. Dùng **tiết kiệm** — kinh nghiệm vòng 1 cho thấy dưới 1% số
cặp. `UNSURE` không phải là "cặp này khó" hay "tôi lười nghĩ".

## 3. Ví dụ đã gán mẫu

Giả sử câu trả lời cho sẵn là: *"Trước 20/11/2025, 23:59."*

| Câu A | Câu B | Nhãn | Vì sao |
|---|---|---|---|
| Hạn nộp Assignment 1 là khi nào? | Tôi phải nộp Assignment 1 trước ngày nào? | SAME | Cùng hỏi một mốc; câu trả lời phục vụ cả hai |
| Hạn nộp Assignment 1 là khi nào? | assignment 1 deadline khi nao v | SAME | Teencode không đổi nghĩa |
| Hạn nộp Assignment 1 là khi nào? | Hạn nộp Assignment 2 là khi nào? | DIFFERENT | Câu trả lời không nói gì về Assignment 2 — dùng cho B là đoán mò |
| Hạn nộp Assignment 1 là khi nào? | Hạn nộp sớm nhất của Assignment 1? | DIFFERENT | "Sớm nhất" hỏi một lượng khác mà câu trả lời không xác nhận |
| Hạn nộp Assignment 1 là khi nào? | Assignment 1 chấm theo tiêu chí nào? | DIFFERENT | Câu trả lời không đề cập tiêu chí chấm |

## 4. Quy tắc làm việc

1. **Làm độc lập.** Không trao đổi với người gán khác cho đến khi cả ba nộp xong.
2. **Chỉ dùng thông tin trong dòng đó.** Không tra cứu ngoài, không dùng kiến
   thức riêng để "sửa" câu trả lời cho sẵn — coi nó là đúng cho một trong hai câu.
3. **Từng cặp một, không suy pattern.** Dữ liệu không có quy luật để đoán.
4. **Nghỉ giải lao.** Khoảng 20–25 giây/cặp → toàn bộ mất 8–10 giờ thuần.
   Khuyến nghị chia 3–4 buổi, nghỉ 5 phút mỗi 100 cặp.
5. **Điền đủ 1.500 dòng.** Dòng bỏ trống bị coi là chưa hoàn thành.
6. Xong thì lưu đúng tên file gốc (`annotator_<số>.csv`) và gửi lại người điều phối.
