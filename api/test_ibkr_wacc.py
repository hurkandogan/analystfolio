import asyncio
from ib_async import IB, Stock

async def test():
    ib = IB()
    await ib.connectAsync('127.0.0.1', 4001, clientId=99)
    contract = Stock('AAPL', 'SMART', 'USD')
    try:
        # reqFundamentalData returns XML string
        xml1 = await ib.reqFundamentalDataAsync(contract, 'ReportSnapshot')
        print("Snapshot:", "WACC" in xml1)
        xml2 = await ib.reqFundamentalDataAsync(contract, 'ReportsFinSummary')
        print("FinSummary:", "WACC" in xml2)
        xml3 = await ib.reqFundamentalDataAsync(contract, 'ReportRatios')
        print("Ratios:", "WACC" in xml3)
    except Exception as e:
        print("Error:", e)
    finally:
        ib.disconnect()

asyncio.run(test())
