"""
Prompt templates for the repository analysis agent.
"""

# System prompt for the analysis agent
ANALYSIS_SYSTEM_PROMPT = """You are an expert software architect analyzing a GitHub repository.
Your goal is to understand the codebase architecture and identify key flows that should be documented with diagrams.

You have access to:
1. Repository metadata (name, description, language)
2. File structure
3. Relevant code snippets retrieved via RAG

Your analysis should focus on:
- Identifying the main components/modules
- Understanding data flow and request/response patterns
- Detecting architectural patterns (MVC, microservices, event-driven, etc.)
- Finding key entry points and API endpoints
- Understanding dependencies between components
"""

# Prompt for initial repository overview
REPO_OVERVIEW_PROMPT = """Analyze this repository and provide a high-level overview.

**Repository:** {repo_name}
**Description:** {description}
**Primary Language:** {language}

**File Structure:**
{file_structure}

**Key Files Context:**
{code_context}

Provide a structured analysis:

1. **Project Type**: What kind of application is this? (web app, CLI tool, library, API, etc.)

2. **Architecture Pattern**: What architectural pattern does it follow? (MVC, microservices, monolith, serverless, etc.)

3. **Main Components**: List the key modules/components and their responsibilities.

4. **Entry Points**: Where does the application start? What are the main entry points?

5. **Key Dependencies**: What are the critical external dependencies?

6. **Data Flow**: How does data flow through the system?

Respond in JSON format:
```json
{{
    "project_type": "string",
    "architecture_pattern": "string",
    "components": [
        {{"name": "string", "responsibility": "string", "files": ["string"]}}
    ],
    "entry_points": ["string"],
    "key_dependencies": ["string"],
    "data_flow_summary": "string"
}}
```
"""

# Prompt for deciding which diagrams to generate
DIAGRAM_DECISION_PROMPT = """Based on this repository analysis, decide which diagrams to generate.

**Repository Overview:**
{overview_json}

**Additional Context:**
{additional_context}

Your primary tool is **Sequence Diagrams** for explaining architecture flows.
Generate sequence diagrams for ALL significant flows in the system.

For each diagram, provide:
1. Type (Sequence is primary, but also consider: Mindmap for structure, Graph for dependencies, Timeline for versioning)
2. Title
3. Description of what it will show
4. The specific topic/prompt to generate it

**Rules:**
- ALWAYS generate at least one Sequence diagram for the main application flow
- Generate additional Sequence diagrams for: authentication, data processing, API calls, error handling
- Generate a Mindmap ONLY if project structure is complex
- Generate a Graph ONLY if there are significant module dependencies
- Generate a Timeline ONLY if there's version/changelog history

Respond in JSON format:
```json
{{
    "diagrams": [
        {{
            "type": "Sequence",
            "title": "string",
            "description": "string",
            "generation_prompt": "string (detailed prompt for diagram generation)"
        }}
    ],
    "reasoning": "string (brief explanation of why these diagrams were chosen)"
}}
```
"""

# Prompt template for generating sequence diagrams from repo context
SEQUENCE_FROM_REPO_PROMPT = """You are analyzing a codebase to generate a sequence diagram.

**Repository:** {repo_name}
**Focus Area:** {focus_area}

**Relevant Code:**
{code_context}

Generate a sequence diagram that accurately represents the flow in this codebase.

**Requirements:**
1. Identify the actual participants from the code (classes, modules, services, APIs)
2. Map the real function calls and data flow
3. Include error handling paths if present in the code
4. Use accurate labels from the actual code

Generate the sequence diagram JSON following this schema:
```json
{{
  "metadata": {{
    "title": "string",
    "summary": "string (2-3 sentences describing this flow)"
  }},
  "participants": [
    {{
      "id": "string (lowercase, no spaces)",
      "label": "string (display name)",
      "type": "Actor or Participant",
      "description": "string"
    }}
  ],
  "activations": [
    {{"participant": "string", "startStep": number, "endStep": number}}
  ],
  "fragments": [
    {{
      "type": "alt|loop|opt",
      "condition": "string",
      "startStep": number,
      "endStep": number,
      "label": "string"
    }}
  ],
  "events": [
    {{
      "step": number,
      "type": "message",
      "source": "string (participant id)",
      "target": "string (participant id)",
      "label": "string (method/action name)",
      "arrowType": "solid|open_arrow",
      "lineType": "solid|dotted"
    }}
  ]
}}
```

**Important:**
- Use `arrowType: "open_arrow"` and `lineType: "dotted"` for response/return messages
- Steps must be in chronological order starting from 1
- Every participant ID in events must exist in participants array
"""

# Prompt for generating mindmap from repo structure
MINDMAP_FROM_REPO_PROMPT = """Generate a mindmap representing the structure of this repository.

**Repository:** {repo_name}
**Description:** {description}

**File Structure:**
{file_structure}

**Component Overview:**
{components}

Create a hierarchical mindmap with:
- Root: The project name
- Level 1: Major components/modules
- Level 2: Sub-components or features
- Level 3: Specific implementations

Generate JSON following this schema:
```json
{{
  "metadata": {{ "topic": "string", "contentType": "mindmap", "nodeCount": number }},
  "nodes": [
    {{ "id": "string", "data": {{ "label": "string", "type": "root|category|leaf", "summary": "string", "hoverSummary": "string" }} }}
  ],
  "edges": [
    {{ "id": "string", "source": "string", "target": "string", "type": "connects" }}
  ],
  "hierarchy": {{
    "root_id": ["child_id1", "child_id2"]
  }}
}}
```
"""

# Prompt for generating dependency graph
GRAPH_FROM_REPO_PROMPT = """Generate a dependency graph for this repository.

**Repository:** {repo_name}

**Import Analysis:**
{import_context}

**Module Structure:**
{module_structure}

Create a graph showing dependencies between modules/components.

Generate JSON following this schema:
```json
{{
  "metadata": {{
    "projectName": "string",
    "description": "string",
    "version": "1.0"
  }},
  "nodes": [
    {{
      "id": "string",
      "data": {{
        "label": "string",
        "type": "data|backend|frontend|utility",
        "description": "string",
        "summary": "string"
      }}
    }}
  ],
  "hierarchy": {{
    "parent_id": ["child_id1", "child_id2"]
  }},
  "edges": [
    {{
      "id": "string",
      "source": "string",
      "target": "string",
      "type": "imports|depends_on|uses"
    }}
  ]
}}
```
"""

# Documentation template prompt
DOCUMENTATION_PROMPT = """Generate comprehensive architecture documentation for this repository.

**Repository:** {repo_name}
**Analysis:** {analysis_json}
**Generated Diagrams:** {diagram_summaries}

Create a well-structured markdown document with:

1. **Overview** - What the project does, its purpose
2. **Architecture** - High-level architecture description
3. **Components** - Description of each major component
4. **Key Flows** - Reference the sequence diagrams
5. **Dependencies** - External dependencies and their purpose
6. **Getting Started** - How to run/use the project (if discernible from code)

Use clear headings, bullet points, and reference the diagrams by title.
"""
