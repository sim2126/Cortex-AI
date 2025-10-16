# Cortex AI

### An Advanced, User-Driven Agentic RAG System

An extensible, production-grade platform that unifies knowledge from multiple sources into an intelligent, context-aware retrieval system. Cortex AI allows users to dynamically build a knowledge base by ingesting PDFs and public web links, and then ask complex questions that are answered strictly based on the provided context.

---

## Key Features

### Advanced RAG Pipeline
Utilizes a sophisticated agentic workflow with advanced prompt engineering to understand user queries, retrieve relevant context, and generate detailed, accurate answers.

### Multi-Source Ingestion
Dynamically build your knowledge base with support for:
- **PDF Upload**: Ingest local PDF documents (up to 6MB) with background processing for a fast, non-blocking user experience
- **Web Link Ingestion**: Scrape and process content from public web pages with built-in link validation for clear user feedback

### Knowledge Base Management
A fully interactive UI that displays all ingested data sources and allows users to clear the entire knowledge base to start fresh.

### Production-Ready Backend
Built with FastAPI, featuring asynchronous task handling, modular routers, and a robust architecture.

### Sleek, Modern Frontend
A responsive and aesthetically pleasing user interface built with Next.js, TypeScript, and Tailwind CSS, featuring a live-updating knowledge panel and streamlined user experience.

---

## Tech Stack

**Backend**
- Python 3.11+
- FastAPI
- LangChain & LangGraph
- Google Gemini API
- Neo4j (Graph Database)

**Frontend**
- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui

**Database**
- Neo4j Desktop

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python**: Version 3.11 or higher
- **Node.js**: Version 18 or higher
- **Neo4j Desktop**: The graph database used for storing knowledge

---

## Getting Started

Follow these steps to set up and run the project locally.

### 1. Clone the Repository

```bash
git clone https://github.com/sim2126/Cortex-AI.git
cd Cortex-AI
```

### 2. Backend Setup

This sets up the Python server, agent logic, and database connections.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
# Rename the .env.example file to .env
# Add your Google API Key
# Ensure your Neo4j credentials are correct
cp .env.example .env

# Start your Neo4j Database
# Open Neo4j Desktop and start the database instance
# Ensure the Bolt URI is set to bolt://localhost:7687 in your .env file
```

### 3. Frontend Setup

This sets up the Next.js user interface.

```bash
# Navigate to the UI directory
cd ui

# Install Node.js dependencies
npm install

# Install the UI components
npx shadcn@latest init     # Accept all defaults
npx shadcn@latest add card
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add textarea
```

---

## Running the Application

You will need two separate terminals running at the same time.

### Terminal 1: Start the Backend Server

Run from the root Cortex AI directory:

```bash
uvicorn api.main:app --reload
```

### Terminal 2: Start the Frontend UI

Run from the `Cortex-AI/ui` directory:

```bash
npm run dev
```

---

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Upload PDFs or add web links to build your knowledge base
3. Ask questions and receive answers based strictly on your ingested content
4. Manage your knowledge base through the interactive UI panel

---

## License

This project is licensed under the MIT License.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
