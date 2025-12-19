import pandas as pd
import os

# This script checks for overlapping stocks between Nasdaq 100 and S&P 500

def check_intersection():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nasdaq_path = os.path.join(base_dir, 'raw_data', 'nasdaq.csv')
    sp500_path = os.path.join(base_dir, 'raw_data', 'sp500.csv')

    if not os.path.exists(nasdaq_path) or not os.path.exists(sp500_path):
        print("❌ CSV files not found! Please run 'task scrape' first.")
        return

    df_ndx = pd.read_csv(nasdaq_path)
    df_spx = pd.read_csv(sp500_path)

    ndx_set = set(df_ndx.iloc[:, 0].str.strip().str.upper())
    spx_set = set(df_spx.iloc[:, 0].str.strip().str.upper())
    common_stocks = ndx_set.intersection(spx_set)
    
    only_nasdaq = ndx_set - spx_set

    print("\n" + "="*40)
    print("📊 MARKET OVERLAP ANALYSIS")
    print("="*40)
    print(f"🔹 Nasdaq 100 Total : {len(ndx_set)}")
    print(f"🔹 S&P 500 Total    : {len(spx_set)}")
    print("-" * 40)
    print(f"🤝 COMMON STOCKS    : {len(common_stocks)} items")
    print(f"🦄 ONLY NASDAQ      : {len(only_nasdaq)} items (Not yet in S&P 500)")
    print("="*40)
    
    print("\n📜 Examples of Common Stocks (First 10):")
    print(list(sorted(common_stocks))[:10])
    
    print("\n📜 Only in Nasdaq (Potential Stars?):")
    print(list(sorted(only_nasdaq)))

if __name__ == "__main__":
    check_intersection()