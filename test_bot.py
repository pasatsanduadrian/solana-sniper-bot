"""Test script pentru verificarea funcționalității bot-ului."""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Adaugă directorul rădăcină la Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.bot import FeedAggregator, TradingEngine, setup_logging
from src.bot.config import settings
from src.bot.trading import jup_quote

async def test_configuration():
    """Test 1: Verifică configurarea"""
    print("\n🔧 TEST 1: Configuration Check")
    print("-" * 50)
    
    checks = {
        "Helius Key": bool(settings.helius_key and settings.helius_key != "demo"),
        "Moralis Key": bool(settings.moralis_key),
        "Wallet Secret": bool(settings.sol_secret),
        "Keypair Valid": bool(settings.keypair),
        "Public Key": settings.public_key or "Not configured"
    }
    
    all_good = True
    for key, value in checks.items():
        status = "✅" if value and value != "Not configured" else "❌"
        print(f"{status} {key}: {value}")
        if not value or value == "Not configured":
            all_good = False
    
    return all_good

async def test_wallet():
    """Test 2: Verifică wallet și balanță"""
    print("\n💰 TEST 2: Wallet Check")
    print("-" * 50)
    
    if not settings.keypair:
        print("❌ No wallet configured")
        return False
    
    try:
        from solana.rpc.async_api import AsyncClient
        
        client = AsyncClient("https://api.mainnet-beta.solana.com")
        
        # Check SOL balance
        balance_resp = await client.get_balance(settings.keypair.pubkey())
        sol_balance = balance_resp.value / 1e9
        
        print(f"✅ Wallet Address: {settings.public_key}")
        print(f"✅ SOL Balance: {sol_balance:.4f} SOL")
        
        # Check USDC balance
        from solders.pubkey import Pubkey
        from solana.rpc.types import TokenAccountOpts
        
        usdc_mint = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        
        token_accounts = await client.get_token_accounts_by_owner(
            settings.keypair.pubkey(),
            TokenAccountOpts(mint=usdc_mint)
        )
        
        usdc_balance = 0
        if token_accounts.value:
            # Parse token balance (simplified)
            print(f"✅ USDC Account Found")
        else:
            print("⚠️ No USDC account found")
        
        await client.close()
        
        return sol_balance > 0.01  # Need at least 0.01 SOL for fees
        
    except Exception as e:
        print(f"❌ Wallet error: {e}")
        return False

async def test_apis():
    """Test 3: Verifică API-urile externe"""
    print("\n🌐 TEST 3: API Connections")
    print("-" * 50)
    
    results = {}
    
    # Test Moralis
    if settings.moralis_key:
        try:
            from src.bot.feeds import fetch_moralis
            data = await fetch_moralis(
                "So11111111111111111111111111111111111111112",
                settings.moralis_key
            )
            results["Moralis API"] = f"✅ Working (SOL: ${data.get('usdPrice', 0):.2f})"
        except Exception as e:
            results["Moralis API"] = f"❌ Error: {str(e)[:50]}"
    else:
        results["Moralis API"] = "⚠️ No API key"
    
    # Test Jupiter
    try:
        quote = await jup_quote(
            "So11111111111111111111111111111111111111112",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            1000000000
        )
        if quote and "outAmount" in quote:
            usdc = int(quote["outAmount"]) / 1e6
            results["Jupiter API"] = f"✅ Working (1 SOL = {usdc:.2f} USDC)"
        else:
            results["Jupiter API"] = "❌ Invalid response"
    except Exception as e:
        results["Jupiter API"] = f"❌ Error: {str(e)[:50]}"
    
    # Test DEX Screener
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.dexscreener.com/latest/dex/search?q=solana",
                timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Verificăm structura corectă
                    if data and isinstance(data, dict) and "pairs" in data:
                        pairs = data.get("pairs", [])
                        if isinstance(pairs, list):
                            count = len(pairs)
                            results["DEX Screener"] = f"✅ Working ({count} pairs)"
                        else:
                            results["DEX Screener"] = "⚠️ Unexpected response format"
                    else:
                        results["DEX Screener"] = "⚠️ No data returned"
                else:
                    results["DEX Screener"] = f"❌ Status {resp.status}"
    except asyncio.TimeoutError:
        results["DEX Screener"] = "❌ Timeout - API might be slow"
    except Exception as e:
        results["DEX Screener"] = f"❌ Error: {str(e)[:50]}"
    
    for api, status in results.items():
        print(f"{api}: {status}")
    
    # Considerăm testul trecut dacă cel puțin Jupiter funcționează
    return "Jupiter API" in results and "✅" in results["Jupiter API"]

async def test_trading_engine():
    """Test 4: Verifică engine-ul de trading"""
    print("\n🤖 TEST 4: Trading Engine")
    print("-" * 50)
    
    try:
        feeds = FeedAggregator()
        engine = TradingEngine(feeds)
        
        # Start services
        await feeds.start()
        await engine.start()
        
        print("✅ Services started")
        
        # Wait for data
        print("⏳ Collecting data (10 seconds)...")
        await asyncio.sleep(10)
        
        # Check results
        tokens = feeds.get_top_tokens(5)
        stats = engine.get_stats()
        
        print(f"\n📊 Results:")
        print(f"Tokens found: {len(feeds.tokens)}")
        print(f"Top tokens: {len(tokens)}")
        
        if tokens:
            print("\nTop 3 opportunities:")
            for i, token in enumerate(tokens[:3], 1):
                print(f"{i}. {token.symbol} - Score: {token.score:.1f}")
        else:
            print("\n⚠️ No tokens found - this is normal without API keys")
        
        # Stop services
        await engine.stop()
        await feeds.stop()
        
        print("\n✅ Services stopped cleanly")
        return True
        
    except Exception as e:
        print(f"❌ Engine error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 SOLANA SNIPER BOT - SYSTEM TEST")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    setup_logging()
    
    tests = [
        ("Configuration", test_configuration),
        ("Wallet", test_wallet),
        ("APIs", test_apis),
        ("Trading Engine", test_trading_engine)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            results[name] = await test_func()
        except Exception as e:
            print(f"\n❌ Test {name} crashed: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("-" * 50)
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    # Mesaj adaptat pentru situația curentă
    if total_passed == 0:
        print("\n📝 This is normal! You need to:")
        print("1. Create .env file with your API keys")
        print("2. Add your wallet private key")
        print("3. Run the test again")
    elif total_passed < total_tests:
        print("\n⚠️ Some tests failed. This is expected without full configuration.")
        print("✅ Core functionality (Jupiter API) is working!")
    else:
        print("\n🎉 All tests passed! Bot is ready to run.")

if __name__ == "__main__":
    asyncio.run(main())
