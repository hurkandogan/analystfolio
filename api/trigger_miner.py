import asyncio
from app.strategies.fundamental_miner import FundamentalMinerBot

async def run_miner():
    print("🚀 Starting Manual Fundamental Miner (Deep Scan)...")
    bot = FundamentalMinerBot()
    # We don't need to manually set attributes because they are hardcoded in execute() for this one-time run.
    await bot.execute()
    print("✅ Manual Mining Task Finished.")

if __name__ == "__main__":
    asyncio.run(run_miner())
