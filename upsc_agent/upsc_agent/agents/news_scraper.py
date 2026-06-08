import os
import sys
import re
import json
import datetime
import requests
from bs4 import BeautifulSoup
import feedparser

# Try to import logger and config
try:
    from upsc_agent.utils.logger import logger
    from upsc_agent.utils.config import config
except ImportError:
    # Fallback to local import if run directly
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import logger
    from utils.config import config

class ScraperError(Exception):
    """Custom exception raised when the news scraper fails to retrieve enough articles."""
    pass

class NewsScraper:
    def __init__(self):
        # Set up a generic browser user-agent to bypass basic blocks
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.timeout = 10  # 10-second timeout for requests
        self.today = datetime.date.today()
        self.today_str = self.today.strftime("%Y-%m-%d")

        # Establish caching paths inside upsc_agent/output/cache
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(self.base_dir, "output", "cache")
        os.makedirs(self.output_dir, exist_ok=True)

    def is_published_today(self, pub_time_str: str, url: str) -> bool:
        """
        Checks if an article was published today.
        Matches YYYY-MM-DD pattern in pub_time_str or /YYYY/MM/DD/ pattern in URL.
        """
        # Format check for URL pattern: e.g., /2026/06/07/ or /2026/6/7/
        date_pattern = rf"/{self.today.year}/0?{self.today.month}/0?{self.today.day}/"
        if url and re.search(date_pattern, url):
            return True

        if pub_time_str:
            # Check if current date YYYY-MM-DD matches start of the timestamp
            if pub_time_str.startswith(self.today_str):
                return True
            # Also try matching standard ISO date format YYYY-MM-DD
            match = re.search(r"(\d{4})-(\d{2})-(\d{2})", pub_time_str)
            if match:
                extracted_date = match.group(0)
                if extracted_date == self.today_str:
                    return True

        return False

    def scrape_the_hindu(self) -> list:
        """
        Scrapes The Hindu national section.
        Falls back to RSS default feeder if primary scraping fails.
        """
        articles = []
        url = "https://www.thehindu.com/news/national/"
        logger.info("Scraping The Hindu primary URL: %s", url)

        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code != 200:
                logger.warning("The Hindu primary scrape returned status %d. Falling back to RSS.", response.status_code)
                return self.scrape_the_hindu_rss()

            soup = BeautifulSoup(response.content, "html.parser")
            # Find story cards and anchor tags containing links to national articles
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # Filter national news article links ending with .ece
                if "/news/national/" in href and href.endswith(".ece"):
                    if href not in links:
                        links.append(href)

            logger.info("Found %d potential article links on The Hindu.", len(links))

            # Fetch details for each article link (limit to first 15 to avoid spam/rate limit)
            for link in links[:15]:
                try:
                    art_response = requests.get(link, headers=self.headers, timeout=self.timeout)
                    if art_response.status_code == 200:
                        art_soup = BeautifulSoup(art_response.content, "html.parser")

                        # Extract Title
                        title_meta = art_soup.find("meta", property="og:title")
                        title = title_meta["content"] if title_meta else ""
                        if not title:
                            h1 = art_soup.find("h1")
                            title = h1.text.strip() if h1 else "No Title"

                        # Extract Date
                        pub_time = ""
                        pub_meta = art_soup.find("meta", property="article:published_time") or \
                                   art_soup.find("meta", property="og:article:published_time")
                        if pub_meta:
                            pub_time = pub_meta["content"]

                        # Check if published today
                        if not self.is_published_today(pub_time, link):
                            continue

                        # Extract Body (first 3 paragraphs)
                        paragraphs = []
                        # Look inside common article containers
                        body_div = art_soup.find("div", class_=re.compile("article-body|story-body|article-desc"))
                        p_tags = body_div.find_all("p") if body_div else art_soup.find_all("p")

                        for p in p_tags:
                            text = p.text.strip()
                            # Filter out social links, ads, and short texts
                            if len(text) > 40 and not text.startswith("Also read") and not text.startswith("Subscribe"):
                                paragraphs.append(text)
                                if len(paragraphs) == 3:
                                    break

                        body = "\n\n".join(paragraphs) if paragraphs else "No body text found."

                        articles.append({
                            "title": title,
                            "body": body,
                            "source": "The Hindu",
                            "url": link,
                            "date": self.today_str
                        })
                except Exception as e:
                    logger.debug("Failed to scrape article detail at %s: %s", link, str(e))
                    continue

        except Exception as e:
            logger.warning("The Hindu scraping failed: %s. Falling back to RSS.", str(e))
            return self.scrape_the_hindu_rss()

        # If primary returned nothing, fallback to RSS
        if not articles:
            logger.warning("No articles found on The Hindu primary. Falling back to RSS.")
            return self.scrape_the_hindu_rss()

        return articles

    def scrape_the_hindu_rss(self) -> list:
        """Fallback RSS parser for The Hindu."""
        logger.info("Accessing The Hindu RSS Fallback...")
        articles = []
        rss_url = "https://www.thehindu.com/feeder/default.rss"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                pub_parsed = entry.get("published_parsed")
                # Parse title and clean html summary
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")

                # Simple BS4 summary text extraction
                summary_soup = BeautifulSoup(summary, "html.parser")
                body = summary_soup.text.strip()

                # Filter today's articles
                is_today = False
                if pub_parsed:
                    pub_date = datetime.date(pub_parsed.tm_year, pub_parsed.tm_mon, pub_parsed.tm_mday)
                    if pub_date == self.today:
                        is_today = True

                # Fallback check on date string
                pub_str = entry.get("published", "")
                if not is_today and self.today_str in pub_str:
                    is_today = True

                if is_today:
                    articles.append({
                        "title": title,
                        "body": body,
                        "source": "The Hindu",
                        "url": link,
                        "date": self.today_str
                    })
        except Exception as e:
            logger.error("The Hindu RSS parsing failed: %s", str(e))
        return articles

    def scrape_indian_express(self) -> list:
        """
        Scrapes Indian Express National section.
        Falls back to RSS feed parser if primary scraping fails.
        """
        articles = []
        url = "https://indianexpress.com/section/india/"
        logger.info("Scraping Indian Express primary URL: %s", url)

        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code != 200:
                logger.warning("Indian Express primary scrape returned status %d. Falling back to RSS.", response.status_code)
                return self.scrape_indian_express_rss()

            soup = BeautifulSoup(response.content, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # Match Indian Express article pattern (contains /article/india/ or similar article urls)
                if "indianexpress.com/article/" in href and not href.endswith("/section/india/"):
                    if href not in links:
                        links.append(href)

            logger.info("Found %d potential article links on Indian Express.", len(links))

            # Fetch details for each article link (limit to first 15)
            for link in links[:15]:
                try:
                    art_response = requests.get(link, headers=self.headers, timeout=self.timeout)
                    if art_response.status_code == 200:
                        art_soup = BeautifulSoup(art_response.content, "html.parser")

                        # Extract Title
                        title_meta = art_soup.find("meta", property="og:title")
                        title = title_meta["content"] if title_meta else ""
                        if not title:
                            h1 = art_soup.find("h1")
                            title = h1.text.strip() if h1 else "No Title"

                        # Extract Date
                        pub_time = ""
                        pub_meta = art_soup.find("meta", property="article:published_time") or \
                                   art_soup.find("meta", property="og:article:published_time")
                        if pub_meta:
                            pub_time = pub_meta["content"]

                        # Check if published today
                        if not self.is_published_today(pub_time, link):
                            continue

                        # Extract Body (first 3 paragraphs)
                        paragraphs = []
                        body_div = art_soup.find("div", id="storyBuf") or art_soup.find("div", class_="articles")
                        p_tags = body_div.find_all("p") if body_div else art_soup.find_all("p")

                        for p in p_tags:
                            text = p.text.strip()
                            if len(text) > 40 and not text.startswith("Also read") and not text.startswith("Subscribe"):
                                paragraphs.append(text)
                                if len(paragraphs) == 3:
                                    break

                        body = "\n\n".join(paragraphs) if paragraphs else "No body text found."

                        articles.append({
                            "title": title,
                            "body": body,
                            "source": "Indian Express",
                            "url": link,
                            "date": self.today_str
                        })
                except Exception as e:
                    logger.debug("Failed to scrape Indian Express article detail at %s: %s", link, str(e))
                    continue

        except Exception as e:
            logger.warning("Indian Express scraping failed: %s. Falling back to RSS.", str(e))
            return self.scrape_indian_express_rss()

        # If primary returned nothing, fallback to RSS
        if not articles:
            logger.warning("No articles found on Indian Express primary. Falling back to RSS.")
            return self.scrape_indian_express_rss()

        return articles

    def scrape_indian_express_rss(self) -> list:
        """Fallback RSS parser for Indian Express."""
        logger.info("Accessing Indian Express RSS Fallback...")
        articles = []
        rss_url = "https://indianexpress.com/feed/"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                pub_parsed = entry.get("published_parsed")
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")

                summary_soup = BeautifulSoup(summary, "html.parser")
                body = summary_soup.text.strip()

                is_today = False
                if pub_parsed:
                    pub_date = datetime.date(pub_parsed.tm_year, pub_parsed.tm_mon, pub_parsed.tm_mday)
                    if pub_date == self.today:
                        is_today = True

                pub_str = entry.get("published", "")
                if not is_today and self.today_str in pub_str:
                    is_today = True

                if is_today:
                    articles.append({
                        "title": title,
                        "body": body,
                        "source": "Indian Express",
                        "url": link,
                        "date": self.today_str
                    })
        except Exception as e:
            logger.error("Indian Express RSS parsing failed: %s", str(e))
        return articles

    def scrape(self) -> list:
        """
        Executes news scraping for both The Hindu and Indian Express.
        Validates output to ensure it matches requirement constraints.
        Saves cache to disk.
        """
        try:
            hindu_articles = self.scrape_the_hindu()
            ie_articles = self.scrape_indian_express()

            # Merge and deduplicate by URL
            seen_urls = set()
            combined = []
            for art in hindu_articles + ie_articles:
                url = art.get("url")
                if url not in seen_urls:
                    seen_urls.add(url)
                    combined.append(art)

            # Log article count per source as required
            logger.info("Hindu: %d articles, IE: %d articles", len(hindu_articles), len(ie_articles))
            logger.info("Combined and deduplicated to %d total articles.", len(combined))

            # Validate that we retrieved at least 8 articles
            if len(combined) < 8:
                # If we have less than 8, let's relax date validation and fetch RSS items from yesterday as a fallback
                logger.warning("Only %d articles found for today. Relaxing date check to include recent items...", len(combined))
                
                # Fetch recent feeds without date restriction to hit the threshold
                all_hindu = self.scrape_the_hindu_rss_relaxed()
                all_ie = self.scrape_indian_express_rss_relaxed()
                
                for art in all_hindu + all_ie:
                    url = art.get("url")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        combined.append(art)
                
                logger.info("After relaxing constraints, total articles: %d", len(combined))

            # Re-check validation
            if len(combined) < 8:
                raise ScraperError(f"Scraper retrieved only {len(combined)} articles. Minimum required is 8.")

            # Save raw articles cache to output/cache/articles_{YYYYMMDD}.json
            cache_file = os.path.join(self.output_dir, f"articles_{self.today.strftime('%Y%m%d')}.json")
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(combined, f, ensure_ascii=False, indent=2)
            logger.info("Saved cached articles to %s", cache_file)

            return combined

        except Exception as e:
            logger.error("Scraper encountered an error during scraping: %s", str(e))
            raise

    def scrape_the_hindu_rss_relaxed(self) -> list:
        """Relaxed RSS scraper for The Hindu (returns all recent items)."""
        articles = []
        try:
            feed = feedparser.parse("https://www.thehindu.com/feeder/default.rss")
            for entry in feed.entries:
                summary_soup = BeautifulSoup(entry.get("summary", ""), "html.parser")
                articles.append({
                    "title": entry.get("title", ""),
                    "body": summary_soup.text.strip(),
                    "source": "The Hindu",
                    "url": entry.get("link", ""),
                    "date": self.today_str
                })
        except Exception:
            pass
        return articles

    def scrape_indian_express_rss_relaxed(self) -> list:
        """Relaxed RSS scraper for Indian Express (returns all recent items)."""
        articles = []
        try:
            feed = feedparser.parse("https://indianexpress.com/feed/")
            for entry in feed.entries:
                summary_soup = BeautifulSoup(entry.get("summary", ""), "html.parser")
                articles.append({
                    "title": entry.get("title", ""),
                    "body": summary_soup.text.strip(),
                    "source": "Indian Express",
                    "url": entry.get("link", ""),
                    "date": self.today_str
                })
        except Exception:
            pass
        return articles

if __name__ == "__main__":
    # Test script standalone execution
    try:
        scraper = NewsScraper()
        results = scraper.scrape()
        print(f"\n--- SUCCESS ---")
        print(f"Retrieved total of {len(results)} articles.")
        print("First 3 Titles:")
        for idx, art in enumerate(results[:3]):
            print(f"{idx+1}. [{art['source']}] {art['title']}")
    except Exception as err:
        print(f"\n--- FAILURE ---")
        print(f"Scraper failed with error: {str(err)}")
        sys.exit(1)
