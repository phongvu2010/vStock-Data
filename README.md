## vStock Data
Thư viện Python tải dữ liệu chứng khoán Việt Nam từ nhiều nguồn khác nhau.


## Cài đặt
```bash
pip install vstock-data


## Ví dụ
```bash
from vstock_data import StockVNData

stock = StockVNData(symbol="VIC", source="TCBS")
df = stock.fetch_data(start="2023-01-01", end="2025-10-01", interval="B")
