BYTE_BRAIN AI — Stock Intelligence Platform

"NOTE: This project was developed collaboratively during a hackathon.
Initial development was done directly in VS Code by the team
Code iterations, UI design, and backend logic were built locally
GitHub was used primarily to upload the final working version
Version control was minimal and focused on submission readiness."

BYTE_BRAIN AI is an advanced stock intelligence platform that combines real-time market data, AI-driven predictions, and multi-layer verification to provide actionable insights for traders and investors.

The platform integrates technical analysis, pattern recognition, and AI reasoning to deliver structured predictions, supported by an additional AI verification layer for improved reliability.

🚀 Features
Real-time stock data visualization with interactive charts
AI-powered stock trend prediction
Dual-layer AI validation system (Prediction + Verification)
Pre-market top performers analysis
Integrated financial data (Stocks, IPOs, Mutual Funds)
Live financial news and streaming integration
AI-generated summaries with optional text-to-speech

🧠 AI Architecture
The system uses a multi-stage AI pipeline:
Stock Analysis AI
Processes market data and technical indicators
Detects patterns (bullish, bearish, neutral)
Generates predictions (trend, levels, confidence)
Verification AI
Reads the prediction output
Cross-validates reasoning and indicators
Ensures logical consistency before displaying results

This layered approach improves trust and reduces false signals.

🛠️ Tech Stack
Frontend: HTML, CSS, JavaScript, Chart.js
Backend: Python, FastAPI
AI Providers: Groq (recommended), Gemini, Anthropic
Data Sources: Yahoo Finance, AMFI
TTS: Microsoft Edge TTS (free, no API key required)

⚙️ Setup Instructions
1. Clone the Repository
git clone https://github.com/your-repo/byte-brain-ai.git
cd byte-brain-ai
2. Install Dependencies
pip install fastapi uvicorn requests yt-dlp edge-tts
3. Get Groq API Key (Recommended)
Go to: https://console.groq.com/keys
Create a free account
Generate an API key
4. Add API Key
Option A: Environment Variable
Windows:
set GROQ_API_KEY=your_api_key_here
Mac/Linux:
export GROQ_API_KEY=your_api_key_here
Option B: Pass in Request (Advanced)
You can also send the API key directly in API requests.
5. Run Backend Server
python proxy.py --port 8080
6. Run Frontend

Simply open:

index.html

in your browser.

🔄 How the System Works
User searches for a stock
Frontend fetches market data
Backend processes data and sends it to AI
AI generates prediction (trend, levels, reasoning)
Second AI verifies the prediction
Final validated output is displayed to the user

📂 Project Structure
├── index.html       # Frontend UI
├── proxy.py         # Backend API + AI proxy
├── README.md
🧪 Commit History (Development Process)

⚠️ Disclaimer
This platform provides AI-generated financial insights for educational and experimental purposes only. It should not be considered financial advice. Always conduct your own research before making investment decisions.
