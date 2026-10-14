# Báo cáo lab Day 26 — Function Calling và MCP

Repo minh họa việc model chọn công cụ bằng Function Calling, client gọi công cụ
qua MCP và server thực thi logic. Phần 01–03 dùng dữ liệu thời tiết giả lập;
phần 04 gọi WeatherAPI thật qua một MCP Server độc lập.

## Môi trường

- Windows, PowerShell, Python 3.12.15, uv 0.13.1.
- Phần 01–03: môi trường `.venv` ở gốc, MCP SDK 2.3.0. Phiên bản đã cài được
  lưu trong `requirements-lock.txt`.
- Phần 04: hai môi trường riêng trong `mcp-server/.venv` và `mcp-client/.venv`,
  MCP SDK 1.28.1, Google ADK 2.3.0; dependency được khóa bằng hai file `uv.lock`.
- Server đọc `04-lab/mcp-server/.env`. Agent đọc `04-lab/mcp-client/.env`;
  biến môi trường của tiến trình có ưu tiên cao hơn file.
- Model gốc là `gemini-2.5-flash`. API báo model này đã hết quota ngày của key
  hiện tại. Cấu hình local đã đổi `GEMINI_MODEL` sang `gemini-3.5-flash-lite`,
  theo tên model có trong API và phản hồi chuyển phiên bản của Google.
  Có thể đổi lại bằng biến `GEMINI_MODEL`; không cần sửa code.

## Cách chạy lại

Từ thư mục gốc repo, hai file `.env` đã có key. Không đưa key vào báo cáo hoặc Git.
Các file `.env.example` chứa cấu trúc cấu hình để dùng trên máy khác.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Lab.ps1
```

Script dùng `uv` trên PATH hoặc bản đã cài ở
`%LOCALAPPDATA%\day26-tools\uv.exe`, đồng bộ dependency và khởi động hai dịch vụ
ở nền. Server dùng cổng 8085, ADK Web dùng cổng 8000.

Mở **http://localhost:8000**, chọn **weather_agent**, rồi hỏi:

1. “Hãy gọi health_check để kiểm tra server.”
2. “Thời tiết hiện tại ở Hanoi thế nào? Trả lời bằng tiếng Việt.”
3. “Dự báo thời tiết Tokyo trong 3 ngày, kèm khả năng mưa.”

Trong trace, kiểm tra yêu cầu gọi tool, dữ liệu tool trả về và câu trả lời cuối.

Để dừng các dịch vụ do script khởi động:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-Lab.ps1
```

Log cục bộ nằm trong `.lab-runtime/`, được Git bỏ qua. Script dừng kiểm tra
đường dẫn tiến trình trước khi dừng cả cây tiến trình Python của dịch vụ.

## Kiểm chứng tự động

```powershell
# Chỉ kiểm tra MCP và WeatherAPI thật
.\04-lab\mcp-client\.venv\Scripts\python.exe .\04-lab\mcp-client\verify_setup.py

# Kiểm tra thêm vòng gọi tool của Gemini/ADK
.\04-lab\mcp-client\.venv\Scripts\python.exe .\04-lab\mcp-client\verify_setup.py --agent --output reports/lab04-verification.json

# Chạy toàn bộ demo và lưu bằng chứng
.\.venv\Scripts\python.exe .\verify_labs.py
```

Các lệnh có Gemini tiêu thụ quota API. Ba câu hỏi ADK được cách nhau 35 giây;
mỗi lượt gọi tool cần ít nhất hai yêu cầu model. Nếu xuất hiện 429, đọc giới hạn
phút/ngày trong lỗi và chờ đúng thời gian; không chạy liên tục để thử lại.

Nếu cần tạo lại môi trường gốc bằng đúng phiên bản đã kiểm tra:

```powershell
uv venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements-lock.txt
```

## Bằng chứng và ý nghĩa

Kết quả cuối: **cả sáu mục lab01, lab02, registry, versioning, auth và lab04
đều đạt**. Phần 04 đã xác nhận đủ ba vòng gọi tool qua Gemini bằng model
`gemini-3.5-flash-lite`. Cơ chế khởi động/dừng hai dịch vụ cũng đã được thử;
ADK Web trả HTTP 200 và liệt kê `weather_agent`.

| Phần | Điều cần xác nhận | Bằng chứng |
|---|---|---|
| 01 | Gemini sinh yêu cầu `get_weather`; app thực thi và model tổng hợp | `reports/lab01-output.txt` |
| 02 | Khám phá tool rồi gọi cho Hanoi, Danang, Haiphong qua stdio | `reports/lab02-output.txt` |
| Registry | Chọn `get_weather_v2` theo tag và phiên bản | `reports/registry-output.txt` |
| Versioning | Tool v1 vẫn chạy; v2 trả JSON; đọc được metadata deprecated | `reports/versioning-output.txt` |
| Auth | Thiếu/sai token bị từ chối; token đúng gọi được tool | `reports/auth-verification.json` |
| 04 | Khám phá 3 tool; lấy dữ liệu thật; Gemini gọi tool và trả lời | `reports/lab04-verification.json` |

`reports/summary.json` tổng hợp trạng thái các demo. JSON của phần 04 chứa thời
điểm kiểm tra, model, tham số gọi tool, dữ liệu trả về và câu trả lời. Dữ liệu
thời tiết trong các file là kết quả tại thời điểm kiểm tra, không phải kết quả
cố định cho các lần chạy sau.

## Những lỗi đã sửa

- Server tự nạp `.env`, mặc định chạy Streamable HTTP thay vì phụ thuộc vào
  trạng thái terminal. Có tùy chọn `--transport stdio` khi cần.
- Agent tự nạp cấu hình, trả lời tiếng Việt và yêu cầu dùng dữ liệu từ tool.
  Mô tả thành phố là ví dụ; tool có thể truy vấn thành phố trên toàn thế giới.
- Loại bỏ thông báo kết nối thành công trước khi có kết nối thật và fallback
  không có tool. Lỗi cấu hình/kết nối được báo rõ.
- Thay phép GET sơ bộ bằng MCP initialize, list_tools và call_tool thật;
  xác nhận dự báo có đủ ba ngày và trace ADK có dữ liệu tool trả về.
- Giới hạn tham số dự báo trong khoảng 1–3 ngày.
- Registry đọc JSON bằng UTF-8; client stdio dùng đường dẫn server theo file
  để có thể chạy từ thư mục gốc.
- Tool giả lập phần 01 chuẩn hóa tên thành phố có/không dấu để model gọi
  `Ha Noi`, `Hanoi` hoặc `Hà Nội` đều nhận đúng dữ liệu giả lập.
- Auth hỗ trợ cổng riêng để tránh xung đột với ADK. Kiểm tra thực tế với SDK
  2.3.0: thiếu token và token sai đều trả HTTP 401.
- Các lỗi model 500/502/503/504 được thử lại tối đa ba lần. Lỗi quota và model
  không còn khả dụng được báo cho người dùng.
- Kiểm tra không in API key; log HTTP chứa URL WeatherAPI được tắt.

## Phạm vi

Bài lab được chạy và kiểm tra local. Cloud Run là hướng triển khai thêm trong
repo; báo cáo này không xác nhận deployment hoặc Docker build. Repo chưa có
rubric hoặc quy định nộp bài, nên cần đối chiếu thêm yêu cầu của giảng viên.
