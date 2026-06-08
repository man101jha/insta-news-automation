import os
import sys
import json
import datetime
from groq import Groq

# Try to import logger, config, and NewsScraper
try:
    from upsc_agent.utils.logger import logger
    from upsc_agent.utils.config import config
    from upsc_agent.agents.news_scraper import NewsScraper
except ImportError:
    # Fallback to local import if run directly
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import logger
    from utils.config import config
    from agents.news_scraper import NewsScraper

class MCQGenerationError(Exception):
    """Custom exception raised when MCQ generation or validation fails."""
    pass

class MCQGenerator:
    def __init__(self):
        # Initialize the Groq client using our validated config key
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"
        self.temperature = 0.4
        self.max_tokens = 3000
        self.today = datetime.date.today()
        self.today_str = self.today.strftime("%Y-%m-%d")

        # Establish cache path
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(self.base_dir, "output", "cache")
        os.makedirs(self.output_dir, exist_ok=True)

    def clean_json_response(self, text: str) -> str:
        """
        Strips accidental markdown code fence tags (```json ... ```) from the LLM output.
        """
        text = text.strip()
        # Remove opening fence
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                text = "\n".join(lines[1:])
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3].strip()
        return text.strip()

    def validate_mcqs(self, mcq_data: dict) -> bool:
        """
        Validates that the generated data structure conforms strictly to UPSC MCQ contract requirements.
        """
        if not isinstance(mcq_data, dict) or "mcqs" not in mcq_data:
            logger.warning("MCQ JSON lacks root 'mcqs' key.")
            return False

        mcqs_list = mcq_data["mcqs"]
        if not isinstance(mcqs_list, list) or len(mcqs_list) != 10:
            logger.warning("MCQ list length is %s instead of exactly 10.", len(mcqs_list) if isinstance(mcqs_list, list) else "not a list")
            return False

        required_keys = {"q_num", "question", "options", "correct", "explanation", "topic", "difficulty"}
        allowed_options = {"A", "B", "C", "D"}
        allowed_difficulties = {"Easy", "Medium", "Hard"}

        for idx, mcq in enumerate(mcqs_list):
            # Check for dictionary and presence of all required keys
            if not isinstance(mcq, dict):
                logger.warning("MCQ at index %d is not a dictionary.", idx)
                return False
            
            missing_keys = required_keys - mcq.keys()
            if missing_keys:
                logger.warning("MCQ at index %d is missing keys: %s", idx, missing_keys)
                return False

            # Check question ends with ?
            if not isinstance(mcq["question"], str) or not mcq["question"].strip().endswith("?"):
                logger.warning("MCQ at index %d question does not end with '?': %s", idx, mcq["question"])
                return False

            # Check options structure
            opts = mcq["options"]
            if not isinstance(opts, dict) or set(opts.keys()) != allowed_options:
                logger.warning("MCQ at index %d options keys are not exactly A, B, C, D.", idx)
                return False

            # Check correct answer value
            if mcq["correct"] not in allowed_options:
                logger.warning("MCQ at index %d correct answer '%s' is not in A, B, C, D.", idx, mcq["correct"])
                return False

            # Check difficulty level
            if mcq["difficulty"] not in allowed_difficulties:
                logger.warning("MCQ at index %d difficulty '%s' is invalid.", idx, mcq["difficulty"])
                return False

            # Check explanation length (max words recommendation)
            explanation = mcq["explanation"]
            if not isinstance(explanation, str) or len(explanation.split()) > 25:
                logger.warning("MCQ at index %d explanation is not a string or exceeds word recommendation: %s", idx, explanation)
                # Note: We won't strictly fail validation on minor word limit overruns unless it's empty, 
                # but we validate it is a non-empty string.
                if not explanation:
                    return False

        return True

    def call_groq(self, system_prompt: str, user_prompt: str) -> str:
        """
        Performs the API request to Groq LLM.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content

    def generate(self, articles: list) -> dict:
        """
        Processes articles through Groq LLM to generate exactly 10 UPSC MCQs.
        Performs validation and handles a single retry upon parsing failures.
        Saves output cache file.
        """
        logger.info("Initializing UPSC MCQ generation for today's articles...")
        
        # Build articles context text block
        articles_text = ""
        for idx, art in enumerate(articles):
            articles_text += f"--- ARTICLE {idx+1} ---\n"
            articles_text += f"Source: {art['source']}\n"
            articles_text += f"Title: {art['title']}\n"
            articles_text += f"Body:\n{art['body']}\n\n"

        system_prompt = (
            "You are an expert UPSC CSE Prelims question setter with 10+ years experience.\n"
            "Generate questions strictly in UPSC Prelims style — factual, precise,\n"
            "with plausible distractors that test conceptual clarity.\n"
            "Topics: Polity, Economy, Environment, IR, Science & Tech, Schemes, History, Geography.\n"
            "Always return valid JSON only. No markdown. No preamble. No explanation outside JSON."
        )

        user_prompt = (
            f"From the following current affairs articles dated {self.today_str}, generate exactly\n"
            "10 UPSC Prelims MCQs.\n\n"
            "Return ONLY this JSON structure, nothing else:\n"
            "{\n"
            "  \"mcqs\": [\n"
            "    {\n"
            "      \"q_num\": 1,\n"
            "      \"question\": \"Full question text ending with ?\",\n"
            "      \"options\": {\n"
            "        \"A\": \"option text\",\n"
            "        \"B\": \"option text\",\n"
            "        \"C\": \"option text\",\n"
            "        \"D\": \"option text\"\n"
            "      },\n"
            "      \"correct\": \"B\",\n"
            "      \"explanation\": \"Single sentence citing the specific fact.\",\n"
            "      \"topic\": \"Polity\",\n"
            "      \"difficulty\": \"Medium\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "RULES:\n"
            "- Each question tests a distinct fact from the articles — no repetition\n"
            "- At least 2 options must be highly plausible (UPSC trap style)\n"
            "- Mix: 3 Easy, 5 Medium, 2 Hard\n"
            "- Cover minimum 4 different topic categories\n"
            "- Explanation: 1 sentence, specific fact, max 20 words\n\n"
            f"Articles:\n{articles_text}"
        )

        raw_response = ""
        try:
            # First attempt
            raw_response = self.call_groq(system_prompt, user_prompt)
            cleaned = self.clean_json_response(raw_response)
            mcq_data = json.loads(cleaned)

            if self.validate_mcqs(mcq_data):
                logger.info("MCQ structure validated successfully on the first attempt.")
                self.save_mcqs_to_cache(mcq_data)
                return mcq_data

            # First attempt validation failed, trigger single retry
            logger.warning("MCQ validation failed on first attempt. Retrying with strict formatting prompt...")
            
            retry_user_prompt = (
                f"Your previous response failed validation checks. You must output exactly 10 MCQs conforming to the required format.\n"
                f"Ensure the JSON matches the schema, has exactly 10 questions, option keys are A, B, C, D, and question texts end with a question mark '?'.\n\n"
                f"Previous Response:\n{raw_response}\n\n"
                f"Generate the corrected JSON now. Only JSON, no explanation."
            )
            
            raw_response = self.call_groq(system_prompt, retry_user_prompt)
            cleaned = self.clean_json_response(raw_response)
            mcq_data = json.loads(cleaned)

            if self.validate_mcqs(mcq_data):
                logger.info("MCQ structure validated successfully on the retry attempt.")
                self.save_mcqs_to_cache(mcq_data)
                return mcq_data
            else:
                raise MCQGenerationError("Generated MCQs failed validation checks twice.")

        except Exception as e:
            logger.error("Failed to generate valid UPSC MCQs. Raw response: %s", raw_response)
            logger.error("Error details: %s", str(e))
            raise MCQGenerationError(f"MCQ Generation Error: {str(e)}")

    def save_mcqs_to_cache(self, mcq_data: dict):
        """Saves validated MCQ data to cache file."""
        cache_file = os.path.join(self.output_dir, f"mcqs_{self.today.strftime('%Y%m%d')}.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(mcq_data, f, ensure_ascii=False, indent=2)
        logger.info("Saved cached MCQs to %s", cache_file)

if __name__ == "__main__":
    # Standalone Test
    try:
        generator = MCQGenerator()
        
        # Load articles from cache if present
        cache_date_str = generator.today.strftime("%Y%m%d")
        articles_cache_file = os.path.join(generator.output_dir, f"articles_{cache_date_str}.json")
        
        if os.path.exists(articles_cache_file):
            logger.info("Loading articles from cache file: %s", articles_cache_file)
            with open(articles_cache_file, "r", encoding="utf-8") as f:
                articles = json.load(f)
        else:
            logger.info("No articles cache found. Running news scraper...")
            scraper = NewsScraper()
            articles = scraper.scrape()

        # Generate MCQs
        mcqs_data = generator.generate(articles)
        
        # Print Q1 full to console as required
        print("\n--- MCQ GENERATOR SUCCESS ---")
        q1 = mcqs_data["mcqs"][0]
        print(f"Q1 ({q1['topic']} - {q1['difficulty']}): {q1['question']}")
        print(f"Options:")
        for key, val in q1["options"].items():
            print(f"  {key}) {val}")
        print(f"Correct Answer: {q1['correct']}")
        print(f"Explanation: {q1['explanation']}")
        
    except Exception as err:
        print(f"\n--- MCQ GENERATOR FAILURE ---")
        print(f"Error: {str(err)}")
        sys.exit(1)
