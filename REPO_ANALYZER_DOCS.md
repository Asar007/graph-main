# GitHub Repository Analyzer - Documentation

## Overview

The GitHub Repository Analyzer is an AI-powered tool that automatically analyzes any GitHub repository and generates architecture documentation with interactive diagrams. It uses RAG (Retrieval-Augmented Generation) to understand codebases and dynamically decides which diagrams best explain the architecture.

## What It Does

1. **Fetches Repository Contents** - Downloads all relevant code files from any public/private GitHub repo
2. **Builds a Knowledge Base** - Creates a searchable vector index of the codebase using embeddings
3. **Analyzes Architecture** - Uses AI to identify project type, patterns, components, and data flows
4. **Plans Diagrams** - Intelligently decides which diagrams to generate based on the codebase
5. **Generates Visualizations** - Creates interactive sequence diagrams, mindmaps, graphs, and timelines
6. **Produces Documentation** - Outputs comprehensive markdown documentation with embedded diagrams

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STREAMLIT UI (repo_analyzer.py)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Repo URL   │  │  API Keys   │  │   Options   │  │  Results    │    │
│  │   Input     │  │   Config    │  │   Sidebar   │  │   Tabs      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         GITHUB FETCHER (PyGithub)                        │
│  • Parses repo URL (handles multiple formats)                           │
│  • Authenticates with token for private repos                           │
│  • Recursively fetches all files                                        │
│  • Filters out binaries, lock files, node_modules, etc.                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      RAG PIPELINE (agent/rag_pipeline.py)                │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  Document        │    │  Text Splitter   │    │  ChromaDB        │  │
│  │  Loader          │───▶│  (by code        │───▶│  Vector Store    │  │
│  │  (code files)    │    │   structure)     │    │  (in-memory)     │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                           │             │
│  ┌──────────────────┐    ┌──────────────────┐            │             │
│  │  HuggingFace     │    │  Similarity      │◀───────────┘             │
│  │  Embeddings      │───▶│  Search          │                          │
│  │  (MiniLM)        │    │  (retrieval)     │                          │
│  └──────────────────┘    └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ANALYSIS AGENT (agent/repo_agent.py)                  │
│                                                                          │
│  Step 1: OVERVIEW ANALYSIS                                               │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ • Query RAG for architecture-relevant code                         │ │
│  │ • Identify: project type, architecture pattern, components         │ │
│  │ • Detect: entry points, dependencies, data flow                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                                    ▼                                     │
│  Step 2: DIAGRAM PLANNING                                                │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ • Analyze what diagrams would best explain the architecture        │ │
│  │ • PRIMARY: Sequence diagrams for ALL flows                         │ │
│  │ • SUPPLEMENTARY: Mindmap (structure), Graph (deps), Timeline       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                                    ▼                                     │
│  Step 3: DIAGRAM GENERATION                                              │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ • For each planned diagram:                                        │ │
│  │   - Query RAG for relevant code context                            │ │
│  │   - Generate diagram JSON via Gemini                               │ │
│  │   - Validate JSON structure                                        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                                    ▼                                     │
│  Step 4: DOCUMENTATION                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ • Generate markdown documentation                                  │ │
│  │ • Include: overview, architecture, components, flows               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  DIAGRAM GENERATOR (diagram_generator.py)                │
│                                                                          │
│  ┌─────────────────┐         ┌─────────────────┐                        │
│  │  JSON Data      │────────▶│  HTML Template  │                        │
│  │  (from agent)   │         │  (D3.js/Mermaid)│                        │
│  └─────────────────┘         └─────────────────┘                        │
│                                      │                                   │
│                                      ▼                                   │
│                          ┌─────────────────────┐                        │
│                          │  inject_data_into_  │                        │
│                          │  html()             │                        │
│                          │                     │                        │
│                          │  Replaces markers:  │                        │
│                          │  /* [INJECTION_     │                        │
│                          │     START] */       │                        │
│                          └─────────────────────┘                        │
│                                      │                                   │
│                                      ▼                                   │
│                          ┌─────────────────────┐                        │
│                          │  Interactive HTML   │                        │
│                          │  with embedded      │                        │
│                          │  diagram            │                        │
│                          └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Repository Fetcher (`repo_analyzer.py`)

**Purpose:** Downloads code files from GitHub repositories.

**How it works:**
```python
# Parses various URL formats
"https://github.com/owner/repo"  →  "owner/repo"
"github.com/owner/repo.git"     →  "owner/repo"
"owner/repo"                    →  "owner/repo"

# Fetches via PyGithub API
repo = Github(token).get_repo("owner/repo")
contents = repo.get_contents(path)
```

**File Filtering:**
- **Included:** `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.rb`, `.html`, `.css`, `.json`, `.yaml`, `.md`, etc.
- **Excluded directories:** `node_modules`, `.git`, `__pycache__`, `venv`, `dist`, `build`, etc.
- **Excluded files:** `package-lock.json`, `yarn.lock`, `Cargo.lock`, etc.
- **Size limit:** 100KB per file

### 2. RAG Pipeline (`agent/rag_pipeline.py`)

**Purpose:** Creates a searchable knowledge base from code files.

**How it works:**

```python
# 1. Create documents from files
documents = []
for file_path, content in files.items():
    doc = Document(
        page_content=content,
        metadata={'source': file_path, 'file_type': 'python', ...}
    )
    documents.append(doc)

# 2. Split large files into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    separators=["\nclass ", "\ndef ", "\nfunction ", ...]  # Code-aware
)
chunks = splitter.split_documents(documents)

# 3. Create embeddings and store in ChromaDB
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(chunks, embeddings)

# 4. Query for relevant code
results = vectorstore.similarity_search("API routes endpoints", k=10)
```

**Key Methods:**
- `build_index(files)` - Index all repository files
- `query(text, k)` - Find k most relevant code chunks
- `get_architecture_context()` - Get code relevant for architecture understanding
- `get_file_structure()` - Generate tree view of repository

### 3. Analysis Agent (`agent/repo_agent.py`)

**Purpose:** Orchestrates the analysis and decides what diagrams to generate.

**Analysis Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│                    analyze_overview()                        │
├─────────────────────────────────────────────────────────────┤
│ Input:  File structure + RAG context (entry points, APIs)   │
│ Output: {                                                    │
│   "project_type": "web application",                        │
│   "architecture_pattern": "MVC",                            │
│   "components": [...],                                       │
│   "entry_points": ["app.py", "main.js"],                    │
│   "data_flow_summary": "..."                                │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     plan_diagrams()                          │
├─────────────────────────────────────────────────────────────┤
│ Input:  Overview analysis + additional code context          │
│ Output: {                                                    │
│   "diagrams": [                                              │
│     {"type": "Sequence", "title": "Main Request Flow", ...},│
│     {"type": "Sequence", "title": "Auth Flow", ...},        │
│     {"type": "Mindmap", "title": "Project Structure", ...}  │
│   ],                                                         │
│   "reasoning": "..."                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  generate_diagram_data()                     │
├─────────────────────────────────────────────────────────────┤
│ For each planned diagram:                                    │
│ 1. Query RAG for relevant code (based on diagram topic)     │
│ 2. Format prompt with code context                           │
│ 3. Call Gemini to generate JSON                              │
│ 4. Validate and return diagram data                          │
└─────────────────────────────────────────────────────────────┘
```

**Diagram Decision Logic:**

| What Agent Finds | Diagram Generated |
|------------------|-------------------|
| Any architecture flow | **Sequence** (always primary) |
| API endpoints, request handlers | Sequence: "API Request Flow" |
| Authentication code | Sequence: "Authentication Flow" |
| Database operations | Sequence: "Data Access Flow" |
| Complex file structure | Mindmap: "Project Structure" |
| Module imports/dependencies | Graph: "Module Dependencies" |
| Changelog/versions | Timeline: "Version History" |

### 4. Diagram Generator (`diagram_generator.py`)

**Purpose:** Converts JSON data to interactive HTML diagrams.

**How it works:**

```python
# 1. Load HTML template with D3.js/Mermaid rendering code
template = load_template("sequence_template.html")

# 2. Template contains injection markers:
# /* [INJECTION_START] */
# const architectureData = {};
# /* [INJECTION_END] */

# 3. Inject diagram JSON between markers
html = inject_data_into_html(template, diagram_json)

# 4. Result: Self-contained HTML with interactive diagram
```

**Diagram Types and Schemas:**

| Type | Template | JSON Schema |
|------|----------|-------------|
| Sequence | `sequence_template.html` | `{participants, events, activations, fragments}` |
| Mindmap | `template.html` | `{nodes, edges, hierarchy}` with type: root/category/leaf |
| Graph | `template.html` | `{nodes, edges, hierarchy}` with type: data/backend/frontend |
| Timeline | `timeline_template.html` | `{events, mermaid_syntax}` |

### 5. Prompt Templates (`agent/prompts.py`)

**Purpose:** Define how the AI analyzes code and generates diagrams.

**Key Prompts:**

1. **REPO_OVERVIEW_PROMPT** - Analyzes repository structure and identifies architecture
2. **DIAGRAM_DECISION_PROMPT** - Decides which diagrams to generate
3. **SEQUENCE_FROM_REPO_PROMPT** - Generates sequence diagram from code context
4. **MINDMAP_FROM_REPO_PROMPT** - Generates mindmap from file structure
5. **DOCUMENTATION_PROMPT** - Generates markdown documentation

## Data Flow Example

```
User enters: "https://github.com/fastapi/fastapi"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ FETCH: Download 150 code files (filter out tests, docs)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ INDEX: Create 450 document chunks in ChromaDB               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ ANALYZE: "FastAPI is a web framework using ASGI pattern     │
│          with dependency injection and Pydantic models"     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ PLAN: Generate 3 diagrams:                                  │
│   1. Sequence: "HTTP Request Lifecycle"                     │
│   2. Sequence: "Dependency Injection Flow"                  │
│   3. Mindmap: "FastAPI Architecture"                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ GENERATE: For each diagram, query relevant code and         │
│           generate JSON via Gemini                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ RENDER: Inject JSON into HTML templates                     │
│         Display interactive diagrams in Streamlit           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT: - 3 interactive diagrams (viewable + downloadable)  │
│         - Markdown documentation                            │
│         - Raw file browser                                  │
└─────────────────────────────────────────────────────────────┘
```

## File Structure

```
graph-main/
├── repo_analyzer.py        # Main Streamlit app for repo analysis
├── diagram_generator.py    # Shared diagram generation module
├── app.py                  # Original topic-based diagram generator
│
├── agent/                  # Analysis agent package
│   ├── __init__.py
│   ├── rag_pipeline.py     # RAG with LangChain + ChromaDB
│   ├── repo_agent.py       # Analysis orchestrator
│   └── prompts.py          # LLM prompt templates
│
├── *_prompt.txt            # Diagram generation prompts
├── *_template.html         # D3.js/Mermaid HTML templates
│
├── requirements.txt        # Python dependencies
├── .env                    # API keys (GOOGLE_API_KEY, GITHUB_TOKEN)
└── Dockerfile              # Container deployment
```

## Usage

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
echo "GOOGLE_API_KEY=your_key_here" > .env
echo "GITHUB_TOKEN=your_token_here" >> .env  # Optional, for private repos

# 3. Run the analyzer
streamlit run repo_analyzer.py

# 4. Open http://localhost:8501 and enter a GitHub repo URL
```

## Technologies Used

| Component | Technology |
|-----------|------------|
| UI Framework | Streamlit |
| LLM | Google Gemini 2.5 Flash |
| Embeddings | HuggingFace (all-MiniLM-L6-v2) |
| Vector Store | ChromaDB (in-memory) |
| RAG Framework | LangChain |
| GitHub API | PyGithub |
| Diagram Rendering | D3.js, Mermaid.js |
