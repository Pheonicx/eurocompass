# 🧭 EuroCompass

> **A cloud-powered financial intelligence platform for comparing EUR exchange rates across Bangladeshi banks.**

EuroCompass automatically collects live EUR exchange rates, tracks historical trends, recommends the most cost-effective bank for international transfers, and updates itself every hour using GitHub Actions.

---

## 🚀 Live Site

**Dashboard:** https://eurocompass.eurocompass.workers.dev

The site is a static page (`site/index.html`) hosted on Cloudflare, and reads
`exports/latest.json` and `history/*.csv` directly from this repository on
every page load — so it always reflects the latest hourly update with no
redeploy required.

---

## ✨ Key Features

- 💶 Live EUR exchange rates from multiple Bangladeshi banks
- 📈 Historical exchange-rate tracking
- 🏦 Intelligent bank recommendation engine, for both sending money to
  Germany (TT selling rate) and converting EUR back to BDT (TT buying rate)
- 💸 Transfer calculator with support for additional costs (transfer fees,
  student file charges) in BDT, EUR, or USD
- ☁️ Automatic hourly updates with GitHub Actions
- 📂 GitHub-based historical storage (no database required)
- 🤖 Telegram bot integration

## 🎯 Why EuroCompass?

Students and professionals sending money from Bangladesh to Europe often compare exchange rates across multiple banks.

EuroCompass automates this process by:

- Collecting live EUR exchange rates
- Comparing transfer costs
- Recommending the lowest-cost bank
- Tracking historical trends over time
- Providing a public dashboard for easy analysis

Instead of manually checking multiple banking websites, users can make informed financial decisions using a single platform.

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │ Bangladeshi Banks   │
                    │ BRAC • CITY • EBL • PRIME • SONALI
                    └──────────┬──────────┘
                               │
                               ▼
                     Python Collectors
                               │
                               ▼
                  Data Processing & Analysis
                               │
             ┌─────────────────┴─────────────────┐
             ▼                                   ▼
     Latest Market Snapshot              Historical CSV Files
             │                                   │
             ▼                                   ▼
      exports/latest.json                 history/*.csv
             │                                   │
             └───────────────┬───────────────────┘
                             │
                             ▼
                  GitHub Repository (Pheonicx/eurocompass)
                             │
                             ▼
              Static Dashboard (site/index.html)
              fetched live on every page load,
              hosted on Cloudflare
                             ▲
                             │
                  GitHub Actions (Hourly)
```

### Data Flow

1. Collect live EUR exchange rates from supported banks.
2. Process and validate exchange-rate data.
3. Export the latest market snapshot to `exports/latest.json`.
4. Update historical CSV files in `history/` and push to GitHub.
5. The static dashboard fetches both files live from GitHub on every visit —
   no build or redeploy needed for new rates to appear.
6. Recommend the most cost-effective bank for transfers, in either direction.

## 🛠️ Technology Stack

| Category | Technology |
|----------|------------|
| Language (data pipeline) | Python 3.12 |
| Dashboard | Static HTML/CSS/JS, Chart.js |
| Dashboard Hosting | Cloudflare Pages/Workers |
| Web Requests | Requests |
| Web Scraping | BeautifulSoup |
| PDF Rate Extraction | pdfplumber |
| Automation | GitHub Actions |
| Version Control | Git & GitHub |
| Environment Management | python-dotenv |
| Notifications | Telegram Bot API |
| Data Storage | CSV + JSON, GitHub Repository |

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/Pheonicx/eurocompass.git
cd eurocompass
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 🔑 Configuration

Create a `.env` file in the project root (copy `.env.example` as a starting point).

```env
GITHUB_TOKEN=your_personal_access_token
GITHUB_USERNAME=your_github_username
GITHUB_REPO=your_repository_name
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

> **Note:** Never commit your `.env` file. It is already excluded by `.gitignore`.

## ▶️ Usage

### Collect Live Exchange Rates

Run:

```bash
python main.py
```

This will:

- Collect the latest EUR exchange rates
- Calculate market statistics
- Export the latest snapshot
- Update historical CSV files
- Synchronize history with GitHub

---

### View the Dashboard

The dashboard is a static site — no local server needed. Either open
`site/index.html` directly in a browser, or visit the live deployed version:

https://eurocompass.eurocompass.workers.dev

---

### Automatic Updates

EuroCompass uses **GitHub Actions** to automatically run every hour.

Each run:

- Collects fresh exchange rates
- Updates historical data
- Pushes changes to GitHub
- The live dashboard picks up the new data automatically on next visit

Whenever `site/index.html` itself is changed and pushed, Cloudflare
redeploys the site automatically within a minute or two.

## 📁 Project Structure

```text
EuroCompass/
│
├── collectors/          # Bank-specific collectors
├── config/               # Configuration
├── data/                # Latest market data
├── exports/              # latest.json snapshot
├── history/              # Historical CSV files
├── services/             # Shared services (market data, transfer calculator)
├── site/                 # Static dashboard, deployed to Cloudflare
├── telegram_bot/         # Telegram bot
├── utils/                # Helper modules
├── worker/                # Cloudflare Worker (Telegram webhook)
│
├── .github/
│   └── workflows/
│       └── update_rates.yml
│
├── main.py
├── requirements.txt
└── README.md
```

## 🗺️ Roadmap

### ✅ Version 1.0

- Live exchange-rate collectors
- Historical tracking
- Germany transfer calculator
- GitHub Actions automation
- Telegram bot integration

### ✅ Version 2.0

- Static dashboard on Cloudflare, replacing the Streamlit app
- Buy/sell direction toggle (send to Germany vs. convert to BDT)
- Fee-aware transfer calculator (BDT/EUR/USD)
- Cost-by-bank comparison table

### 🚀 Future Improvements

- Additional currencies (USD, GBP, etc.)
- Exchange-rate forecasting
- Trend and volatility analysis
- Personalized alerts

## 📄 License

This project is licensed under the **MIT License**.

See the `LICENSE` file for details.

## 🙏 Acknowledgements

Thanks to the official banking websites and publicly available exchange-rate information that make this project possible.

This project was built as a learning exercise in software engineering, automation, and financial data analysis.
