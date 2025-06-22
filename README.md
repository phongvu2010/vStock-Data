# vStock Data

Thư viện Python tải dữ liệu chứng khoán Việt Nam từ nhiều nguồn khác nhau.

## Cài đặt
```bash
pip install vstock-data


## Ví dụ
```bash
from vstock_data import StockVNData
stock = StockVNData(symbol="FPT", interval="B", source="tcbs")
data = stock.data
