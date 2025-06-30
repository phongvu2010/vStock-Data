import pandas as pd
import time

from datetime import datetime as dt
from functools import lru_cache


class StockVNData:
    def __init__(self, symbol: str, source: str = "yfinance", credential: dict = None):
        """
        Khởi tạo đối tượng StockVNData.
        Args:
            symbol (str): Mã chứng khoán (ví dụ: "FPT").
            source (str, optional): Nguồn dữ liệu. Chỉ chấp nhận "yfinance", "tcbs", hoặc "bigquery". Mặc định là "yfinance".
            credential (dict, optional): Thông tin xác thực cho BigQuery. Bắt buộc nếu source là "bigquery".

        Raises:
            ValueError: Nếu 'source' không hợp lệ hoặc 'credential' bị thiếu khi cần.
        """
        ALLOWED_SOURCES = ["yfinance", "bigquery", "tcbs"]
        source_lower = source.lower() # Chuyển source thành chữ thường để kiểm tra

        if source_lower not in ALLOWED_SOURCES:
            raise ValueError(f"Nguồn '{ source }' không được hỗ trợ. Vui lòng chọn một trong các nguồn sau: { ALLOWED_SOURCES }")

        if source_lower == "bigquery":
            if not isinstance(credential, dict) or not credential:
                raise ValueError(f"Nguồn '{ source }' yêu cầu tham số 'credential' phải là một dictionary không rỗng.")

        self.symbol = symbol.upper()
        self.source = source_lower
        self.credential = credential

    @lru_cache(maxsize = 128)
    def fetch_data(self, start: str = None, end: str = None, interval: str = "B"):
        if self.source == "yfinance":
            df = self.fetch_data_from_yfinance(start, end)

        elif self.source == "bigquery":
            df = self.fetch_data_from_bigquery(start, end)

        elif self.source == "tcbs":
            df = self.fetch_data_from_tcbs(start, end)

        else:
            raise ValueError(f"Nguồn '{ self.source }' không được hỗ trợ.")

        if df.empty:
            raise ValueError(f"Dữ liệu '{ self.symbol }' không tồn tại từ nguồn '{ self.source }'.")

        df.rename(columns = {
            "close": "Close", "high": "High", "low": "Low", "open": "Open", "volume": "Volume"
        }, inplace = True)
        df.index.name = "Date"
        df.index = pd.to_datetime(df.index)

        if interval != "B":
            df = df.resample(interval).agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            })

        return df.sort_index()

    def fetch_data_from_yfinance(self, start = None, end = None):
        """
            ✅ Tải dữ liệu chứng khoán từ Yahoo Finance
        """
        import yfinance as yf

        try:
            df = yf.download(
                self.symbol + ".VN",
                start=start, end=end,
                interval="1d", period="5y",
                auto_adjust=True, progress=False
            )
            df.columns = df.columns.droplevel(1)
            return df
        except Exception as e:
            raise ValueError(f"Lỗi khi tải dữ liệu từ Yahoo Finance: { str(e) }")

    def fetch_data_from_bigquery(self, start = None, end = None):
        """
            ✅ Tải dữ liệu chứng khoán từ BigQuery
        """
        from google.api_core.exceptions import BadRequest
        from google.cloud import bigquery
        from google.oauth2.service_account import Credentials

        try:
            service_account = Credentials.from_service_account_info(self.credential)
            dataset_id = self.credential["dataset_id"]
            client = bigquery.Client(credentials=service_account, location="US")

            query = f"""
                SELECT
                    `Date`,
                    `Close Adj` * 1000 AS `Close`,
                    `High Adj` * 1000 AS `High`,
                    `Low Adj` * 1000 AS `Low`,
                    `Open Adj` * 1000 AS `Open`,
                    `Volume`
                FROM `{ dataset_id }.histories`
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
            query_job = client.query(query, job_config=job_config)
            rows = query_job.result()

            return pd.DataFrame([dict(row) for row in rows]).set_index("Date")
        except BadRequest as e:
            raise ValueError(f"Lỗi khi gọi API BigQuery: { str(e) }")
        except Exception as e:
            raise ValueError(f"Lỗi khi tải dữ liệu từ BigQuery: { str(e) }")

    def fetch_data_from_tcbs(self, start = None, end = None):
        """
            ✅ Tải dữ liệu chứng khoán từ TCBS
        """
        import requests
        from json import JSONDecodeError
        from requests.exceptions import RequestException

        try:
            if start is None: start = "2000-01-01"
            fd = int(time.mktime(dt.strptime(start, "%Y-%m-%d").timetuple()))

            if end is None: end = dt.now().strftime("%Y-%m-%d")
            td = int(time.mktime(dt.strptime(end, "%Y-%m-%d").timetuple()))

            url = "https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term"
            response = requests.get(f"{ url }?ticker={ self.symbol }&type=stock&resolution=D&from={ fd }&to={ td }", timeout=10)
            response.raise_for_status() # Tự động báo lỗi nếu request không thành công
            json_data = response.json()

            if "data" not in json_data or not json_data["data"]:
                raise ValueError("API của TCBS không trả về dữ liệu.")

            df = pd.json_normalize(json_data["data"])
            df["tradingDate"] = pd.to_datetime(df.tradingDate.str.split("T", expand=True)[0])
            df["tradingDate"] = pd.to_datetime(df["tradingDate"])

            return df.set_index("tradingDate")[["close", "high", "low", "open", "volume"]]
        except RequestException as e:
            raise ConnectionError(f"Lỗi khi tải dữ liệu từ TCBS: { str(e) }")
        except JSONDecodeError:
            raise ValueError(f"Không thể giải mã JSON từ TCBS. Phản hồi từ server: { response.text }")
        except (KeyError, IndexError) as e:
            raise ValueError(f"Cấu trúc dữ liệu trả về từ TCBS không như mong đợi: { str(e) }")
