# USB AI Tool (Portable Python)

Bản Portable chạy trực tiếp trên Windows (không cần cài Python, không cần cài thêm thư viện).

## Cách sử dụng
1. Tải toàn bộ thư mục này về (Clone hoặc **Download ZIP** rồi giải nén vào USB/máy tính).
2. Điền API key vào `config.json`:
   - Nếu chưa có file `config.json`, hãy chạy `run.bat` lần đầu để tool tự tạo `config.json` (hoặc copy từ `config.example.json` và đổi tên thành `config.json`).
   - Điền `gemini_api_key` và/hoặc `fosta_api_key` vào `config.json`.
3. Nhấn đúp **`run.bat`** để chạy.
4. Tạo hoặc thả file `.txt` (ví dụ `de.txt`) vào cùng thư mục — tool sẽ tự gọi AI (ưu tiên Gemini, lỗi tự fallback sang Fosta) và xuất kết quả ra `de_answer.txt`.
