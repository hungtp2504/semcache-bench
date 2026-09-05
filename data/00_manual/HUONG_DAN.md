# Hướng dẫn gán nhãn (dành cho người gán — đọc kỹ trước khi bắt đầu)

> **Ghi chú lưu trữ (2026-09-05):** đây là bản hướng dẫn nguyên văn đã phát cho
> ba người gán nhãn. Việc gán đã hoàn tất; kết quả nằm ở
> `data/00_manual/annotator_{1,2,3}.jsonl`, phân tích bằng
> `scripts/gold_agreement.py` → `results/human_gold.json`. Các đường dẫn
> `human_annotation/...` bên dưới là bố cục thư mục tại thời điểm gán nhãn.


Cảm ơn bạn tham gia. Nhiệm vụ của bạn là đọc từng **cặp câu hỏi** và trả lời đúng
một câu duy nhất:

> **"Hai câu hỏi này có nên nhận CÙNG một câu trả lời không?"**

Không cần biết gì về đề tài nghiên cứu. Không cần biết đáp án thật của câu hỏi.
Chỉ cần suy nghĩ: *nếu có một câu trả lời đầy đủ và đúng cho câu A, thì câu trả
lời đó có đồng thời đầy đủ và đúng cho câu B không (và ngược lại)?*

---

## 1. Đọc ở đâu, ghi vào đâu

- Mở file của riêng bạn trong thư mục `human_annotation/sheets/`:
  - Người 1: `annotator_1.csv`
  - Người 2: `annotator_2.csv`
  - Người 3: `annotator_3.csv`
- File mở được bằng **Excel, Numbers, LibreOffice hoặc Google Sheets** (đã lưu
  UTF-8 có BOM nên tiếng Việt hiển thị đúng; nếu dùng Google Sheets: File →
  Import → Upload).
- Mỗi dòng là một cặp: cột `cau_hoi_A` và `cau_hoi_B`.
- Bạn **chỉ điền cột `nhan`** với đúng một trong ba giá trị (viết hoa):
  `SAME` · `DIFFERENT` · `UNSURE`
- Cột `ghi_chu` là tùy chọn — ghi khi bạn thấy cặp đó khó hoặc thú vị.
- **Không sửa, không xóa, không sắp xếp lại** các cột/dòng khác (cột `stt` và
  `gid` dùng để ghép kết quả, phải giữ nguyên).
- Tổng cộng **1.500 cặp**. Khoảng 300 cặp là **tiếng Việt** — nếu bạn không đọc
  được tiếng Việt, báo lại người điều phối ngay, KHÔNG đoán.

## 2. Ba nhãn — định nghĩa và cách quyết định

Giả định: cả hai câu hỏi đều được hỏi trên **cùng một nguồn tri thức** (một tài
liệu môn học, tài liệu kỹ thuật của một sản phẩm, tờ thông tin y tế, hoặc một
văn bản quy định).

### SAME — cùng câu trả lời
Chọn `SAME` khi **bất kỳ** câu trả lời đầy đủ, đúng cho câu này cũng là câu trả
lời đầy đủ, đúng cho câu kia. Những khác biệt sau **KHÔNG** làm thay đổi nhãn:
- lỗi chính tả, viết tắt, teencode ("assignment 1 deadline khi nao v")
- khác cách diễn đạt, đảo cấu trúc câu ("Khi nào hạn nộp?" ↔ "Tôi phải nộp trước ngày nào?")
- thiếu dấu tiếng Việt, khác văn phong (trang trọng ↔ suồng sã)

### DIFFERENT — khác câu trả lời
Chọn `DIFFERENT` khi câu trả lời đúng cho câu này sẽ **sai, thiếu, hoặc gây hiểu
lầm** nếu dùng cho câu kia. Dấu hiệu thường gặp (chỉ cần MỘT cái là đủ):
- **khác thực thể/số hiệu**: "Assignment 1" ↔ "Assignment 2"; "React" ↔ "Vue"; hai tên bệnh khác nhau
- **đảo chiều/phủ định**: "có được phép… không?" ↔ "có bị cấm… không?"; "bao gồm" ↔ "không bao gồm"
- **khác lượng/mốc**: "sớm nhất" ↔ "muộn nhất"; "tối đa" ↔ "tối thiểu"; "ít nhất 3" ↔ "đúng 3"
- **khác khía cạnh**: "hạn nộp là khi nào?" ↔ "chấm theo tiêu chí nào?" (cùng chủ đề nhưng hỏi việc khác)
- **khác phạm vi**: "hạn nộp Assignment 1" ↔ "hạn nộp phần phụ lục của Assignment 1"
- **khác tiền giả định**: "Nộp trễ bị phạt bao nhiêu?" giả định có phạt — khác với "Hạn nộp là khi nào?"

### UNSURE — thật sự không chắc
Chỉ chọn `UNSURE` khi bạn đã suy nghĩ kỹ mà vẫn thấy **người hợp lý có thể bất
đồng chính đáng** về việc một câu trả lời có phục vụ được cả hai câu hay không.
Dùng **tiết kiệm** — kinh nghiệm cho thấy dưới 2–3% số cặp. `UNSURE` không phải
là "cặp này khó" hay "tôi lười nghĩ".

## 3. Ví dụ đã gán mẫu

| Câu A | Câu B | Nhãn | Vì sao |
|---|---|---|---|
| Hạn nộp Assignment 1 là khi nào? | Tôi phải nộp Assignment 1 trước ngày nào? | SAME | Cùng hỏi một mốc thời gian, chỉ khác cách nói |
| Hạn nộp Assignment 1 là khi nào? | assignment 1 deadline khi nao v | SAME | Teencode/không dấu không đổi nghĩa |
| Hạn nộp Assignment 1 là khi nào? | Hạn nộp Assignment 2 là khi nào? | DIFFERENT | Khác thực thể (1 ↔ 2) — đáp án khác hoàn toàn |
| Thư viện có mở cửa Chủ nhật không? | Thư viện có đóng cửa Chủ nhật không? | DIFFERENT | Đảo chiều — trả lời "Có" cho câu này là "Không" cho câu kia |
| Hạn nộp Assignment 1 là khi nào? | Hạn nộp sớm nhất của Assignment 1? | DIFFERENT | Thêm "sớm nhất" — hỏi một lượng khác |
| Hạn nộp Assignment 1 là khi nào? | Assignment 1 chấm theo tiêu chí nào? | DIFFERENT | Cùng chủ đề, khác khía cạnh |

## 4. Quy tắc làm việc (quan trọng ngang định nghĩa nhãn)

1. **Làm độc lập.** Không trao đổi với người gán khác, không hỏi ai, cho đến khi
   cả ba người nộp xong. (Sau đó mới có buổi thảo luận các cặp bất đồng.)
2. **Không tra đáp án.** Bạn đánh giá quan hệ giữa HAI CÂU HỎI, không cần biết
   câu trả lời thật.
3. **Từng cặp một, không suy pattern.** Đừng nghĩ "nãy giờ nhiều DIFFERENT quá
   chắc cặp này SAME" — dữ liệu không có quy luật để đoán.
4. **Nghỉ giải lao.** Khoảng 15–20 giây/cặp → toàn bộ mất **6–8 giờ thuần**.
   Khuyến nghị chia 3–4 buổi (mỗi buổi ~400 cặp), nghỉ 5 phút mỗi 100 cặp.
   Đừng làm một mạch — mệt là chất lượng rơi.
5. **Điền đủ 1.500 dòng.** Dòng bỏ trống sẽ bị coi là chưa hoàn thành.
6. Xong thì lưu đúng tên file gốc (`annotator_<số>.csv`) và gửi lại người điều phối.

## 5. Sau khi cả ba người nộp (người điều phối làm)

```bash
python3 human_annotation/scripts/sheet_to_jsonl.py human_annotation/sheets/annotator_1.csv   # -> human_annotation/annotator_1.jsonl (x3)
python3 human_annotation/scripts/gold_agreement.py human_annotation/annotator_*.jsonl
```

Script in ra: **Fleiss' κ** (cổng đạt: ≥ 0.65), agreement từng cặp người, độ
khớp nhãn đa số ↔ nhãn thiết kế (tổng thể / theo trục / theo miền), và ghi danh
sách các cặp chưa nhất trí vào `human_annotation/adjudication_needed.jsonl` — ba người
họp, thảo luận từng cặp đó, chốt **nhãn vàng** (bất đồng dai dẳng thì trọng tài
quyết).
