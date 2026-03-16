# 📊 Portfolio Morning Brief
**Daily AI-powered stock news digest — free, automated, delivered to your inbox by 7 AM IST**

Powered by: **Groq (LLaMA3-70B)** · **Google News RSS** · **GitHub Actions** · **Gmail**

---

## What It Does

Every morning (Mon–Sat), this workflow:
1. Reads your stock list from `config.yaml`
2. Fetches last 24 hours of news from Google News, MoneyControl, Economic Times
3. Sends each stock's news to Groq's free LLaMA3 API for equity analysis
4. Builds a clean HTML email report with sentiment, key events, and analyst notes
5. Delivers it to your inbox before markets open

**Zero cost. No paid APIs.**

---

## Setup — Step by Step

### Step 1: Fork / Clone this repository
```bash
git clone https://github.com/YOUR_USERNAME/portfolio-morning-brief
cd portfolio-morning-brief
```

### Step 2: Get your free API keys

#### A) Groq API Key (Free)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free, no credit card needed)
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

#### B) Gmail App Password
> ⚠️ Use App Password, NOT your Gmail password. Required if you have 2FA (recommended).

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select app: **Mail** → Device: **Other** → name it "Portfolio Brief"
3. Copy the 16-character password shown

### Step 3: Add secrets to GitHub
Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

| Secret Name      | Value                          |
|------------------|--------------------------------|
| `GROQ_API_KEY`   | Your Groq API key (`gsk_...`)  |
| `GMAIL_USER`     | Your Gmail address             |
| `GMAIL_APP_PASS` | 16-char Gmail app password     |
| `REPORT_TO`      | Email to receive reports (can be same as GMAIL_USER) |

### Step 4: Customize your portfolio
Edit `config.yaml` — replace the sample stocks with your actual holdings:

```yaml
portfolio:
  - ticker: "RELIANCE"
    name: "Reliance Industries"
    exchange: "NSE"
    keywords: ["Reliance Industries", "RIL", "Jio", "Mukesh Ambani"]

  - ticker: "HDFCBANK"
    name: "HDFC Bank"
    exchange: "NSE"
    keywords: ["HDFC Bank", "HDFCBANK"]
```

**Tips for keywords:**
- Include the company's popular abbreviation (RIL, TCS, etc.)
- Add sector keywords if relevant (e.g., "solar pump", "EV battery")
- 2–4 keywords per stock is ideal

### Step 5: Enable GitHub Actions
1. Go to repo → **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. The workflow runs automatically at **7:00 AM IST** (Mon–Sat)

### Step 6: Test manually
1. Go to **Actions** → **Daily Portfolio Morning Brief**
2. Click **Run workflow** → **Run workflow**
3. Check your inbox within 2–3 minutes

---

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GROQ_API_KEY="gsk_your_key_here"
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASS="your16charpassword"
export REPORT_TO="you@gmail.com"
export SAVE_REPORT_LOCAL="true"   # Saves report.html locally to preview

# Run
python main.py
```

Open the generated `report_*.html` in your browser to preview the email.

---

## File Structure

```
portfolio-morning-brief/
├── config.yaml          ← YOUR STOCK LIST (edit this)
├── main.py              ← Main orchestrator
├── news_fetcher.py      ← Fetches from Google News, MC, ET RSS
├── groq_analyser.py     ← Calls Groq LLaMA3 for analysis
├── report_builder.py    ← Builds HTML email
├── email_sender.py      ← Sends via Gmail SMTP
├── requirements.txt     ← Python dependencies
└── .github/
    └── workflows/
        └── daily_brief.yml  ← GitHub Actions scheduler
```

---

## Customising the Schedule

Edit `.github/workflows/daily_brief.yml`:
```yaml
# Current: 01:30 UTC = 07:00 AM IST
- cron: "30 1 * * 1-6"

# For 06:00 AM IST: use 00:30 UTC
- cron: "30 0 * * 1-6"

# For 7 days a week (including Sunday):
- cron: "30 1 * * *"
```
Use [crontab.guru](https://crontab.guru) to build your preferred schedule.

---

## Free Tier Limits

| Service | Free Limit | Usage per run |
|---|---|---|
| GitHub Actions | 2,000 min/month | ~3 min/run = ~78 min/month ✅ |
| Groq API | 14,400 req/day | 1 req per stock ✅ |
| Google News RSS | Unlimited | Free ✅ |
| Gmail SMTP | 500 emails/day | 1/day ✅ |

---

## Adding Pipeline 2 (Transcript Analyser)

Coming next — quarterly earnings transcript analysis with 1–2 quarter and 1–2 year outlook using Gemini 1.5 Pro's 1M context window.

---

## Disclaimer
This tool is for personal informational use only. It is not SEBI-registered investment advice. Always do your own research before making investment decisions.
