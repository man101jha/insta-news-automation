import os
import sys
import json
import datetime
from playwright.sync_api import sync_playwright

# Try to import logger and config
try:
    from upsc_agent.utils.logger import logger
    from upsc_agent.utils.config import config
except ImportError:
    # Fallback to local import if run directly
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import logger
    from utils.config import config

class SlideBuilder:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.html_dir = os.path.join(self.base_dir, "output", "html")
        self.slides_dir = os.path.join(self.base_dir, "output", "slides")
        
        # Ensure directories exist
        os.makedirs(self.html_dir, exist_ok=True)
        os.makedirs(self.slides_dir, exist_ok=True)

    def get_common_head_tags(self) -> str:
        """Returns standard HTML head tags including styling and web fonts."""
        return """
        <meta charset="utf-8">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,400&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-dark: #0f1923;
                --gold: #c8a96e;
                --gold-light: rgba(200, 169, 110, 0.08);
                --gold-border: rgba(200, 169, 110, 0.22);
                --gold-grid: rgba(200, 169, 110, 0.045);
                --white: rgba(255, 255, 255, 0.95);
                --text-muted: rgba(255, 255, 255, 0.7);
                --text-super-muted: rgba(255, 255, 255, 0.5);
                --green: #4ade80;
                --green-bg: rgba(34, 168, 85, 0.15);
                --yellow: #facc15;
                --yellow-bg: rgba(234, 179, 8, 0.15);
                --red: #f87171;
                --red-bg: rgba(239, 68, 68, 0.15);
            }
            
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            body {
                width: 1080px;
                height: 1080px;
                overflow: hidden;
                background-color: var(--bg-dark);
                font-family: 'Inter', sans-serif;
                color: var(--white);
                position: relative;
            }

            .grid-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: 
                    linear-gradient(to right, var(--gold-grid) 1px, transparent 1px),
                    linear-gradient(to bottom, var(--gold-grid) 1px, transparent 1px);
                background-size: 48px 48px;
                pointer-events: none;
                z-index: 1;
            }

            .gold-bar-top {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background-color: var(--gold);
                z-index: 10;
            }

            .gold-bar-bottom {
                position: absolute;
                bottom: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background-color: var(--gold);
                z-index: 10;
            }

            .container {
                position: relative;
                width: 100%;
                height: 100%;
                padding: 70px 80px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                z-index: 5;
            }

            .pill {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border-radius: 99px;
                font-weight: 700;
                letter-spacing: 0.12em;
                text-transform: uppercase;
            }

            .pill-gold-outline {
                border: 1px solid var(--gold-border);
                background: transparent;
                color: var(--gold);
            }

            .pill-gold-solid {
                background: var(--gold);
                color: var(--bg-dark);
            }

            .circle-arrow {
                border-radius: 50%;
                border: 1.5px solid var(--gold-border);
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--gold);
                font-weight: bold;
            }

            .footer-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: auto;
            }

            .footer-text {
                font-size: 13px;
                color: var(--text-muted);
                letter-spacing: 0.1em;
                text-transform: uppercase;
            }
        </style>
        """

    def generate_slide_1_html(self, data: dict) -> str:
        """Generates Slide 1 (Cover) HTML with high readability sizing."""
        topics = data.get("topics", [])
        topic_pills = "".join([f'<span class="pill pill-gold-outline" style="font-size: 14px; padding: 8px 20px; margin-right: 12px; margin-bottom: 12px;">{t}</span>' for t in topics[:4]])
        
        cover_image = "https://images.unsplash.com/photo-1628155930542-3c7a64e2c833?auto=format&fit=crop&w=1080&h=1080&q=80"
        
        return f"""<!DOCTYPE html>
        <html>
        <head>
            {self.get_common_head_tags()}
            <style>
                .cover-bg {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-image: url('{cover_image}');
                    background-size: cover;
                    background-position: center;
                    z-index: 0;
                }}
                .cover-overlay {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(to top, rgba(0, 0, 0, 0.95) 0%, rgba(0, 0, 0, 0.4) 60%, rgba(10, 15, 30, 0.6) 100%);
                    z-index: 2;
                }}
                .header-wrapper {{
                    text-align: center;
                    margin-top: 25px;
                }}
                .cover-content {{
                    margin-top: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 24px;
                }}
                .headline {{
                    font-family: 'Playfair Display', serif;
                    font-size: 56px;
                    font-weight: 700;
                    line-height: 1.2;
                    color: var(--white);
                    text-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
                }}
                .subheadline {{
                    font-size: 20px;
                    color: var(--gold);
                    font-weight: 500;
                    letter-spacing: 0.05em;
                }}
                .date-chip {{
                    font-size: 16px;
                    color: rgba(255, 255, 255, 0.85);
                    font-weight: 600;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                }}
                .swipe-hint {{
                    font-size: 16px;
                    color: var(--text-muted);
                    font-weight: 500;
                    letter-spacing: 0.05em;
                }}
            </style>
        </head>
        <body>
            <div class="cover-bg"></div>
            <div class="cover-overlay"></div>
            <div class="grid-overlay"></div>
            <div class="gold-bar-top"></div>
            <div class="gold-bar-bottom"></div>
            
            <div class="container">
                <div class="header-wrapper">
                    <span class="pill pill-gold-solid" style="font-size: 16px; padding: 8px 24px;">UPSC CSE · PRELIMS 2025</span>
                </div>

                <div class="cover-content">
                    <div class="date-chip">{data.get("day", "")}, {data.get("date", "")}</div>
                    <h1 class="headline">{data.get("hook", "Daily UPSC Practice")}</h1>
                    <div class="subheadline">{data.get("subheadline", "Based on today's The Hindu + Indian Express")}</div>
                    
                    <div style="display: flex; flex-wrap: wrap; margin-top: 5px;">
                        {topic_pills}
                    </div>

                    <div class="footer-row" style="margin-top: 30px;">
                        <span class="swipe-hint">Swipe → Attempt all 10 → Answers in caption</span>
                        <div class="circle-arrow" style="width: 56px; height: 56px; font-size: 22px;">→</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def generate_slide_mcq_html(self, mcq1: dict, mcq2: dict, slide_num: int, date_str: str) -> str:
        """Generates an MCQ Slide with large fonts, stacked options list, and no pre-highlighted correct answers."""
        topics = list(set([mcq1.get("topic", "General"), mcq2.get("topic", "General")]))
        topic_header = " · ".join(topics).upper()
        
        q_start = (slide_num - 2) * 2 + 1
        q_end = q_start + 1
        q_range = f"Q{q_start}–{q_end}"

        def build_mcq_block(q: dict) -> str:
            diff = q.get("difficulty", "Medium")
            diff_class = "diff-medium"
            if diff == "Easy":
                diff_class = "diff-easy"
            elif diff == "Hard":
                diff_class = "diff-hard"

            # Render option list in vertical cards
            options_html = ""
            for key in ["A", "B", "C", "D"]:
                opt_val = q.get("options", {}).get(key, "")
                options_html += f'<div class="option">{key}) {opt_val}</div>'

            return f"""
            <div class="mcq-block">
                <div class="mcq-header">
                    <span class="q-number">Q{q.get("q_num", 1)}.</span>
                    <span class="diff-badge {diff_class}">{diff}</span>
                </div>
                <div class="question-text">{q.get("question", "")}</div>
                <div class="options-list">
                    {options_html}
                </div>
            </div>
            """

        block1 = build_mcq_block(mcq1)
        block2 = build_mcq_block(mcq2)

        return f"""<!DOCTYPE html>
        <html>
        <head>
            {self.get_common_head_tags()}
            <style>
                .mcq-slide-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }}
                .topic-header-pill {{
                    background: var(--gold-light);
                    color: var(--gold);
                    border: 1.5px solid var(--gold-border);
                    padding: 10px 24px;
                    font-size: 14px;
                    font-weight: 700;
                    letter-spacing: 0.1em;
                    border-radius: 99px;
                    text-transform: uppercase;
                }}
                .q-range-circle {{
                    width: 52px;
                    height: 52px;
                    border-radius: 50%;
                    border: 1.5px solid var(--gold-border);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                    font-weight: 700;
                    color: var(--gold);
                }}
                .mcq-block {{
                    background-color: var(--gold-light);
                    border: 1px solid var(--gold-border);
                    border-radius: 12px;
                    padding: 24px 28px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }}
                .mcq-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .q-number {{
                    font-size: 22px;
                    font-weight: 700;
                    color: var(--gold);
                }}
                .diff-badge {{
                    font-size: 12px;
                    font-weight: 700;
                    padding: 5px 12px;
                    border-radius: 4px;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                .diff-easy {{
                    background: var(--green-bg);
                    color: var(--green);
                }}
                .diff-medium {{
                    background: var(--yellow-bg);
                    color: var(--yellow);
                }}
                .diff-hard {{
                    background: var(--red-bg);
                    color: var(--red);
                }}
                .question-text {{
                    font-size: 22px;
                    font-weight: 500;
                    line-height: 1.45;
                    color: rgba(255, 255, 255, 0.95);
                }}
                .options-list {{
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    margin-top: 4px;
                }}
                .option {{
                    font-size: 18px;
                    color: rgba(255, 255, 255, 0.85);
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(200, 169, 110, 0.15);
                    padding: 8px 16px;
                    border-radius: 6px;
                    line-height: 1.35;
                }}
                .slide-divider {{
                    background: linear-gradient(90deg, transparent, rgba(200, 169, 110, 0.22), transparent);
                    height: 1.5px;
                    margin: 12px 0;
                    width: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="grid-overlay"></div>
            <div class="gold-bar-top"></div>
            <div class="gold-bar-bottom"></div>
            
            <div class="container">
                <div class="mcq-slide-header">
                    <span class="topic-header-pill">{topic_header}</span>
                    <span class="q-range-circle">{q_range}</span>
                </div>

                {block1}
                <div class="slide-divider"></div>
                {block2}

                <div class="footer-row">
                    <span class="footer-text">The Hindu · Indian Express · {date_str}</span>
                    <div class="circle-arrow" style="width: 44px; height: 44px; font-size: 18px;">→</div>
                </div>
            </div>
        </body>
        </html>
        """

    def generate_slide_7_html(self, data: dict) -> str:
        """Generates Slide 7 (Closing/CTA) HTML with high readability sizing."""
        return f"""<!DOCTYPE html>
        <html>
        <head>
            {self.get_common_head_tags()}
            <style>
                .closing-wrapper {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    height: 100%;
                    gap: 36px;
                    margin-top: 20px;
                }}
                .quote-block {{
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    max-width: 85%;
                }}
                .quote-text {{
                    font-family: 'Playfair Display', serif;
                    font-size: 32px;
                    font-weight: 600;
                    line-height: 1.4;
                    color: var(--white);
                }}
                .quote-attribution {{
                    font-size: 16px;
                    color: var(--gold);
                    font-weight: 600;
                    letter-spacing: 0.05em;
                }}
                .divider-gold-gradient {{
                    background: linear-gradient(90deg, transparent, var(--gold), transparent);
                    height: 1.5px;
                    width: 300px;
                }}
                .challenge-box {{
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }}
                .challenge-title {{
                    font-size: 22px;
                    font-weight: 700;
                    color: rgba(255,255,255,0.9);
                }}
                .challenge-scores {{
                    font-size: 18px;
                    font-weight: 600;
                }}
                .social-row {{
                    display: flex;
                    gap: 16px;
                    justify-content: center;
                    margin-top: 15px;
                }}
                .social-pill {{
                    border: 1.5px solid var(--gold-border);
                    background: transparent;
                    color: var(--gold);
                    padding: 8px 18px;
                    font-size: 14px;
                    border-radius: 99px;
                    font-weight: 600;
                }}
                .handle-text {{
                    font-size: 18px;
                    color: var(--text-muted);
                    font-weight: 600;
                    letter-spacing: 0.05em;
                }}
            </style>
        </head>
        <body>
            <div class="grid-overlay"></div>
            <div class="gold-bar-top"></div>
            <div class="gold-bar-bottom"></div>
            
            <div class="container">
                <div style="text-align: center; margin-top: 20px;">
                    <span class="pill pill-gold-solid" style="font-size: 16px; padding: 8px 24px;">UPSC · Daily Practice</span>
                </div>

                <div class="closing-wrapper">
                    <div class="quote-block">
                        <p class="quote-text">"{data.get("quote", "Consistency beats intensity.")}"</p>
                        <span class="quote-attribution">— Daily UPSC Prep</span>
                    </div>

                    <div class="divider-gold-gradient"></div>

                    <div class="challenge-box">
                        <span class="challenge-title">Comment your score below!</span>
                        <span class="challenge-scores">0–3 🔴 &middot; 4–6 🟡 &middot; 7–10 🟢</span>
                    </div>

                    <div class="social-row">
                        <div class="social-pill">👍 Like if helpful</div>
                        <div class="social-pill">🔔 Follow for daily MCQs</div>
                        <div class="social-pill">📤 Share with a friend</div>
                    </div>
                </div>

                <div class="footer-row" style="justify-content: center; position: relative; margin-top: 30px;">
                    <span class="handle-text" style="position: absolute; bottom: 0;">{data.get("ig_handle", "@yourupscpage")}</span>
                    <div class="circle-arrow" style="margin-left: auto; width: 44px; height: 44px; font-size: 16px;">↓</div>
                </div>
            </div>
        </body>
        </html>
        """

    def generate_combined_preview_html(self) -> str:
        """Generates a combined layout containing all 7 slides in a grid for local review."""
        return """<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>UPSC Daily MCQ Carousel Preview</title>
            <style>
                body {
                    background-color: #1a1a24;
                    font-family: 'Inter', sans-serif;
                    padding: 40px;
                    color: #fff;
                }
                h1 {
                    text-align: center;
                    margin-bottom: 40px;
                    font-weight: 300;
                    color: #c8a96e;
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 30px;
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .slide-preview {
                    border: 2px solid #333;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                    position: relative;
                }
                iframe {
                    width: 1080px;
                    height: 1080px;
                    border: none;
                    transform: scale(0.333333);
                    transform-origin: top left;
                }
                .iframe-container {
                    width: 360px;
                    height: 360px;
                    overflow: hidden;
                    background-color: #0f1923;
                }
                .slide-label {
                    background: #252538;
                    padding: 10px;
                    text-align: center;
                    font-size: 12px;
                    font-weight: 600;
                    color: #c8a96e;
                    border-top: 1px solid #333;
                }
            </style>
        </head>
        <body>
            <h1>UPSC Daily MCQ Carousel Preview</h1>
            <div class="grid">
                <div class="slide-preview">
                    <div class="iframe-container"><iframe src="slide_01.html"></iframe></div>
                    <div class="slide-label">Slide 1: Cover Page</div>
                </div>
                <div class="slide-preview">
                    <div class="iframe-container"><iframe src="slide_02.html"></iframe></div>
                    <div class="slide-label">Slide 2: Q1 & Q2</div>
                </div>
                <div class="slide-preview">
                    <div class="iframe-container"><iframe src="slide_03.html"></iframe></div>
                    <div class="slide-label">Slide 3: Q3 & Q4</div>
                </div>
                <div class="slide-preview">
                    <div class="iframe-container"><iframe src="slide_04.html"></iframe></div>
                    <div class="slide-label">Slide 4: Q5 & Q6</div>
                </div>
                <div class="slide-preview">
                    <div class="iframe-container"><iframe src="slide_05.html"></iframe></div>
                    <div class="slide-label">Slide 5: Q7 & Q8</div>
                </div>
                <div class="slide-preview">
                    <div class="iframe-container"><iframe src="slide_06.html"></iframe></div>
                    <div class="slide-label">Slide 6: Q9 & Q10</div>
                </div>
                <div class="slide-preview">
                    <div class="iframe-container"><iframe src="slide_07.html"></iframe></div>
                    <div class="slide-label">Slide 7: Closing / CTA</div>
                </div>
            </div>
        </body>
        </html>
        """

    def render(self, data: dict) -> list:
        """
        Processes standard data payload, writes HTMLs to output/html/
        and uses Playwright to capture PNG screenshots to output/slides/.
        Returns list of 7 PNG absolute file paths.
        """
        logger.info("Starting slide generation and rendering...")
        
        # Step 1: Write all standalone HTMLs
        html_files = {}
        
        # Cover slide
        html_files[1] = self.generate_slide_1_html(data)
        
        # MCQ slides
        mcqs = data.get("mcqs", [])
        if len(mcqs) < 10:
            raise ValueError(f"Insufficient MCQs: expected 10, got {len(mcqs)}.")
            
        for s in range(2, 7):
            idx1 = (s - 2) * 2
            idx2 = idx1 + 1
            html_files[s] = self.generate_slide_mcq_html(
                mcq1=mcqs[idx1], 
                mcq2=mcqs[idx2], 
                slide_num=s, 
                date_str=data.get("date", "")
            )
            
        # Closing slide
        html_files[7] = self.generate_slide_7_html(data)
        
        # Save HTML files to disk
        saved_paths = []
        for slide_num, html_content in html_files.items():
            path = os.path.join(self.html_dir, f"slide_0{slide_num}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html_content)
            saved_paths.append(path)
            
        # Combined preview HTML
        preview_path = os.path.join(self.html_dir, "combined_preview.html")
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(self.generate_combined_preview_html())
            
        logger.info("Saved 7 HTML files and combined preview to output/html/")

        # Step 2: Playwright Screenshot captures
        logger.info("Launching Playwright to capture slide screenshots...")
        png_paths = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_viewport_size({"width": 1080, "height": 1080})
            
            for s in range(1, 8):
                html_path = os.path.join(self.html_dir, f"slide_0{s}.html")
                file_url = f"file:///{html_path.replace(os.sep, '/')}"
                
                # Navigate and wait for assets/fonts to load
                page.goto(file_url)
                page.wait_for_load_state("networkidle")
                
                # Add a micro sleep to guarantee font rendering settles down
                page.wait_for_timeout(300)
                
                png_path = os.path.join(self.slides_dir, f"slide_0{s}.png")
                page.screenshot(path=png_path, type="png")
                png_paths.append(png_path)
                logger.info("Captured screenshot for Slide %d: %s", s, png_path)
                
            browser.close()
            
        logger.info("Completed rendering all 7 slides to PNG formats.")
        return png_paths

if __name__ == "__main__":
    # Test script standalone execution using mock data
    logger.info("Running SlideBuilder test with mock data...")
    mock_data = {
        "date": "08 Jun 2026",
        "day": "Monday",
        "hook": "Start Your Week Strong",
        "subheadline": "Based on today's The Hindu + Indian Express",
        "topics": ["Polity", "Environment", "IR", "Schemes"],
        "mcqs": [
            {
                "q_num": i+1,
                "question": f"Which constitutional body recently recommended linking MGNREGS wages to the Consumer Price Index for Agricultural Labourers (CPI-AL)? (Test question {i+1})",
                "options": {
                    "A": "Finance Commission",
                    "B": "NITI Aayog",
                    "C": "Planning Commission",
                    "D": "Labour Ministry"
                },
                "correct": "B",
                "explanation": f"NITI Aayog's report recommended CPI-AL linked revision of MGNREGS wages.",
                "topic": "Polity" if i % 2 == 0 else "Environment",
                "difficulty": "Medium" if i % 3 == 0 else ("Easy" if i % 3 == 1 else "Hard")
            } for i in range(10)
        ],
        "quote": "The UPSC exam is not about studying more. It's about studying smarter — every single day.",
        "ig_handle": "@upsc_daily_practice"
    }

    try:
        builder = SlideBuilder()
        pngs = builder.render(mock_data)
        print("\n--- SLIDE BUILDER SUCCESS ---")
        print("Generated Slide PNGs:")
        for path in pngs:
            print(f" - {path}")
        print(f"\nPreview HTML: {os.path.join(builder.html_dir, 'combined_preview.html')}")
    except Exception as err:
        print(f"\n--- SLIDE BUILDER FAILURE ---")
        print(f"Error: {str(err)}")
        sys.exit(1)
