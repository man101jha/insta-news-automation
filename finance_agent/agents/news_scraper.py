import feedparser
# pyrefly: ignore [missing-import]
import praw
import time
from datetime import datetime, timedelta
from utils.config import Config
from utils.logger import get_logger

# Initialize module logger
logger = get_logger("news_scraper")

# Default RSS Feeds for Indian finance news
RSS_FEEDS = {
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Livemint": "https://www.livemint.com/rss/markets",
    "Moneycontrol": "https://www.moneycontrol.com/rss/marketreports.xml"
}

class NewsScraper:
    """
    Agent responsible for scraping news from multiple RSS feeds and Reddit.
    Aggregates, normalizes, and dedupes findings.
    """
    
    def __init__(self):
        """
        Initialize the scraper and setup Reddit API client if credentials exist.
        """
        self.reddit_client = None
        self._init_reddit()

    def _init_reddit(self):
        """
        Safely initializes PRAW (Reddit API wrapper) with credentials.
        If credentials are missing or invalid, logs a warning and proceeds.
        Free Tier / Rate Limits: Reddit API limits requests to 60 requests per minute.
        """
        try:
            # Check if all required Reddit keys are set and not placeholder values
            if (Config.REDDIT_CLIENT_ID and 
                Config.REDDIT_CLIENT_SECRET and 
                Config.REDDIT_USER_AGENT and
                "your_" not in Config.REDDIT_CLIENT_ID):
                
                self.reddit_client = praw.Reddit(
                    client_id=Config.REDDIT_CLIENT_ID,
                    client_secret=Config.REDDIT_CLIENT_SECRET,
                    user_agent=Config.REDDIT_USER_AGENT,
                    # Short timeout to avoid hanging if Reddit is slow
                    timeout=10.0
                )
                logger.info("Reddit PRAW client initialized successfully.")
            else:
                logger.warning("Reddit API credentials missing or contains placeholders. Skipping Reddit scraping.")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {str(e)}")

    def scrape_rss_feed(self, source_name: str, feed_url: str) -> list[dict]:
        """
        Scrapes a single RSS feed using feedparser.
        
        Args:
            source_name: Name of the news source (e.g. 'Livemint')
            feed_url: RSS feed URL
        Returns:
            List of parsed article dicts.
        """
        articles = []
        logger.info(f"Scraping RSS feed: {source_name} ({feed_url})")
        
        try:
            # Parse the XML feed from the remote URL
            feed = feedparser.parse(feed_url)
            
            # check parsing errors
            if feed.bozo:
                logger.warning(f"Possible parsing issue with {source_name}: {feed.bozo_exception}")
                
            for entry in feed.entries:
                # Extract description and strip HTML tags if present
                description = getattr(entry, "summary", "") or getattr(entry, "description", "")
                
                # Normalize publication date
                published_str = getattr(entry, "published", "") or getattr(entry, "updated", "")
                
                articles.append({
                    "title": getattr(entry, "title", "No Title").strip(),
                    "link": getattr(entry, "link", ""),
                    "description": description.strip(),
                    "source": source_name,
                    "published_at": published_str
                })
                
            logger.info(f"Successfully scraped {len(articles)} articles from {source_name}")
        except Exception as e:
            logger.error(f"Error scraping RSS feed {source_name}: {str(e)}")
            
        return articles

    def scrape_reddit(self, subreddit_name: str = "IndiaInvestments", limit: int = 10) -> list[dict]:
        """
        Scrapes top posts from the last 24 hours of the specified subreddit.
        
        Args:
            subreddit_name: Subreddit to scrape.
            limit: Number of posts to retrieve.
        Returns:
            List of parsed post dicts.
        """
        posts = []
        if not self.reddit_client:
            logger.debug("Reddit client not initialized. Skipping Reddit fetch.")
            return posts

        logger.info(f"Scraping r/{subreddit_name} top posts from the last 24 hours...")
        try:
            subreddit = self.reddit_client.subreddit(subreddit_name)
            
            # Fetch top posts in the last 24 hours (time_filter='day')
            for post in subreddit.top(time_filter="day", limit=limit):
                # Avoid stickied/pinned announcements
                if post.stickied:
                    continue
                
                # Combine post selftext with URL if it's a link post
                description = post.selftext or ""
                if post.url and not post.is_self:
                    description = f"Link post pointing to: {post.url}. {description}"
                
                # Format creation time
                created_utc = datetime.utcfromtimestamp(post.created_utc)
                published_str = created_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
                
                posts.append({
                    "title": post.title.strip(),
                    "link": f"https://www.reddit.com{post.permalink}",
                    "description": description.strip(),
                    "source": f"Reddit: r/{subreddit_name}",
                    "published_at": published_str
                })
                
            logger.info(f"Successfully scraped {len(posts)} posts from r/{subreddit_name}")
        except Exception as e:
            logger.error(f"Error scraping Reddit r/{subreddit_name}: {str(e)}")
            
        return posts

    def scrape_all(self) -> list[dict]:
        """
        Scrapes all RSS sources and Reddit feeds, aggregates them, and removes duplicates.
        
        Returns:
            Deduplicated list of articles.
        """
        all_articles = []
        
        # 1. Scrape RSS Feeds
        for source, url in RSS_FEEDS.items():
            all_articles.extend(self.scrape_rss_feed(source, url))
            
        # 2. Scrape Reddit (if initialized)
        if self.reddit_client:
            all_articles.extend(self.scrape_reddit())
            
        # 3. Deduplicate articles by title (case-insensitive, whitespace normalized)
        seen_titles = set()
        deduped_articles = []
        
        for article in all_articles:
            normalized_title = " ".join(article["title"].lower().split())
            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                deduped_articles.append(article)
                
        logger.info(f"Aggregation complete. Total raw: {len(all_articles)}, Deduplicated: {len(deduped_articles)}")
        return deduped_articles

if __name__ == "__main__":
    print("--- News Scraper Agent Test ---")
    scraper = NewsScraper()
    results = scraper.scrape_all()
    
    print(f"\nScrape results preview (showing first 3 of {len(results)} items):")
    for idx, item in enumerate(results[:3]):
        print(f"\n[{idx + 1}] Source: {item['source']}")
        print(f"Title: {item['title']}")
        print(f"Link: {item['link']}")
        print(f"Published: {item['published_at']}")
        print(f"Description (Truncated): {item['description'][:150]}...")
