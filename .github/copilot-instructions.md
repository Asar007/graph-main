# Copilot Instructions

## Project Overview

AI-powered graph visualization suite with two main applications:

1. **`app.py`** - Interactive diagram generator: Users enter a topic, generates visualizations via Gemini
2. **`repo_analyzer.py`** - GitHub repository analyzer: Analyzes repos with RAG, auto-generates architecture diagrams

Both use Google Gemini for LLM and render diagrams via D3.js/Mermaid HTML templates.

## Commands

```bash
# Run the topic-based diagram generator
streamlit run app.py

# Run the GitHub repo analyzer
streamlit run repo_analyzer.py

# Run with Docker
docker build -t graph-app .
docker run -p 8501:8501 graph-app

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Core Flow
- `app.py` - Topic-based Streamlit diagram generator
- `repo_analyzer.py` - GitHub repo analysis with RAG-powered agent
- `diagram_generator.py` - Shared diagram generation module
- `agent/` - RAG pipeline and analysis agent
  - `rag_pipeline.py` - LangChain + ChromaDB for code indexing
  - `repo_agent.py` - Orchestrates analysis and diagram decisions
  - `prompts.py` - LLM prompt templates
- Prompt templates (`*_prompt.txt`) - Define JSON schema expectations for Gemini
- HTML templates (`*_template.html`) - D3.js/Mermaid visualizations with injection markers

### Visualization Types
| Type | Prompt File | Template | JSON Schema |
|------|-------------|----------|-------------|
| Graph | `json_only_prompt.txt` | `template.html` | nodes, hierarchy, edges |
| Mindmap | `mindmap_prompt.txt` | `template.html` | nodes, hierarchy, edges (type: root/category/leaf) |
| Sequence | `sequence_prompt.txt` | `sequence_template.html` | participants, events, activations, fragments |
| Timeline | `timeline_prompt.txt` | `timeline_template.html` | events array + mermaid_syntax |

### JSON Injection Pattern
HTML templates contain injection markers:
```javascript
/* [INJECTION_START] */
const architectureData = {...};
/* [INJECTION_END] */
```
The `inject_data_into_html()` function replaces content between these markers.

## Key Conventions

### Adding New Visualization Types
1. Create `<type>_prompt.txt` with JSON schema and generation rules
2. Create `<type>_template.html` with D3.js/Mermaid rendering and injection markers
3. Add to `DiagramGenerator.DIAGRAM_CONFIG` in `diagram_generator.py`
4. Update the graph type selector in the UI

### Prompt Template Format
- Use `[INSERT TOPIC HERE]` as the placeholder for user input
- Use `[INSERT CURRENT JSON DATA HERE]` and `[INSERT CHANGE REQUEST HERE]` for modification prompts
- Define strict JSON schemas - Gemini output is parsed directly

### JSON Validation
`validate_json()` handles multiple schema types:
- Sequence: requires `participants` and `events`
- Timeline: requires `mermaid_syntax`
- Graph/Mindmap: requires `nodes`, `hierarchy`, `edges`

### Repo Analyzer Agent
The agent prioritizes **Sequence Diagrams** for architecture explanation:
- Always generates sequence diagrams for main flows
- Supplementary: Mindmap (structure), Graph (dependencies), Timeline (history)

## Environment

Requires in `.env` file:
- `GOOGLE_API_KEY` - Gemini API access (required)
- `GITHUB_TOKEN` - For private repo access (optional)
