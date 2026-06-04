import json
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from utils.config import Config
from utils.logger import get_logger

# Initialize module logger
logger = get_logger("filter_agent")

class FilterAgent:
    """
    Agent responsible for analyzing and scoring scraped news articles.
    Selects the top 5 most relevant and actionable finance stories for Indian retail investors.
    """
    
    def __init__(self):
        """
        Initializes the Groq LLM client using LangChain.
        
        Free Tier Limits: Groq's llama-3.3-70b-versatile model has free tier limits:
        - 30 Requests Per Minute (RPM)
        - 14,400 Requests Per Day (RPD)
        - 40,000 Tokens Per Minute (TPM)
        We package all articles into a single structured prompt to use exactly 1 API request.
        """
        if not Config.GROQ_API_KEY or "your_" in Config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured or contains placeholder values in .env")
            
        # Initialize LangChain Groq chat client
        self.llm = ChatGroq(
            groq_api_key=Config.GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1,  # Low temperature for highly consistent, deterministic scoring
            timeout=30.0
        )

    def filter_stories(self, articles: list[dict]) -> list[dict]:
        """
        Sends the list of scraped articles to Groq to select and summarize the top 5.
        
        Args:
            articles: List of scraped article dictionaries.
        Returns:
            List of 5 highly scored news dictionaries.
        """
        if not articles:
            logger.warning("No articles provided for filtering.")
            return []
            
        # Slicing the input articles to the top 20 to avoid exceeding the Groq free tier TPM limit (12,000 tokens)
        max_input_articles = 20
        logger.info(f"Filtering top {min(len(articles), max_input_articles)} out of {len(articles)} articles using Groq LLM...")
        articles_to_evaluate = articles[:max_input_articles]
        
        # Format the scraped articles into a clean string for the prompt
        formatted_articles = []
        for idx, art in enumerate(articles_to_evaluate):
            formatted_articles.append(
                f"ID: {idx}\n"
                f"Source: {art['source']}\n"
                f"Title: {art['title']}\n"
                f"Description: {art['description']}\n"
                f"Link: {art['link']}\n"
                f"-----------------------------------"
            )
        articles_text = "\n".join(formatted_articles)
        
        # Construct the system and human prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert Indian retail financial advisor and news editor.\n"
                "Your task is to analyze financial news articles and pick the top 5 most critical stories for Indian retail investors.\n\n"
                "Scoring Criteria:\n"
                "1. Relevance to Indian Retail Investor (1-10): How much does this matter to an individual investing in Indian stocks, mutual funds, gold, real estate, or local savings?\n"
                "2. Actionability (1-10): Can the retail investor take action? Does it directly affect their tax, portfolio choice, loan rates, or retirement planning?\n"
                "3. Freshness & Local Angle: Prioritize news from the last 24h. Avoid global macro-only news unless there is a direct, substantial impact on Indian markets.\n\n"
                "Select exactly 5 stories, score them, and provide a 2-line simple summary explaining the impact on their money.\n"
                "You MUST respond ONLY with a valid JSON array of objects. Do not include markdown formatting like ```json ... ``` or any introductory/concluding text. Just raw JSON.\n\n"
                "JSON format:\n"
                "[\n"
                "  {{\n"
                "    \"title\": \"Original Article Title\",\n"
                "    \"link\": \"Original Article Link\",\n"
                "    \"source\": \"Original Source\",\n"
                "    \"score\": 9.5,\n"
                "    \"retail_impact_summary\": \"2-line simple summary of what this means for the investor's money.\"\n"
                "  }}\n"
                "]"
            )),
            ("human", "Here are the articles to evaluate:\n\n{articles}")
        ])
        
        try:
            # Generate LLM response
            chain = prompt | self.llm
            response = chain.invoke({"articles": articles_text})
            
            response_content = response.content.strip()
            
            # Clean up potential markdown formatting wrapping the JSON
            if response_content.startswith("```"):
                response_content = re.sub(r"^```(?:json)?\n", "", response_content)
                response_content = re.sub(r"\n```$", "", response_content)
            response_content = response_content.strip()
            
            # Parse response as JSON
            selected_stories = json.loads(response_content)
            
            # Basic validation of length
            if not isinstance(selected_stories, list):
                raise ValueError("LLM did not return a JSON list.")
                
            logger.info(f"Successfully filtered and retrieved top {len(selected_stories)} stories.")
            return selected_stories
            
        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse JSON response from LLM: {str(jde)}")
            logger.debug(f"Raw response was: {response.content}")
            return []
        except Exception as e:
            logger.error(f"Error during article filtering: {str(e)}")
            return []

if __name__ == "__main__":
    from agents.news_scraper import NewsScraper
    
    print("--- Groq Filter Agent Test ---")
    
    # 1. Scrape articles
    scraper = NewsScraper()
    raw_articles = scraper.scrape_all()
    
    # 2. Filter top 5 using Groq
    if raw_articles:
        try:
            filter_agent = FilterAgent()
            top_stories = filter_agent.filter_stories(raw_articles)
            
            print("\n--- TOP 5 STORIES FOR RETAIL INVESTORS ---")
            for idx, story in enumerate(top_stories):
                print(f"\n#{idx+1} [Score: {story.get('score')}] - {story.get('title')}")
                print(f"Source: {story.get('source')}")
                print(f"Impact: {story.get('retail_impact_summary')}")
                print(f"Link: {story.get('link')}")
        except Exception as err:
            print(f"Initialization/Execution Error: {str(err)}")
    else:
        print("No articles found to filter.")
