import json
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from utils.config import Config
from utils.logger import get_logger

# Initialize module logger
logger = get_logger("carousel_writer")

class CarouselWriter:
    """
    Agent responsible for transforming top financial news stories into formatted,
    high-impact copywriting for a 7-slide Instagram carousel.
    """
    
    def __init__(self):
        """
        Initializes the Groq LLM client using LangChain.
        
        Free Tier Limits: Groq's llama-3.3-70b-versatile model has free tier limits:
        - 30 Requests Per Minute (RPM)
        - 14,400 Requests Per Day (RPD)
        We use exactly 1 API request to generate the entire copy list.
        """
        if not Config.GROQ_API_KEY or "your_" in Config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured or contains placeholder values in .env")
            
        # Initialize Groq Chat model via LangChain
        self.llm = ChatGroq(
            groq_api_key=Config.GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,  # Low temperature for precise formatting, but slightly higher for creative/punchy copy
            timeout=30.0
        )

    def write_carousel_copy(self, top_stories: list[dict]) -> list[dict]:
        """
        Generates copywriting for a 7-slide carousel based on the top 5 news stories.
        
        Args:
            top_stories: List of 5 selected news story dictionaries.
        Returns:
            A list of 7 slide dictionaries matching the design format:
            [ { "slide_num": 1, "headline": "...", "body": "...", "type": "cover|news|cta" }, ... ]
        """
        if len(top_stories) < 5:
            logger.warning(f"Expected at least 5 stories, got {len(top_stories)}. Writing copy anyway...")
            
        logger.info("Generating carousel copywriting slide deck copy via Groq LLM...")
        
        # Serialize top stories for the prompt
        stories_input = json.dumps(top_stories, indent=2)
        
        # Construct copy generation system/human instructions
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert financial copywriter and Instagram social media manager.\n"
                "Your task is to convert 5 financial news stories into a high-converting, premium-looking 7-slide Instagram carousel.\n\n"
                 "Slide Layout Guidelines:\n"
                 "1. SLIDE 1 (Cover): Type 'cover'. Tag must be 'COVER'. Headline must be exactly '5 Finance Headlines Every Indian Should Know Today'. The body must be exactly 'SWIPE TO SEE SHORT, EASY DAILY UPDATES THAT MATTER TO YOUR MONEY'. Stat fields must be empty strings.\n"
                 "2. SLIDES 2-6 (News Slides): Type 'news'. Each slide represents one of the 5 stories in order.\n"
                 "   - Tag: A short 1-2 word uppercase category matching the topic (e.g. 'MARKETS', 'REAL ESTATE', 'BANKING', 'WEALTH CREATION').\n"
                 "   - Headline: A very punchy, short, serif-style title summarizing the story (maximum 6-8 words). Example: '$1 Billion Green Housing Push' or 'Markets Recover 700 Points'.\n"
                 "   - Body: A detailed 6-8 line paragraph of high-impact sans-serif body text (approximately 80-100 words total). Explain clearly what happened, why it happened, and its direct actionability/consequences for a retail investor's savings, mutual funds, or stock portfolio. Provide deep, high-quality, dense information to fill the layout space beautifully.\n"
                 "   - stat1 & stat1_label: The first key metric from the news (e.g. '+700 pts' for stat1, 'Sensex' for stat1_label; or '12%' for stat1, 'Realistic' for stat1_label).\n"
                 "   - stat2 & stat2_label: The second key metric or contextual label from the news (e.g. '+0.9%' for stat2, 'Nifty' for stat2_label; or '41%' for stat2, 'Upside' for stat2_label).\n"
                 "3. SLIDE 7 (CTA): Type 'cta'. Tag must be 'FOLLOW'. Headline must be exactly 'Stay Money Smart, Every Day'. The body must be exactly 'Follow for daily finance news & tips'. Stat fields must be empty strings.\n\n"
                 "Constraints:\n"
                 "- Output EXACTLY 7 items in the JSON array (slide_num 1 to 7).\n"
                 "- Ensure all string values are on a single line. Do not output literal newline/carriage return characters inside the JSON string values (if you need a newline, use the escaped '\\\\n' string character instead).\n"
                 "- Return ONLY raw JSON, with no markdown code blocks or introduction/conclusion text.\n\n"
                 "JSON format:\n"
                 "[\n"
                 "  {{\n"
                 "    \"slide_num\": 1,\n"
                 "    \"tag\": \"COVER\",\n"
                 "    \"headline\": \"5 Finance Headlines Every Indian Should Know Today\",\n"
                 "    \"body\": \"SWIPE TO SEE SHORT, EASY UPDATES THAT MATTER TO YOUR MONEY\",\n"
                 "    \"type\": \"cover\",\n"
                 "    \"stat1\": \"\",\n"
                 "    \"stat1_label\": \"\",\n"
                 "    \"stat2\": \"\",\n"
                 "    \"stat2_label\": \"\"\n"
                 "  }},\n"
                 "  {{\n"
                 "    \"slide_num\": 2,\n"
                 "    \"tag\": \"MARKETS\",\n"
                 "    \"headline\": \"Short Serif Title\",\n"
                 "    \"body\": \"Detailed 3-4 line paragraph detailing the news and what action the retail investor should take with their money.\",\n"
                 "    \"type\": \"news\",\n"
                 "    \"stat1\": \"+700 pts\",\n"
                 "    \"stat1_label\": \"Sensex\",\n"
                 "    \"stat2\": \"+0.9%\",\n"
                 "    \"stat2_label\": \"Nifty\"\n"
                 "  }},\n"
                 "  ...\n"
                 "  {{\n"
                 "    \"slide_num\": 7,\n"
                 "    \"tag\": \"FOLLOW\",\n"
                 "    \"headline\": \"Stay Money Smart, Every Day\",\n"
                 "    \"body\": \"Follow for quick finance news & tips\",\n"
                 "    \"type\": \"cta\",\n"
                 "    \"stat1\": \"\",\n"
                 "    \"stat1_label\": \"\",\n"
                 "    \"stat2\": \"\",\n"
                 "    \"stat2_label\": \"\"\n"
                 "  }}\n"
                 "]"
            )),
            ("human", "Here are the top 5 filtered finance stories:\n\n{stories}")
        ])
        
        try:
            # Generate LLM response
            chain = prompt | self.llm
            response = chain.invoke({"stories": stories_input})
            
            response_content = response.content.strip()
            
            # Clean up markdown code fences if present
            if response_content.startswith("```"):
                response_content = re.sub(r"^```(?:json)?\n", "", response_content)
                response_content = re.sub(r"\n```$", "", response_content)
            response_content = response_content.strip()
            
            # Parse response as JSON using strict=False to tolerate literal control characters (like unescaped newlines)
            slides = json.loads(response_content, strict=False)
            
            # Verify the list length
            if not isinstance(slides, list) or len(slides) != 7:
                raise ValueError(f"LLM did not return exactly 7 slides. Returned count: {len(slides) if isinstance(slides, list) else 'not a list'}")
                
            logger.info("Successfully generated copywriting for all 7 slides.")
            return slides
            
        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse copywriting JSON: {str(jde)}")
            logger.debug(f"Raw response content: {response.content}")
            return []
        except Exception as e:
            logger.error(f"Error during copywriting generation: {str(e)}")
            return []

if __name__ == "__main__":
    from agents.news_scraper import NewsScraper
    from agents.filter_agent import FilterAgent
    
    print("--- Carousel Copywriter Agent Test ---")
    
    # 1. Scrape articles
    scraper = NewsScraper()
    raw_articles = scraper.scrape_all()
    
    if raw_articles:
        # 2. Filter top 5
        filter_agent = FilterAgent()
        top_stories = filter_agent.filter_stories(raw_articles)
        
        if top_stories:
            # 3. Write copy
            writer = CarouselWriter()
            slides = writer.write_carousel_copy(top_stories)
            
            print("\n--- GENERATED SLIDE COPY DECK ---")
            for slide in slides:
                print(f"\n[Slide {slide.get('slide_num')}] ({slide.get('type').upper()})")
                print(f"HEADLINE: {slide.get('headline')}")
                print(f"BODY: {slide.get('body')}")
        else:
            print("No top stories filtered.")
    else:
        print("No articles scraped.")
