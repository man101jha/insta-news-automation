# Indian Finance News Instagram Automation Bot

A premium, multi-agent Python system designed to scrape daily Indian financial news, select the top 5 most actionable stories for retail investors, auto-generate a sleek 7-slide dark-mode square carousel containing real news images, request team approval via a interactive Telegram Group, and publish the approved post live to Instagram.

---

## 🚀 Key Features

*   **Multi-Source Aggregator:** Scrapes the latest financial headlines from **Economic Times Markets**, **Livemint**, **Moneycontrol**, and **r/IndiaInvestments** (Reddit).
*   **AI-Powered Editing:** Uses Groq's `llama-3.3-70b-versatile` to select, score, and summarize the top 5 retail investor stories.
*   **Dynamic Carousel Generation:** Renders a 7-slide square (1080x1080px) slide deck with a dark slate layout. **Automatically fetches real background images** from the news pages (`og:image`), applies a dark overlay, displays a source attribution tag, and appends metric pills.
*   **Interactive Team Approval:** Dispatches preview slide galleries to a private **Telegram Group** using custom polling, allowing multiple team members to click **Approve** or **Reject** with live clicker attribution logging.
*   **Auto-Publishing:** Hosts slide assets on Litterbox and posts the carousel to your Instagram Professional Account via the **Instagram Graph API**.
*   **GitHub Actions Automation:** Runs automatically on the GitHub cloud daily at **8:40 AM IST (3:10 AM UTC)**, cleaning up all temporary local image files on completion.

---

## 📂 Project Architecture

```text
insta-automation/
├── .github/
│   └── workflows/
│       └── daily_run.yml       # GitHub Actions cron scheduler workflow
├── .gitignore                  # Excludes local virtual environments and .env secrets
├── README.md                   # Setup and system documentation (this file)
└── finance_agent/
    ├── main.py                 # Pipeline Orchestrator (houses main loop and try...finally cleanup)
    ├── requirements.txt        # Package dependencies (praw, feedparser, playwright, etc.)
    ├── .env                    # Local API keys and credentials (ignored by git)
    ├── .env.example            # Template of required environment variables
    ├── utils/
    │   ├── config.py           # Configuration parser and env validator
    │   └── logger.py           # Colored console logging output format
    └── agents/
        ├── news_scraper.py     # RSS Feeds and Reddit PRAW scraper agent
        ├── filter_agent.py     # Groq LLM ranking and selection editor agent
        ├── carousel_writer.py  # Instagram copywriting text generation agent
        ├── canva_builder.py    # Playwright HTML/CSS to PNG image builder agent
        ├── telegram_bot.py     # Interactive Telegram group approval callback bot agent
        └── instagram_poster.py # Litterbox uploader & Instagram Graph API publisher agent
```

---

## 🛠️ Step-by-Step Setup Guide

### 1. Prerequisites
Before setting up the project, make sure you have:
*   **Python 3.11+** installed.
*   **Git** installed.
*   **Groq API Key:** Sign up at [console.groq.com](https://console.groq.com/) and grab a free API Key.
*   **Telegram Bot:** Create a bot via `@BotFather` on Telegram.
*   **Instagram Professional Account:** Ensure your Instagram account is switched to a Creator or Business account and linked to a Facebook Page. Create a Meta Developer App to retrieve your **Instagram Business Account ID** and a **Page Access Token**.

---

### 2. Local Installation & Configuration

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/man101jha/insta-news-automation.git
    cd insta-news-automation
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    # On Windows:
    python -m venv finance_agent/venv
    finance_agent/venv/Scripts/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r finance_agent/requirements.txt
    ```

4.  **Install Playwright Headless Browser:**
    ```bash
    playwright install chromium
    ```

5.  **Configure Environment Variables:**
    Duplicate `finance_agent/.env.example` as `finance_agent/.env` and fill in your keys:
    ```env
    GROQ_API_KEY=your_groq_api_key
    
    # Telegram Configuration (use a negative number for Groups, e.g., -100123456789)
    TELEGRAM_BOT_TOKEN=your_bot_token
    TELEGRAM_CHAT_ID=your_group_chat_id
    
    # Instagram Configuration
    INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_id
    INSTAGRAM_ACCESS_TOKEN=your_long_lived_meta_access_token
    ```

---

### 3. Run the Bot Locally

Once the `.env` parameters are populated, navigate to the `finance_agent` directory and run the orchestrator:
```bash
cd finance_agent
python main.py
```
*   The script will log progress in the terminal.
*   A preview of the 7 slide images will be sent to your Telegram Group.
*   Tapping **Approve & Post** will publish the carousel to Instagram.
*   Tapping **Reject & Cancel** will terminate the pipeline.
*   All temporary files (`slide_*.png`, `bg_slide_*.jpg`) will be automatically deleted from the local disk on completion.

---

### 4. GitHub Actions Cloud Automation

The workflow file is already configured at the root repository directory under `.github/workflows/daily_run.yml`.

1.  **Register Secrets on GitHub:**
    Go to your GitHub repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**, and register:
    *   `GROQ_API_KEY`
    *   `TELEGRAM_BOT_TOKEN`
    *   `TELEGRAM_CHAT_ID`
    *   `INSTAGRAM_BUSINESS_ACCOUNT_ID`
    *   `INSTAGRAM_ACCESS_TOKEN`
    *   *(Optional: Reddit PRAW keys if scraping custom subreddits)*

2.  **Trigger Scheduler:**
    *   Click on the **Actions** tab of your repository.
    *   Select **Daily Finance Carousel Automation** on the left.
    *   Click the **Run workflow** button to test the cloud environment manually.
    *   The workflow will trigger automatically **every day at 8:40 AM IST (3:10 AM UTC)**.
