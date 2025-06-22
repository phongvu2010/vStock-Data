import datetime as dt
import pandas as pd
import time


class StockVNData:
    def __init__(self, symbol: str, interval: str="B", source: str="yfinance", credential: dict=None):
        """
        Khởi tạo đối tượng StockVNData.

        Args:
            symbol (str): Mã chứng khoán (ví dụ: "FPT").
            interval (str, optional): Khoảng thời gian resampling ('B', 'W', 'M'). Mặc định là "B" (ngày làm việc).
            source (str, optional): Nguồn dữ liệu. Chỉ chấp nhận "yfinance", "tcbs", hoặc "bigquery". Mặc định là "yfinance".
            credential (dict, optional): Thông tin xác thực cho BigQuery. Bắt buộc nếu source là "bigquery".

        Raises:
            ValueError: Nếu 'source' không hợp lệ hoặc 'credential' bị thiếu khi cần.
        """
        self.symbol = symbol.upper()
        self.interval = interval

        ALLOWED_SOURCES = ["yfinance", "bigquery", "tcbs"]
        source_lower = source.lower() # Chuyển source thành chữ thường để kiểm tra

        if source_lower not in ALLOWED_SOURCES:
            raise ValueError(f"Nguồn '{source}' không được hỗ trợ. Vui lòng chọn một trong các nguồn sau: {ALLOWED_SOURCES}")

        if source_lower == "bigquery" and not credential:
            raise ValueError(f"Nguồn '{source}' yêu cầu phải có tham số 'credential'.")

        self.source = source
        self.credential = credential
        self.data = pd.DataFrame()
        self.fetch_data()

    def fetch_data(self):
        if self.source.lower() == "yfinance":
            df = self.fetch_data_from_yfinance()

        elif self.source.lower() == "bigquery":
            df = self.fetch_data_from_bigquery()

        elif self.source.lower() == "tcbs":
            df = self.fetch_data_from_tcbs()

        else:
            raise ValueError(f"Nguồn '{self.source}' không được hỗ trợ.")

        if df.empty:
            raise ValueError(f"Dữ liệu '{self.symbol}' không tồn tại từ nguồn '{self.source}'.")

        df.columns = ["Close", "High", "Low", "Open", "Volume"]
        df.index.name = "Date"
        df.index = pd.to_datetime(df.index)

        if self.interval != "B":
            df = df.resample(self.interval).agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            })

        self.data = df.sort_index()

    def fetch_data_from_yfinance(self) -> pd.DataFrame:
        """
            ✅ Tải dữ liệu chứng khoán từ Yahoo Finance
        """
        import yfinance as yf

        try:
            return yf.download(
                self.symbol + ".VN", interval="1d", period="5y", auto_adjust=True, progress=False
            )
        except Exception as e:
            print(f"[Error] {e}")
            raise ValueError(f"Lỗi khi tải dữ liệu từ Yahoo Finance: {str(e)}")

    def fetch_data_from_bigquery(self) -> pd.DataFrame:
        """
            ✅ Tải dữ liệu chứng khoán từ BigQuery
        """
        from google.api_core.exceptions import BadRequest
        from google.cloud import bigquery
        from google.oauth2.service_account import Credentials

        try:
            client = bigquery.Client(
                credentials=Credentials.from_service_account_info(self.credential),
                location="US"
            )

            dataset_id = self.credential["dataset_id"]
            query_job = client.query(f"""
                SELECT
                    Date, `Close Adj` * 1000, `High Adj` * 1000, `Low Adj` * 1000, `Open Adj` * 1000, Volume
                FROM `{dataset_id}.histories`
                WHERE `Symbol` = "{self.symbol}" 
                ORDER BY Date ASC
            """)
            rows = query_job.result()

            return pd.DataFrame([dict(row) for row in rows]).set_index("Date")
        except BadRequest as e:
            print(f"[Error] {e}")
            raise ValueError(f"Lỗi khi gọi API BigQuery: {str(e)}")
        except Exception as e:
            print(f"[Error] {e}")
            raise ValueError(f"Lỗi khác khi tải dữ liệu từ BigQuery: {str(e)}")

    def fetch_data_from_tcbs(self) -> pd.DataFrame:
        """
            ✅ Tải dữ liệu chứng khoán từ TCBS
        """
        import requests

        try:
            fd = int(time.mktime(dt.date(2000, 1, 1).timetuple()))
            td = int(time.mktime(dt.date.today().timetuple()))

            url = "https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term"
            data = requests.get(f"{url}?ticker={self.symbol}&type=stock&resolution=D&from={fd}&to={td}")

            df = pd.json_normalize(data.json()["data"])
            df["tradingDate"] = pd.to_datetime(df.tradingDate.str.split("T", expand = True)[0])

            return df.set_index("tradingDate")[["close", "high", "low", "open", "volume"]]
        except Exception as e:
            print(f"[Error] {e}")
            raise ValueError(f"Lỗi khi tải dữ liệu từ TCBS: {str(e)}")
