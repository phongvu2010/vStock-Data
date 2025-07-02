import pandas as pd
import pytest
from unittest.mock import Mock
from vstock_data import StockVN


# --- Dữ liệu giả lập (Fixtures) ---
# Sử dụng @pytest.fixture để tạo dữ liệu có thể tái sử dụng trong các test
@pytest.fixture
def mock_tcbs_response():
    """ Tạo một đối tượng Mock Response giả lập cho API của TCBS. """
    mock_resp = Mock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": [
            {
                "tradingDate": "2024-01-02T00:00:00",
                "open": 50.0, "high": 52.0, "low": 49.5, "close": 51.5, "volume": 100000
            },
            {
                "tradingDate": "2024-01-03T00:00:00",
                "open": 51.5, "high": 53.0, "low": 51.0, "close": 52.5, "volume": 120000
            }
        ]
    }
    return mock_resp

# --- Các Test Case ---
def test_initialization_success():
    """ Kiểm tra xem class có khởi tạo thành công với tham số hợp lệ không. """
    stock = StockVN(symbol='FPT', source='tcbs')
    assert stock.symbol == 'FPT'
    assert stock.source == 'tcbs'

def test_initialization_invalid_source():
    """ Kiểm tra xem class có báo lỗi ValueError khi nguồn không hợp lệ. """
    with pytest.raises(ValueError) as excinfo:
        StockVN(symbol='FPT', source='invalid_source')
    # Kiểm tra nội dung của thông báo lỗi
    assert "không được hỗ trợ" in str(excinfo.value)

def test_fetch_tcbs_success_mocked(mocker, mock_tcbs_response):
    """
    Kiểm tra chức năng fetch_data với nguồn TCBS bằng cách mock API call.
    `mocker` là một fixture đặc biệt từ pytest-mock.
    """
    # 1. Giả lập `requests.get`
    # Khi code của bạn gọi `requests.get`, nó sẽ bị thay thế và trả về dữ liệu giả lập của chúng ta
    mocker.patch('requests.get', return_value=mock_tcbs_response)

    # 2. Chạy code thật
    stock = StockVN(symbol='FPT', source='tcbs')
    df = stock.fetch_data(start='2024-01-01', end='2024-01-03')

    # 3. Kiểm tra kết quả (Assertions)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) == 2
    assert list(df.columns) == ['Close', 'High', 'Low', 'Open', 'Volume']
    assert df.index.name == 'Date'
    assert df['Close'].iloc[0] == 51.5

def test_fetch_data_empty_response_mocked(mocker):
    """Kiểm tra trường hợp API trả về dữ liệu rỗng."""
    mock_resp = Mock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"data": []} # Dữ liệu rỗng
    mocker.patch('requests.get', return_value=mock_resp)
    
    stock = StockVN(symbol='XYZ', source='tcbs')
    
    # Kiểm tra xem có báo lỗi ValueError như mong đợi không
    with pytest.raises(ValueError) as excinfo:
        stock.fetch_data()
    assert "Không tìm thấy dữ liệu" in str(excinfo.value)