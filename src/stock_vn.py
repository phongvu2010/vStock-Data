import pandas as pd
import time

from datetime import datetime as dt


class StockVNData:
    def __init__(self, symbol: str, source: str = "yfinance", credential: dict = None):
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
        ALLOWED_SOURCES = ["yfinance", "bigquery", "tcbs"]
        source_lower = source.lower() # Chuyển source thành chữ thường để kiểm tra

        if source_lower not in ALLOWED_SOURCES:
            raise ValueError(f"Nguồn '{source}' không được hỗ trợ. Vui lòng chọn một trong các nguồn sau: {ALLOWED_SOURCES}")

        if source_lower == "bigquery" and not credential:
            raise ValueError(f"Nguồn '{source}' yêu cầu phải có tham số 'credential'.")

        self.symbol = symbol.upper()
        self.source = source
        self.credential = credential

    def fetch_data(self, start_date: str = None, end_date: str = None, interval: str = "B"):
        if self.source.lower() == "yfinance":
            df = self.fetch_data_from_yfinance(start_date, end_date)

        elif self.source.lower() == "bigquery":
            df = self.fetch_data_from_bigquery(start_date, end_date)

        elif self.source.lower() == "tcbs":
            df = self.fetch_data_from_tcbs(start_date, end_date)

        else:
            raise ValueError(f"Nguồn '{self.source}' không được hỗ trợ.")

        if df.empty:
            raise ValueError(f"Dữ liệu '{self.symbol}' không tồn tại từ nguồn '{self.source}'.")

        df.columns = ["Close", "High", "Low", "Open", "Volume"]
        df.index.name = "Date"
        df.index = pd.to_datetime(df.index)

        if interval != "B":
            df = df.resample(self.interval).agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            })

        return df.sort_index()

    def fetch_data_from_yfinance(self, start_date = None, end_date = None):
        """
            ✅ Tải dữ liệu chứng khoán từ Yahoo Finance
        """
        import yfinance as yf

        try:
            return yf.download(
                self.symbol + ".VN", start=start_date, end=end_date,
                interval="1d", period="5y", auto_adjust=True, progress=False
            )
        except Exception as e:
            raise ValueError(f"Lỗi khi tải dữ liệu từ Yahoo Finance: {str(e)}")

    def fetch_data_from_bigquery(self, start_date = None, end_date = None):
        """
            ✅ Tải dữ liệu chứng khoán từ BigQuery
        """
        from google.api_core.exceptions import BadRequest
        from google.cloud import bigquery
        from google.oauth2.service_account import Credentials

        try:
            service_account = Credentials.from_service_account_info(self.credential)
            client = bigquery.Client(
                credentials=service_account, location="US"
            )

            statment_date = ""
            if start_date is None:
                statment_date += " AND `Date` >= '" & start_date & "'"

            if end_date is None:
                statment_date += " AND `Date` >= '" & end_date & "'"

            dataset_id = self.credential["dataset_id"]
            query_job = client.query(f"""
                SELECT
                    `Date`,
                    `Close Adj` * 1000 AS Close,
                    `High Adj` * 1000 AS High,
                    `Low Adj` * 1000 AS Low,
                    `Open Adj` * 1000 AS Open,
                    `Volume`
                FROM `{ dataset_id }.histories`
                WHERE
                    `Symbol` = "{ self.symbol }"
                    { statment_date }
                ORDER BY Date ASC
            """)
            rows = query_job.result()

            return pd.DataFrame([dict(row) for row in rows]).set_index("Date")
        except BadRequest as e:
            raise ValueError(f"Lỗi khi gọi API BigQuery: {str(e)}")
        except Exception as e:
            raise ValueError(f"Lỗi khi tải dữ liệu từ BigQuery: {str(e)}")

    def fetch_data_from_tcbs(self, start_date = None, end_date = None):
        """
            ✅ Tải dữ liệu chứng khoán từ TCBS
        """
        import requests

        try:
            if start_date is None:
                start_date = "2000-01-01"
            fd = int(time.mktime(dt.strptime(start_date, "%Y-%m-%d").timetuple()))

            if end_date is None:
                end_date = dt.now().strftime("%Y-%m-%d")
            td = int(time.mktime(dt.strptime(end_date, "%Y-%m-%d").timetuple()))

            url = "https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term"
            data = requests.get(f"{url}?ticker={self.symbol}&type=stock&resolution=D&from={fd}&to={td}")

            df = pd.json_normalize(data.json()["data"])
            df["tradingDate"] = pd.to_datetime(df.tradingDate.str.split("T", expand=True)[0])

            return df.set_index("tradingDate")[["close", "high", "low", "open", "volume"]]
        except Exception as e:
            raise ValueError(f"Lỗi khi tải dữ liệu từ TCBS: {str(e)}")
