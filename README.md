# USB AI Tool (Portable Python)

Công cụ chạy trực tiếp trên USB (Windows), tự động theo dõi file `.txt` mới và gọi AI (ưu tiên Gemini, tự động fallback sang Fosta) để xuất kết quả ra `<tên_file>_answer.txt`.

## Cài đặt nhanh
1. Chạy `setup_usb.ps1` một lần trên máy có mạng để tải Python 3.12 Embeddable và các thư viện (`google-genai`, `openai`, `watchdog`) vào thư mục `python\`:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup_usb.ps1
   ```
2. Tạo `config.json` từ `config.example.json` (hoặc chạy `run.bat` lần đầu để tự sinh) và điền API key:
   - `gemini_api_key`
   - `fosta_api_key`
   - `fosta_base_url` (mặc định `https://codex.fosta.app/v1`)
3. Chép toàn bộ thư mục vào USB và chạy `run.bat` trên máy Windows bất kỳ.
