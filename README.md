<div align="center"><br /><img src="https://www.google.com/search?q=https://i.imgur.com/O61L4mG.png" alt="Cortex AI Banner" width="800"/><br /><h1><b>Cortex AI</b></h1><h3><i>An Advanced, User-Driven Agentic RAG System</i></h3><p>An extensible, production-grade platform that unifies knowledge from multiple sources into an intelligent, context-aware retrieval system. Cortex AI allows users to dynamically build a knowledge base by ingesting PDFs and public web links, and then ask complex questions that are answered <i>strictly</i> based on the provided context.</p></div>✨ Features🧠 Advanced RAG Pipeline: Utilizes a sophisticated agentic workflow with advanced prompt engineering to understand user queries, retrieve relevant context, and generate detailed, accurate answers.📚 Multi-Source Ingestion: Dynamically build your knowledge base.PDF Upload: Ingest local PDF documents (up to 6MB) with background processing for a fast, non-blocking user experience.Web Link Ingestion: Scrape and process content from public web pages. Includes link validation to provide clear user feedback.💡 Knowledge Base Management: A fully interactive UI that displays all ingested data sources and allows the user to clear the entire knowledge base to start fresh.🚀 Production-Ready Backend: Built with FastAPI, featuring asynchronous task handling, modular routers, and a robust architecture.🎨 Sleek, Modern Frontend: A responsive and aesthetically pleasing user interface built with Next.js, TypeScript, and Tailwind CSS, featuring a live-updating knowledge panel and a streamlined user experience.📸 DemoHere is the final application in action:🛠️ Tech StackBackendFrontendDatabase📋 PrerequisitesBefore you begin, ensure you have the following installed:Python: Version 3.11 or higher.Node.js: Version 18 or higher.Neo4j Desktop: The graph database used for storing knowledge.🚀 Getting StartedFollow these steps to set up and run the project locally.1. Clone the Repositorygit clone [https://github.com/sim2126/Cortex-AI.git](https://github.com/sim2126/Cortex-AI.git)
cd Cortex-AI
2. Backend SetupThis sets up the Python server, agent logic, and database connections.# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate  # On Windows: .venv\Scripts\Activate.ps1

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set up environment variables
#    - Rename the `.env.example` file to `.env`
#    - Add your Google API Key
#    - Ensure your Neo4j credentials are correct
cp .env.example .env

# 4. Start your Neo4j Database
#    - Open Neo4j Desktop and start the database instance.
#    - Ensure the Bolt URI is set to `bolt://localhost:7687` in your `.env` file.
3. Frontend SetupThis sets up the Next.js user interface.# 1. Navigate to the UI directory
cd ui

# 2. Install Node.js dependencies
npm install

# 3. Install the UI components
npx shadcn@latest init     # Accept all defaults
npx shadcn@latest add card
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add textarea
⚡ Running the ApplicationYou will need two separate terminals running at the same time.Terminal 1: Start the Backend Server(Run from the root Cortex AI directory)uvicorn api.main:app --reload
Terminal 2: Start the Frontend UI(Run from the Cortex AI/ui directory)npm run dev
