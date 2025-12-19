from enum import Enum

class ViewName(str, Enum):
    DASHBOARD = "dashboard"
    ANALYTICS = "analytics"
    SETTINGS = "settings"

class DataRole(str, Enum):
    TRADE = "TRADE"       # Al-Sat yaptıklarımız
    MACRO = "MACRO"       # VIX, Tahvil faizi vb. takip ettiklerimiz
    BENCHMARK = "BENCH"   # S&P 500 gibi kıyaslama endeksleri

class SecType(str, Enum):
    STOCK = "STK"
    OPTION = "OPT"
    FUTURE = "FUT"
    INDEX = "IND"
    CASH = "CASH"

class Exchange(str, Enum):
    SMART = "SMART"
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"