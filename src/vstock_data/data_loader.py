import pandas as pd
import time
from datetime import datetime as dt
from functools import lru_cache

# --- Khai báo trạng thái của các thư viện tùy chọn ---
try:
    import requests
    from json import JSONDecodeError
    from requests.exceptions import RequestException
    TCBS_INSTALLED = True
except ImportError:
    TCBS_INSTALLED = False

try:
    import yfinance as yf
    YFINANCE_INSTALLED = True
except ImportError:
    YFINANCE_INSTALLED = False

try:
    from google.cloud import bigquery
    from google.oauth2.service_account import Credentials
    from google.api_core.exceptions import BadRequest
    BIGQUERY_INSTALLED = True
except ImportError:
    BIGQUERY_INSTALLED = False


class StockVN:
    """
    Lớp chính để tải và xử lý dữ liệu lịch sử của chứng khoán Việt Nam.

    Lớp này đóng gói logic để lấy dữ liệu từ nhiều nguồn khác nhau như
    TCBS, yfinance, và Google BigQuery. Nó cũng cung cấp các chức năng
    để chuẩn hóa dữ liệu và kiểm tra các thư viện phụ thuộc.

    Attributes:
        symbol (str): Mã chứng khoán được chuẩn hóa.
        source (str): Nguồn dữ liệu được chọn.
        credential (dict): Thông tin xác thực cho nguồn BigQuery.
    """
    def __init__(self, symbol: str, source: str = "TCBS", credential: dict = None):
        """
        Khởi tạo đối tượng StockVN.

        Args:
            symbol (str): Mã chứng khoán (ví dụ: "FPT", "VCB").
            source (str, optional): Nguồn dữ liệu. Hỗ trợ "TCBS", "YFinance", 
                "BigQuery". Mặc định là "TCBS".
            credential (dict, optional): Thông tin xác thực cho BigQuery. 
                Bắt buộc khi `source` là "bigquery".

        Raises:
            ValueError: Nếu `source` không được hỗ trợ hoặc `credential` bị thiếu
                khi cần thiết.
            ImportError: Nếu thư viện cần thiết cho `source` đã chọn chưa được
                cài đặt.
        """
        ALLOWED_SOURCES = ["tcbs", "yfinance", "bigquery"]
        source_lower = source.lower() # Chuyển source thành chữ thường để kiểm tra

        if source_lower not in ALLOWED_SOURCES:
            raise ValueError(f"Nguồn '{source_lower}' không được hỗ trợ. Vui lòng chọn: {ALLOWED_SOURCES}")

        self.symbol = symbol.upper()
        self.source = source_lower
        self.credential = credential

        # Kiểm tra thư viện tương ứng với source ngay khi khởi tạo
        if source_lower == "tcbs" and not TCBS_INSTALLED:
            raise ImportError("Nguồn 'tcbs' yêu cầu cài đặt. Vui lòng chạy: pip install vstock-data")

        if source_lower == "yfinance" and not YFINANCE_INSTALLED:
            raise ImportError("Nguồn 'yfinance' yêu cầu cài đặt. Vui lòng chạy: pip install vstock-data[yfinance]")

        if source_lower == "bigquery" and not BIGQUERY_INSTALLED:
            raise ImportError(f"Nguồn 'bigquery' yêu cầu cài đặt. Vui lòng chạy: pip install vstock-data[bigquery]")

        if source_lower == "bigquery" and not isinstance(credential, dict):
            raise ValueError(f"Nguồn 'bigquery' yêu cầu tham số 'credential'.")

    @lru_cache(maxsize = 128)
    def fetch_data(self, start: str = None, end: str = None, interval: str = "B"):
        """
        Tải, chuẩn hóa và trả về dữ liệu chứng khoán lịch sử.

        Phương thức này là giao diện chính để lấy dữ liệu. Nó gọi đến phương
        thức private tương ứng với nguồn đã chọn, sau đó chuẩn hóa
        tên cột, kiểu dữ liệu index và resample dữ liệu nếu cần.

        Args:
            start (str, optional): Ngày bắt đầu lấy dữ liệu, định dạng 'YYYY-MM-DD'.
                Mặc định là None (lấy từ đầu lịch sử).
            end (str, optional): Ngày kết thúc lấy dữ liệu, định dạng 'YYYY-MM-DD'.
                Mặc định là None (lấy đến ngày gần nhất).
            interval (str, optional): Khoảng thời gian của dữ liệu. Hỗ trợ:
                'B' (ngày), 'W' (tuần), 'ME' (tháng). Mặc định là 'B'.

        Returns:
            pd.DataFrame: Một DataFrame chứa dữ liệu OHLCV đã được chuẩn hóa,
            với 'Date' là index.

        Raises:
            ValueError: Nếu `interval` không được hỗ trợ hoặc không tìm thấy
            dữ liệu cho mã chứng khoán.
        """
        ALLOWED_INTERVALS = ["B", "W", "ME"]
        if interval.upper() not in ALLOWED_INTERVALS:
            raise ValueError(f"Khoảng thời gian không được hỗ trợ. Vui lòng chọn: {ALLOWED_INTERVALS}")

        # Lựa chọn phương thức tải dữ liệu dựa trên nguồn
        if self.source == "yfinance":
            df = self._fetch_yfinance(start, end)
        elif self.source == "bigquery":
            df = self._fetch_bigquery(start, end)
        elif self.source == "tcbs":
            df = self._fetch_tcbs(start, end)
        else:
            # Trường hợp này khó xảy ra do đã kiểm tra trong __init__
            raise ValueError(f"Nguồn '{self.source}' không được hỗ trợ.")

        if df.empty:
            raise ValueError(f"Không tìm thấy dữ liệu cho mã '{self.symbol}' từ '{self.source}'.")

        # Chuẩn hóa tên cột
        df.rename(columns = {
            "close": "Close", "high": "High", "low": "Low", "open": "Open", "volume": "Volume"
        }, inplace = True)

        df.index.name = "Date"
        df.index = pd.to_datetime(df.index)

        # Resample dữ liệu nếu interval không phải là ngày
        if interval.upper() != "B":
            df = df.resample(interval.upper()).agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            })
            df.dropna(inplace = True) # Xóa các dòng rỗng do resample

        return df.sort_index()

    def _fetch_tcbs(self, start: str, end: str) -> pd.DataFrame:
        """ ✅ Tải dữ liệu chứng khoán từ TCBS """
        try:
            start_date = dt.strptime(start, "%Y-%m-%d") if start else dt(2000, 1, 1)
            end_date = dt.strptime(end, "%Y-%m-%d") if end else dt.now()

            fd = int(time.mktime(start_date.timetuple()))
            td = int(time.mktime(end_date.timetuple()))

            url = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term?ticker={self.symbol}&type=stock&resolution=D&from={fd}&to={td}"
            response = requests.get(url, timeout=10)
            response.raise_for_status() # Tự động báo lỗi nếu request không thành công
            json_data = response.json()

            if not json_data.get("data"):
                return pd.DataFrame()

            df = pd.json_normalize(json_data["data"])
            df["tradingDate"] = pd.to_datetime(df["tradingDate"].str.split("T").str[0])

            return df.set_index("tradingDate")[["close", "high", "low", "open", "volume"]]
        except RequestException as e:
            raise ConnectionError(f"Lỗi kết nối đến '{self.source}': {e}")
        except JSONDecodeError:
            raise ValueError(f"Lỗi giải mã JSON từ '{self.source}'. Phản hồi: {response.text}")
        except (KeyError, IndexError) as e:
            raise ValueError(f"Cấu trúc dữ liệu từ '{self.source}' không như mong đợi: {e}")

    def _fetch_yfinance(self, start: str, end: str) -> pd.DataFrame:
        """ ✅ Tải dữ liệu chứng khoán từ Yahoo Finance """
        symbol = self.symbol
        if not symbol.endswith(".VN"):
            symbol += ".VN"

        try:
            df = yf.download(symbol, start=start, end=end, interval="1d", auto_adjust=True, progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            return df
        except Exception as e:
            raise IOError(f"Lỗi khi tải dữ liệu từ '{self.source}': {e}")

    def _fetch_bigquery(self, start: str, end: str) -> pd.DataFrame:
        """ ✅ Tải dữ liệu chứng khoán từ BigQuery """
        try:
            service_account = Credentials.from_service_account_info(self.credential)
            dataset_id = self.credential["dataset_id"]
            client = bigquery.Client(credentials=service_account, location="US")

            query = f"""
                SELECT `Date`, `Close Adj` * 1000 AS `Close`, `High Adj` * 1000 AS `High`,
                       `Low Adj` * 1000 AS `Low`, `Open Adj` * 1000 AS `Open`, `Volume`
                FROM `{dataset_id}.histories`
                WHERE `Symbol` = @symbol
            """
            # Khởi tạo danh sách tham số
            params = [bigquery.ScalarQueryParameter("symbol", "STRING", self.symbol)]

            # Thêm điều kiện ngày nếu có
            if start:
                query += " AND `Date` >= @start_date"
                params.append(bigquery.ScalarQueryParameter("start_date", "DATE", dt.strptime(start, '%Y-%m-%d').date()))

            if end:
                query += " AND `Date` <= @end_date"
                params.append(bigquery.ScalarQueryParameter("end_date", "DATE", dt.strptime(end, '%Y-%m-%d').date()))

            query += " ORDER BY Date ASC"

            # Thiết lập job config với tham số
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            rows = client.query(query, job_config=job_config).result()

            return pd.DataFrame([dict(row) for row in rows]).set_index("Date")
        except BadRequest as e:
            raise ValueError(f"Lỗi truy vấn '{self.source}' (BadRequest): {e}")
        except Exception as e:
            raise IOError(f"Lỗi khi tải dữ liệu từ '{self.source}': {e}")
