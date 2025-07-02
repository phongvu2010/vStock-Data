# vStock-Data 📦

[![PyPI version](https://badge.fury.io/py/vstock-data.svg)](https://badge.fury.io/py/vstock-data)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)

Thư viện Python đơn giản và mạnh mẽ để tải dữ liệu lịch sử của chứng khoán Việt Nam từ nhiều nguồn khác nhau.

## ✨ Tính Năng Nổi Bật

* **Đa nguồn dữ liệu**: Hỗ trợ tải dữ liệu từ các nguồn phổ biến bao gồm **TCBS**, **Yahoo Finance**, và **Google BigQuery**.
* **API nhất quán**: Giao diện (API) đơn giản và đồng nhất, dễ dàng chuyển đổi giữa các nguồn dữ liệu.
* **Dữ liệu chuẩn hóa**: Tự động trả về dữ liệu dưới dạng `pandas.DataFrame` đã được làm sạch và chuẩn hóa (tên cột `Open`, `High`, `Low`, `Close`, `Volume`).
* **Kiểm tra thông minh**: Tự động kiểm tra và hướng dẫn cài đặt các thư viện phụ thuộc cần thiết cho từng nguồn dữ liệu.
* **Linh hoạt**: Dễ dàng tùy chỉnh khoảng thời gian và tần suất dữ liệu (ngày, tuần, tháng).

## 💾 Cài Đặt

Bạn có thể cài đặt thư viện thông qua `pip`.

**1. Cài đặt cơ bản (chỉ hỗ trợ nguồn TCBS):**

```bash
pip install vstock-data
```

**2. Cài đặt với các nguồn tùy chọn:**

Để sử dụng các nguồn dữ liệu khác, bạn cần cài đặt các "extras" tương ứng.

* **Để sử dụng Yahoo Finance:**

```bash
pip install vstock-data[yfinance]
```

* **Để sử dụng Google BigQuery:**

```bash
pip install vstock-data[bigquery]
```

* **Để cài đặt tất cả các nguồn:**

```bash
pip install vstock-data[all]
```

## 🚀 Hướng Dẫn Nhanh
Sử dụng `vstock-data` cực kỳ đơn giản. Dưới đây là một vài ví dụ.

**Ví dụ 1: Tải dữ liệu của FPT từ TCBS (nguồn mặc định)**

```python
from vstock_data import StockVN

try:
    # Khởi tạo đối tượng cho mã FPT với nguồn mặc định là TCBS
    fpt_stock = StockVN(symbol='FPT')

    # Tải dữ liệu từ đầu năm 2024 đến nay
    data = fpt_stock.fetch_data(start='2024-01-01')

    # In 5 dòng dữ liệu đầu tiên
    print(data.head())

except (ImportError, ValueError, ConnectionError) as e:
    print(f"Đã có lỗi xảy ra: {e}")
```

**Ví dụ 2: Tải dữ liệu của VCB từ Yahoo Finance theo tuần**

```python
from vstock_data import StockVN

try:
    # Khởi tạo đối tượng, chỉ định rõ nguồn là "yfinance"
    vcb_stock = StockVN(symbol='VCB', source='yfinance')

    # Tải dữ liệu theo tuần cho quý 1 năm 2025
    weekly_data = vcb_stock.fetch_data(start='2025-01-01', end='2025-03-31', interval='W')

    print("Dữ liệu của VCB theo tuần:")
    print(weekly_data)

except (ImportError, ValueError, IOError) as e:
    print(f"Đã có lỗi xảy ra: {e}")
```

## 📜 Giấy Phép

Dự án này được cấp phép dưới giấy phép MIT. Xem chi tiết tại file `LICENSE`.
