import firebase_admin
from firebase_admin import credentials, firestore
import asyncio
import json
import os
import math
from datetime import datetime
from enum import Enum
from app.config import settings

class AssetType(str, Enum):
    ASSET = "ASSET"
    OPTION = "OPTION"
    CASH = "CASH"
    CRYPTO = "CRYPTO"

class FirebaseClient:
    def __init__(self):
        self.db = None
        self.user_id = settings.FIREBASE_USER_ID
        self._initialized = False
        self.etf_mapping = self._load_etf_mapping()

    def _load_etf_mapping(self):
        try:
            # app/infrastructure/firebase_client.py -> app/
            app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            map_path = os.path.join(app_path, "data", "etf_mapping.json")
            if os.path.exists(map_path):
                with open(map_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load ETF mapping: {e}")
        return {}

    def _ensure_initialized(self):
        if not self._initialized:
            try:
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                key_path = os.path.join(base_path, "serviceAccountKey.json")
                
                if not os.path.exists(key_path):
                    print(f"❌ Firebase Error: {key_path} not found!")
                    return

                if not firebase_admin._apps:
                    cred = credentials.Certificate(key_path)
                    firebase_admin.initialize_app(cred)
                
                self.db = firestore.client()
                self._initialized = True
                print("✅ Firebase initialized successfully.")
            except Exception as e:
                print(f"❌ Firebase initialization failed: {e}")
                self.db = None

    async def sync_portfolio(self, portfolio_items, cash_positions, enrichment_map):
        return await asyncio.to_thread(self._sync_process, portfolio_items, cash_positions, enrichment_map)

    def _sync_process(self, portfolio_items, cash_positions, enrichment_map):
        self._ensure_initialized()
        if not self.db:
            return False, "Firebase connection failed."

        try:
            batch = self.db.batch()
            assets_ref = self.db.collection('users').document(self.user_id).collection('assets')
            
            docs = assets_ref.where('source', '==', 'IBKR').stream()
            existing_ids = {doc.id for doc in docs}
            current_ids = set()

            # 1. Aggregate Portfolio Positions (Summing duplicates across accounts/exchanges)
            aggregated_portfolio = {}
            for item in portfolio_items:
                # Skip closed positions (qty == 0)
                if float(item.position) == 0:
                    continue
                    
                symbol = item.contract.symbol.strip().upper() if item.contract.symbol else "UNKNOWN"
                sec_type = item.contract.secType
                
                if sec_type == 'OPT':
                    identifier = item.contract.localSymbol.replace(' ', '') if item.contract.localSymbol else f"{symbol}_OPT_{item.contract.conId}"
                    doc_id = f"IBKR_{identifier}"
                    asset_type = AssetType.OPTION
                else:
                    doc_id = f"IBKR_{symbol.replace(' ', '_')}"
                    asset_type = AssetType.ASSET
                
                if doc_id not in aggregated_portfolio:
                    details = enrichment_map.get(symbol, {})
                    sector = details.get('sector')
                    industry = details.get('industry')
                    
                    if symbol in self.etf_mapping:
                        sector = self.etf_mapping[symbol]['sector']
                        industry = self.etf_mapping[symbol]['industry']
                        
                    aggregated_portfolio[doc_id] = {
                        "item": item,
                        "total_position": float(item.position),
                        "market_value_sum": float(item.marketValue),
                        "weighted_avg_cost": float(item.averageCost),
                        "weighted_pnl_unrealized": float(item.unrealizedPNL),
                        "weighted_pnl_realized": float(item.realizedPNL),
                        "asset_type": asset_type,
                        "symbol": symbol,
                        "sector": sector,
                        "industry": industry
                    }
                else:
                    # Sum values for existing doc_id
                    agg = aggregated_portfolio[doc_id]
                    agg["total_position"] += float(item.position)
                    agg["market_value_sum"] += float(item.marketValue)
                    agg["weighted_pnl_unrealized"] += float(item.unrealizedPNL)
                    agg["weighted_pnl_realized"] += float(item.realizedPNL)

            # 2. Sync to Firebase
            current_ids = set()
            for doc_id, agg in aggregated_portfolio.items():
                current_ids.add(doc_id)
                doc_ref = assets_ref.document(doc_id)
                item = agg["item"]

                data = {
                    "id": doc_id,
                    "type": agg["asset_type"],
                    "source": "IBKR",
                    "symbol": agg["symbol"],
                    "name": item.contract.localSymbol or agg["symbol"],
                    "currency": item.contract.currency,
                    "amount": str(agg["total_position"]),
                    "avg_cost": str(item.averageCost), # Using last known avg cost for now
                    "current_price": str(item.marketPrice),
                    "market_value": str(agg["market_value_sum"]),
                    "unrealized_pnl": str(agg["weighted_pnl_unrealized"]),
                    "realized_pnl": str(agg["weighted_pnl_realized"]),
                    "multiplier": str(item.contract.multiplier) if item.contract.multiplier else "1",
                    "cost_basis_money": str(agg["total_position"] * item.averageCost),
                    "sector": agg["sector"],
                    "industry": agg["industry"],
                    "is_active": True,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
                
                batch.set(doc_ref, data, merge=True)

            for cash in cash_positions:
                curr = cash['currency']
                val = cash['value']
                
                doc_id = f"IBKR_{curr}"
                current_ids.add(doc_id)
                
                doc_ref = assets_ref.document(doc_id)
                
                data = {
                    "id": doc_id,
                    "type": AssetType.CASH,
                    "source": "IBKR",
                    "symbol": curr,
                    "name": f"{curr} Cash",
                    "currency": curr,
                    "amount": str(val),
                    "avg_cost": "1.0",
                    "current_price": "1.0",
                    "market_value": str(val),
                    "unrealized_pnl": "0",
                    "realized_pnl": "0",
                    "multiplier": "1",
                    "cost_basis_money": str(val),
                    "sector": "Cash",
                    "industry": "Cash",
                    "is_active": True,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
                batch.set(doc_ref, data, merge=True)

            # --- SOFT DELETE (Set items missing from IBKR to zero) ---
            ids_to_deactivate = existing_ids - current_ids
            for doc_id in ids_to_deactivate:
                doc_ref = assets_ref.document(doc_id)
                batch.set(doc_ref, {
                    "amount": "0",
                    "market_value": "0",
                    "is_active": False,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }, merge=True)

            batch.commit()
            return True, f"Synced {len(portfolio_items)} items + {len(cash_positions)} cash. Deactivated {len(ids_to_deactivate)} missing items."

        except Exception as e:
            return False, str(e)

    async def sync_kraken_portfolio(self):
        """
        Fetches Kraken balance, prices it, and writes to Firebase.
        """
        from app.infrastructure.kraken_client import kraken_client
        
        # 1. Fetch Balance
        balances = await kraken_client.get_account_balance()
        if not balances or "error" in balances:
            print(f"❌ Kraken Sync Error: {balances}")
            return

        # 2. Normalize and Aggregate (Aggregation)
        # Kraken sometimes gives same asset like ETH and ETH.S (Staked) in separate rows.
        # We aggregate these under a single 'ETH' symbol.
        aggregated = {}
        
        for asset, amount in balances.items():
            amount = float(amount)
            if amount < 0.00000001: continue 
            
            # --- Normalization Logic ---
            symbol = asset
            
            # 1. Suffix cleanup (.S, .M, .B etc.)
            if '.' in symbol:
                symbol = symbol.split('.')[0]
            
            # 2. Prefix and Code Transformations (Kraken Standards)
            if symbol in ['XXBT', 'XBT']: symbol = 'BTC'
            elif symbol in ['XETH', 'ETH2']: symbol = 'ETH'
            elif symbol == 'XXRP': symbol = 'XRP'
            elif symbol == 'XLTC': symbol = 'LTC'
            elif symbol == 'XXDG': symbol = 'DOGE'
            elif symbol == 'XXLM': symbol = 'XLM'
            elif symbol == 'ZUSD': symbol = 'USD'
            elif symbol == 'ZEUR': symbol = 'EUR'
            elif symbol == 'ZGBP': symbol = 'GBP'
            
            aggregated[symbol] = aggregated.get(symbol, 0.0) + amount

        kraken_assets = []

        # 3. Price and Prepare the List
        for symbol, amount in aggregated.items():
            price = 1.0
            
            # Fetch price for non-fiat and non-stablecoin assets
            if symbol not in ['USD', 'EUR', 'GBP', 'USDT', 'USDC']:
                # Fetch Price (BTC -> XBTUSD)
                pair = f"{symbol}USD"
                if symbol == 'BTC': pair = 'XBTUSD'
                if symbol == 'ETH': pair = 'ETHUSD'
                if symbol == 'XRP': pair = 'XRPUSD'
                
                ticker = await kraken_client.get_ticker(pair)
                if ticker:
                    price = float(ticker['c'][0])
            
            # Special rate correction for EUR/GBP/JPY etc. to USD
            currency = "USD"
            if symbol in ['EUR', 'GBP', 'JPY', 'CHF', 'HKD', 'TRY']:
                currency = symbol
                # For the market value calculation, we need to know the price in USD
                # If symbol is EUR, we already fetched EURUSD price above or specifically below
                if symbol == 'EUR':
                    ticker = await kraken_client.get_ticker('EURUSD')
                    if ticker: price = float(ticker['c'][0])
                elif symbol == 'GBP':
                    ticker = await kraken_client.get_ticker('GBPUSD')
                    if ticker: price = float(ticker['c'][0])
                # ... other currencies could be added if needed, but price is already 1.0 or handled
            
            market_value = amount * price
            
            kraken_assets.append({
                "id": f"KRAKEN_{symbol}",
                "type": AssetType.CRYPTO,
                "source": "KRAKEN",
                "symbol": symbol,
                "name": f"{symbol}",
                "currency": currency,
                "amount": str(amount),
                "current_price": str(price),
                "market_value": str(market_value),
                "avg_cost": "0", # Fetching cost from Kraken API is complex, 0 or manual for now
                "unrealized_pnl": "0",
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
        # 4. Firebase Operations (Add/Update and DELETE)
        # Now calling special method that both adds and deletes.
        await asyncio.to_thread(self._sync_kraken_process, kraken_assets)

    def _get_all_user_ids(self):
        self._ensure_initialized()
        try:
            from firebase_admin import auth
            users = auth.list_users()
            return [user.uid for user in users.iterate_all()]
        except Exception as e:
            # Fallback to database stream if Auth API lacks permissions
            print(f"Auth list_users failed, falling back: {e}")
            if not self.db: return []
            users_ref = self.db.collection('users')
            docs = users_ref.stream()
            return [doc.id for doc in docs]

    async def sync_all_users_manual_assets(self):
        """
        Iterates over all users and updates their manual assets.
        """
        user_ids = await asyncio.to_thread(self._get_all_user_ids)
        for uid in user_ids:
            try:
                await self.sync_manual_assets(target_uid=uid)
            except Exception as e:
                print(f"Failed to sync manual assets for {uid}: {e}")

    async def sync_all_users_crypto(self):
        """
        Iterates over all users and updates their CRYPTO assets with Kraken prices.
        Skips the primary user as they have full Kraken wallet sync.
        """
        user_ids = await asyncio.to_thread(self._get_all_user_ids)
        for uid in user_ids:
            if uid == self.user_id:
                continue  # Primary user already has full Kraken sync
            try:
                await self._sync_user_crypto_prices(uid)
            except Exception as e:
                print(f"Failed to sync crypto for {uid}: {e}")

    async def _sync_user_crypto_prices(self, uid):
        """
        Fetches CRYPTO-type assets for a user and updates their prices from Kraken.
        """
        from app.infrastructure.kraken_client import kraken_client
        
        self._ensure_initialized()
        if not self.db: return

        # Fetch Categories
        category_map = await asyncio.to_thread(self._fetch_category_map, uid)
        
        assets_ref = self.db.collection('users').document(uid).collection('assets')
        docs = assets_ref.where('type', '==', AssetType.CRYPTO).stream()
        crypto_docs = [doc.to_dict() for doc in docs]
        
        if not crypto_docs:
            return
        
        updates = []
        for doc in crypto_docs:
            category_id = doc.get('category_id')
            cat_type = 'ASSET'
            if category_id and category_id in category_map:
                cat_type = category_map[category_id].get('type', 'ASSET')

            if cat_type == 'CASH':
                continue # Skip cash positions in crypto list (theyll be handled as 1.0 elsewhere if needed)

            symbol = doc.get('symbol', '').strip().upper()
            if not symbol or symbol in ['USD', 'EUR', 'GBP']:
                continue
            
            # Build Kraken pair
            pair = f"{symbol}USD"
            if symbol == 'BTC': pair = 'XBTUSD'
            elif symbol == 'ETH': pair = 'ETHUSD'
            elif symbol == 'XRP': pair = 'XRPUSD'
            
            try:
                ticker = await kraken_client.get_ticker(pair)
                if ticker:
                    price = float(ticker['c'][0])
                    amount = float(doc.get('amount', 0))
                    avg_cost = float(doc.get('avg_cost', 0))
                    market_val = amount * price
                    cost_basis = amount * avg_cost
                    unrealized = market_val - cost_basis
                    
                    updates.append({
                        "id": doc['id'],
                        "type": AssetType.CRYPTO,
                        "current_price": str(price),
                        "market_value": str(market_val),
                        "unrealized_pnl": str(unrealized),
                        "cost_basis_money": str(cost_basis),
                        "updated_at": firestore.SERVER_TIMESTAMP
                    })
            except Exception as e:
                print(f"⚠️ Kraken price fetch failed for {symbol}: {e}")
        
        if updates:
            await asyncio.to_thread(self._batch_update_assets, updates, uid)
            print(f"✅ Updated {len(updates)} Crypto assets for user '{uid}'.")

    def _fetch_category_map(self, uid):
        """
        Fetches the category map for a user from the 'categories' collection.
        Returns: {category_id: {'name': str, 'type': str}}
        """
        self._ensure_initialized()
        if not self.db: return {}
        
        try:
            categories_ref = self.db.collection('users').document(uid).collection('categories')
            docs = categories_ref.stream()
            
            category_map = {}
            for doc in docs:
                data = doc.to_dict()
                cat_id = doc.id
                category_map[cat_id] = {
                    'name': data.get('name', 'Unknown'),
                    'type': data.get('type', 'ASSET')
                }
            return category_map
        except Exception as e:
            print(f"⚠️ Error fetching category map for {uid}: {e}")
            return {}

    async def sync_manual_assets(self, target_uid=None):
        """
        Reads MANUAL assets from Firebase, updates their prices from IBKR or yfinance.
        If the asset belongs to a category with type 'CASH', price is locked to 1.0.
        """
        uid = target_uid or self.user_id
        from app.infrastructure.ibkr_client import ibkr_client
        from ib_async import Stock
        
        # 0. Fetch Categories
        category_map = await asyncio.to_thread(self._fetch_category_map, uid)

        # Accept delayed-frozen data 
        ibkr_client.ib.reqMarketDataType(4)

        # 1. Read Manual Assets
        manual_docs = await asyncio.to_thread(self._fetch_manual_docs, uid)
        if not manual_docs: return

        # 2. Fetch Prices
        contracts = []
        doc_map = {}
        cash_updates = []
        
        for doc in manual_docs:
            symbol = doc.get('symbol', '').strip()
            currency = doc.get('currency', 'USD')
            exchange = doc.get('exchange', 'SMART')
            category_id = doc.get('category_id')
            
            # Use category type if available
            cat_type = 'ASSET'
            if category_id and category_id in category_map:
                cat_type = category_map[category_id].get('type', 'ASSET')

            if cat_type == 'CASH':
                # Lock price to 1.0 for CASH categories
                price = 1.0
                amount = float(doc.get('amount', 0))
                avg_cost = float(doc.get('avg_cost', 0))
                
                market_val = amount * price
                cost_basis = amount * avg_cost
                unrealized = market_val - cost_basis
                
                cash_updates.append({
                    "id": doc['id'],
                    "current_price": str(price),
                    "market_value": str(market_val),
                    "unrealized_pnl": str(unrealized),
                    "cost_basis_money": str(cost_basis),
                    "updated_at": firestore.SERVER_TIMESTAMP
                })
                continue

            if symbol:
                c = Stock(symbol, exchange, currency)
                contracts.append(c)
                doc_map[symbol.upper()] = doc
        
        # Apply Cash Updates immediately
        if cash_updates:
            await asyncio.to_thread(self._batch_update_assets, cash_updates, uid)
            print(f"💵 Locked {len(cash_updates)} CASH assets to 1.0 for user '{uid}'.")

        if not contracts: return

        # FIX: conId's must be filled before calling reqTickersAsync
        try:
            await ibkr_client.ib.qualifyContractsAsync(*contracts)
        except Exception as e:
            print(f"⚠️ Manual Asset Qualification Error: {e}")

        # Request only successfully qualified contracts (with conId > 0)
        valid_contracts = [c for c in contracts if c.conId > 0]
        if not valid_contracts: return

        # 2.1 Fetch Details (Sector/Industry)
        details_map = {}
        async def fetch_details(contract):
            try:
                d_list = await ibkr_client.ib.reqContractDetailsAsync(contract)
                return contract.symbol, (d_list[0] if d_list else None)
            except:
                return contract.symbol, None

        results = await asyncio.gather(*[fetch_details(c) for c in valid_contracts])
        details_map = {sym: det for sym, det in results if det}

        # IBKR Snapshot
        tickers = await ibkr_client.ib.reqTickersAsync(*valid_contracts)
        
        updates = []
        for t in tickers:
            symbol = t.contract.symbol.upper()
            if symbol in doc_map:
                doc = doc_map[symbol]
                price = t.marketPrice()
                
                # FALLBACK: If IBKR price is invalid (NaN, 0, or -1) due to subscription errors
                if not price or math.isnan(price) or price <= 0:
                    try:
                        import yfinance as yf
                        # Some users might enter LHA.DE directly, or we can try to guess for common cases
                        yf_symbol = symbol
                        # If its a non-USD currency, it likely needs a suffix in yfinance (e.g. .DE, .L)
                        # This is a basic heuristic; user can also enter the suffix in Firestore symbol.
                        ticker_data = await asyncio.to_thread(lambda: yf.Ticker(yf_symbol).fast_info)
                        price = ticker_data.get('lastPrice')
                        if price:
                            print(f"ℹ️ Used yfinance fallback price for {symbol}: {price}")
                    except Exception as yf_err:
                        print(f"⚠️ yfinance fallback failed for {symbol}: {yf_err}")

                if price and not math.isnan(price) and price > 0:
                    amount = float(doc.get('amount', 0))
                    avg_cost = float(doc.get('avg_cost', 0))
                    
                    market_val = amount * price
                    cost_basis = amount * avg_cost
                    unrealized = market_val - cost_basis
                    
                    update_data = {
                        "id": doc['id'],
                        "type": AssetType.ASSET,
                        "current_price": str(price),
                        "market_value": str(market_val),
                        "unrealized_pnl": str(unrealized),
                        "cost_basis_money": str(cost_basis),
                        "updated_at": firestore.SERVER_TIMESTAMP
                    }

                    if symbol in details_map:
                        update_data["sector"] = details_map[symbol].category
                        update_data["industry"] = details_map[symbol].industry


                    # Manual Mapping Override (ETF/ETC)
                    if symbol in self.etf_mapping:
                        update_data["sector"] = self.etf_mapping[symbol]['sector']
                        update_data["industry"] = self.etf_mapping[symbol]['industry']

                    updates.append(update_data)
        
        # 3. Write Updates
        if updates:
            await asyncio.to_thread(self._batch_update_assets, updates, uid)
            print(f"✅ Updated {len(updates)} Manual assets for user '{uid}'.")

    def _fetch_manual_docs(self, target_uid=None):
        self._ensure_initialized()
        if not self.db: return []
        
        uid = target_uid or self.user_id
        assets_ref = self.db.collection('users').document(uid).collection('assets')
        docs = assets_ref.where('source', '==', 'MANUAL').stream()
        return [doc.to_dict() for doc in docs]

    def _sync_kraken_process(self, assets):
        """
        Updates Kraken assets and deletes those no longer in wallet.
        """
        self._ensure_initialized()
        if not self.db: return

        batch = self.db.batch()
        assets_ref = self.db.collection('users').document(self.user_id).collection('assets')
        
        # A. Fetch existing Kraken assets (for deletion process)
        docs = assets_ref.where('source', '==', 'KRAKEN').stream()
        existing_ids = {doc.id for doc in docs}
        current_ids = {item['id'] for item in assets}

        # B. Update / Add
        for item in assets:
            item['is_active'] = True
            doc_ref = assets_ref.document(item['id'])
            batch.set(doc_ref, item, merge=True)

        # C. Soft Delete (Deactivate Kraken assets no longer in wallet)
        ids_to_deactivate = existing_ids - current_ids
        for doc_id in ids_to_deactivate:
            doc_ref = assets_ref.document(doc_id)
            batch.set(doc_ref, {
                "amount": "0",
                "market_value": "0",
                "is_active": False,
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)

        batch.commit()
        print(f"✅ Synced {len(assets)} Kraken assets. Deactivated {len(ids_to_deactivate)} items.")

    def _batch_update_assets(self, items, target_uid=None):
        self._ensure_initialized()
        if not self.db: return
        
        uid = target_uid or self.user_id
        batch = self.db.batch()
        assets_ref = self.db.collection('users').document(uid).collection('assets')
        
        for item in items:
            doc_ref = assets_ref.document(item['id'])
            # merge=True is critical: preserves fields like category_id
            batch.set(doc_ref, item, merge=True)
            
        batch.commit()

    async def create_all_users_daily_snapshots(self):
        """
        Iterates over all users and creates their daily snapshots.
        """
        user_ids = await asyncio.to_thread(self._get_all_user_ids)
        snapshots = {}
        for uid in user_ids:
            try:
                snap = await self.create_daily_snapshot(target_uid=uid)
                if snap:
                    snapshots[uid] = snap
            except Exception as e:
                print(f"Snapshot Creation Failed for {uid}: {e}")
        return snapshots

    async def create_daily_snapshot(self, target_uid=None):
        """
        Creates a daily portfolio summary (Snapshot) and saves it to the 'portfolio_history' collection.
        Holds a single record for each day (with YYYY-MM-DD ID).
        """
        self._ensure_initialized()
        if not self.db: return

        uid = target_uid or self.user_id
        try:
            # 1. Fetch Configuration (for categories) - Using unified fetcher
            category_map = await asyncio.to_thread(self._fetch_category_map, uid)

            # 2. Fetch Assets and Currency Rates
            assets_ref = self.db.collection('users').document(uid).collection('assets')
            assets_docs = await asyncio.to_thread(lambda: list(assets_ref.stream()))
            
            currencies_ref = self.db.collection('currencies')
            currency_docs = await asyncio.to_thread(lambda: list(currencies_ref.stream()))
            rates = {doc.id: doc.to_dict().get('rate', 1.0) for doc in currency_docs}
            
            total_market_value_usd = 0.0
            total_cost_basis_usd = 0.0
            total_unrealized_pnl_usd = 0.0
            
            category_breakdown = {} # category_id -> value_usd

            for doc in assets_docs:
                data = doc.to_dict()
                try:
                    mkt_val = float(data.get('market_value', 0))
                    cost = float(data.get('cost_basis_money', 0))
                    unrealized = float(data.get('unrealized_pnl', 0))
                    currency = data.get('currency', 'USD')
                except (ValueError, TypeError):
                    continue

                # Convert to USD if necessary
                rate_to_usd = 1.0
                if currency != 'USD':
                    rate_to_usd = rates.get(f"{currency}_USD", 1.0)
                
                mkt_val_usd = mkt_val * rate_to_usd
                cost_usd = cost * rate_to_usd
                unrealized_usd = unrealized * rate_to_usd

                total_market_value_usd += mkt_val_usd
                total_cost_basis_usd += cost_usd
                total_unrealized_pnl_usd += unrealized_usd
                
                # Category Based Total (FE assigned 'category_id' is used)
                cat_id = data.get('category_id', 'uncategorized')
                category_breakdown[cat_id] = category_breakdown.get(cat_id, 0.0) + mkt_val_usd

            # 3. Fetch Daily Transactions (Optional - if Transaction schema exists)
            daily_tx_count = 0
            try:
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                transactions_ref = self.db.collection('users').document(uid).collection('transactions')
                # If 'date' field exists, count those after today
                tx_docs = await asyncio.to_thread(lambda: list(transactions_ref.where('date', '>=', today_start).stream()))
                daily_tx_count = len(tx_docs)
            except Exception:
                pass 

            # 4. Prepare Snapshot Data
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            formatted_breakdown = []
            for cat_id, val in category_breakdown.items():
                cat_info = category_map.get(cat_id, {'name': 'Uncategorized', 'type': 'OTHER'})
                formatted_breakdown.append({
                    "category_id": cat_id,
                    "name": cat_info['name'],
                    "type": cat_info['type'],
                    "value": val,
                    "percentage": (val / total_market_value_usd * 100) if total_market_value_usd > 0 else 0
                })

            snapshot_data = {
                "date": today_str,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "total_market_value": total_market_value_usd,
                "total_cost_basis": total_cost_basis_usd,
                "total_unrealized_pnl": total_unrealized_pnl_usd,
                "daily_transaction_count": daily_tx_count,
                "allocation": formatted_breakdown,
                "asset_count": len(assets_docs)
            }

            # 5. Kaydet (portfolio_history/YYYY-MM-DD)
            history_ref = self.db.collection('users').document(uid).collection('portfolio_history').document(today_str)
            await asyncio.to_thread(history_ref.set, snapshot_data, merge=True)
            
            print(f"✅ Daily Snapshot created for {today_str} on user '{uid}'")
            return snapshot_data

        except Exception as e:
            print(f"❌ Snapshot Creation Failed: {e}")
            return None

    async def sync_currencies(self, rates):
        """
        Writes currency rates to the 'currencies' collection.
        """
        return await asyncio.to_thread(self._sync_currencies_process, rates)

    def _sync_currencies_process(self, rates):
        self._ensure_initialized()
        if not self.db: return

        batch = self.db.batch()
        currencies_ref = self.db.collection('currencies')
        
        for item in rates:
            doc_ref = currencies_ref.document(item['id'])
            batch.set(doc_ref, item, merge=True)
            
        batch.commit()
        print(f"✅ Successfully synced {len(rates)} currency rates to Firebase.")

firebase_client = FirebaseClient()
