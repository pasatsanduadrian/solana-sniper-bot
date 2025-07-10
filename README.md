[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USERNAME/solana-sniper-bot/blob/main/notebooks/sniper_colab.ipynb)

Bot automat pentru trading de meme-coins pe Solana cu strategie de sniping pentru token-uri noi.

## 🎯 Features

- **🔍 Scanner Automat**: Monitorizează token-uri noi pe Solana via DEX Screener
- **📊 Analiză Multi-Sursă**: Agregare date din Moralis și DEX Screener  
- **🤖 Trading Automat**: Entry/exit bazat pe score și parametri configurabili
- **💰 Management Poziții**: Take profit, stop loss, position sizing
- **📈 Dashboard Live**: Interfață Gradio pentru monitorizare în timp real
- **🚀 Detecție 3x/5x/10x**: Heuristici simple pentru identificarea pump-urilor
- **🔒 Wallet Secure**: Suport pentru Phantom și alte wallet-uri Solana

## 🚀 Quick Start în Google Colab

### 1️⃣ Deschide în Colab
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USERNAME/solana-sniper-bot/blob/main/notebooks/sniper_colab.ipynb)

### 2️⃣ Pregătește Cheile API

Înainte de a rula în Colab, ai nevoie de:

1. **Moralis API Key** (Gratuit)
   - Înregistrează-te la [moralis.io](https://moralis.io/)
   - Dashboard → Web3 APIs → Copy API Key

2. **Helius API Key** (Opțional, pentru features avansate)
   - Înregistrează-te la [helius.dev](https://www.helius.dev/)
   - Dashboard → API Keys → Create New Key

3. **Phantom Wallet Private Key**
   - Deschide Phantom → Settings → Security & Privacy
   - Show Secret Recovery Phrase sau Export Private Key
   - **IMPORTANT**: Folosește un wallet de test cu fonduri mici!

### 3️⃣ Rulează în Colab

În notebook-ul Colab, urmează pașii din interfața interactivă.

### 🔬 Testare rapidă Moralis API

Pentru a verifica dacă cheia Moralis funcționează, rulează scriptul
`test_moralis_api.py` sau deschide notebook-ul dedicat:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USERNAME/solana-sniper-bot/blob/main/notebooks/moralis_api_test.ipynb)

Setează variabila `MORALIS_KEY` în mediul Colab pentru a putea accesa
endpoint-urile Moralis.

### 🛠 Integrare API-uri

Proiectul folosește trei surse principale de date:

1. **DEX Screener** – căutare perechi noi pe Solana
   ```python
   from src.api.dexscreener import DexScreenerAPI
   api = DexScreenerAPI()
   pairs = await api.search_tokens("solana")
   ```

2. **Moralis** – prețuri și metadata token
   ```python
   from src.api.moralis import MoralisAPI
   api = MoralisAPI("YOUR_MORALIS_KEY")
   price = await api.get_token_price("mainnet", token_address)
   ```

3. **Helius** – detalii suplimentare despre holderi
   ```python
   from src.api.helius import HeliusAPI
   api = HeliusAPI("YOUR_HELIUS_KEY")
   holders = await api.get_token_holders(token_address)
   ```

Aceste module pot fi testate rapid în Google Colab folosind notebook-ul
`notebooks/sniper_colab.ipynb`.

## ⚠️ Disclaimer

**AVERTISMENT**: Trading-ul de crypto implică **RISC EXTREM DE MARE**.

- Poți pierde **TOȚI** banii investiți
- Bot-ul este pentru **SCOP EDUCAȚIONAL**
- Nu garantăm profit
- Începe cu sume mici (<$50)

## 📜 Licență

Proiect open-source sub licența MIT. Vezi [LICENSE](LICENSE) pentru detalii.

---

**⚡ Happy Trading & Stay Safe!**
