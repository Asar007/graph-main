"""
Repository Analysis Agent
Orchestrates RAG queries and diagram generation decisions
"""

import json
import re
from typing import Dict, List, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from .rag_pipeline import RAGPipeline
from .prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    REPO_OVERVIEW_PROMPT,
    DIAGRAM_DECISION_PROMPT,
    SEQUENCE_FROM_REPO_PROMPT,
    MINDMAP_FROM_REPO_PROMPT,
    GRAPH_FROM_REPO_PROMPT,
    DOCUMENTATION_PROMPT
)


class RepoAnalysisAgent:
    """Agent for analyzing repositories and generating architecture diagrams."""
    
    def __init__(self, google_api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize the analysis agent.
        
        Args:
            google_api_key: Google API key for Gemini
            model_name: Gemini model to use
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_api_key,
            temperature=0.3
        )
        self.rag = RAGPipeline()
        self.repo_data = None
        self.overview = None
        self.diagram_plan = None
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Extract JSON from LLM response."""
        try:
            # Try to find JSON in code blocks
            match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # Try to find raw JSON
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            
            return None
        except json.JSONDecodeError:
            return None
    
    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Call the LLM with given prompts."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        response = self.llm.invoke(messages)
        return response.content
    
    def ingest_repository(self, repo_data: Dict[str, Any]) -> int:
        """
        Ingest repository data into the RAG pipeline.
        
        Args:
            repo_data: Repository data from GitHub fetcher
            
        Returns:
            Number of documents indexed
        """
        self.repo_data = repo_data
        return self.rag.build_index(repo_data['files'])
    
    def analyze_overview(self) -> Dict[str, Any]:
        """
        Generate high-level repository overview.
        
        Returns:
            Overview analysis as dictionary
        """
        if not self.repo_data:
            raise ValueError("No repository data. Call ingest_repository first.")
        
        # Get file structure
        file_structure = self.rag.get_file_structure(self.repo_data['files'])
        
        # Get architecture-relevant context
        code_context = self.rag.get_architecture_context(k=8)
        
        # Format prompt
        prompt = REPO_OVERVIEW_PROMPT.format(
            repo_name=self.repo_data['full_name'],
            description=self.repo_data.get('description', 'No description'),
            language=self.repo_data.get('language', 'Unknown'),
            file_structure=file_structure[:3000],  # Limit size
            code_context=code_context[:8000]  # Limit size
        )
        
        # Call LLM
        response = self._call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
        self.overview = self._parse_json_response(response)
        
        if not self.overview:
            # Fallback to raw response
            self.overview = {
                "project_type": "unknown",
                "architecture_pattern": "unknown",
                "components": [],
                "raw_analysis": response
            }
        
        return self.overview
    
    def plan_diagrams(self) -> Dict[str, Any]:
        """
        Decide which diagrams to generate.
        
        Returns:
            Diagram generation plan
        """
        if not self.overview:
            self.analyze_overview()
        
        # Get additional context for specific areas
        additional_queries = [
            "API routes endpoints request response",
            "authentication login session token",
            "database queries models data access",
            "error handling exceptions"
        ]
        
        additional_context_parts = []
        for query in additional_queries:
            results = self.rag.query(query, k=3)
            for doc in results:
                additional_context_parts.append(
                    f"[{doc.metadata.get('source', 'unknown')}]\n{doc.page_content[:500]}"
                )
        
        additional_context = "\n\n".join(additional_context_parts[:6])
        
        # Format prompt
        prompt = DIAGRAM_DECISION_PROMPT.format(
            overview_json=json.dumps(self.overview, indent=2),
            additional_context=additional_context[:5000]
        )
        
        # Call LLM
        response = self._call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
        self.diagram_plan = self._parse_json_response(response)
        
        if not self.diagram_plan:
            # Fallback to default diagram plan
            self.diagram_plan = {
                "diagrams": [
                    {
                        "type": "Sequence",
                        "title": f"{self.repo_data['name']} Main Flow",
                        "description": "Main application flow",
                        "generation_prompt": f"Main request/response flow in {self.repo_data['name']}"
                    }
                ],
                "reasoning": "Default diagram plan (LLM parsing failed)"
            }
        
        return self.diagram_plan
    
    def generate_diagram_data(self, diagram_spec: Dict[str, Any]) -> Optional[Dict]:
        """
        Generate diagram JSON data based on specification.
        
        Args:
            diagram_spec: Diagram specification from plan_diagrams
            
        Returns:
            Diagram JSON data ready for rendering
        """
        diagram_type = diagram_spec.get('type', 'Sequence')
        focus_area = diagram_spec.get('generation_prompt', diagram_spec.get('title', ''))
        
        # Query RAG for relevant context
        relevant_docs = self.rag.query(focus_area, k=10)
        code_context = "\n\n".join([
            f"=== {doc.metadata.get('source', 'unknown')} ===\n{doc.page_content}"
            for doc in relevant_docs
        ])
        
        if diagram_type == "Sequence":
            prompt = SEQUENCE_FROM_REPO_PROMPT.format(
                repo_name=self.repo_data['full_name'],
                focus_area=focus_area,
                code_context=code_context[:10000]
            )
        elif diagram_type == "Mindmap":
            file_structure = self.rag.get_file_structure(self.repo_data['files'])
            components = json.dumps(self.overview.get('components', []), indent=2)
            prompt = MINDMAP_FROM_REPO_PROMPT.format(
                repo_name=self.repo_data['full_name'],
                description=self.repo_data.get('description', ''),
                file_structure=file_structure[:3000],
                components=components
            )
        elif diagram_type == "Graph":
            # Query for imports/dependencies
            import_docs = self.rag.query("import require from dependencies", k=15)
            import_context = "\n\n".join([
                f"[{doc.metadata.get('source', '')}]\n{doc.page_content}"
                for doc in import_docs
            ])
            prompt = GRAPH_FROM_REPO_PROMPT.format(
                repo_name=self.repo_data['full_name'],
                import_context=import_context[:5000],
                module_structure=code_context[:5000]
            )
        else:
            # Default to sequence
            prompt = SEQUENCE_FROM_REPO_PROMPT.format(
                repo_name=self.repo_data['full_name'],
                focus_area=focus_area,
                code_context=code_context[:10000]
            )
        
        response = self._call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
        diagram_data = self._parse_json_response(response)
        
        if diagram_data:
            diagram_data['_meta'] = {
                'type': diagram_type,
                'title': diagram_spec.get('title', 'Untitled'),
                'description': diagram_spec.get('description', '')
            }
        
        return diagram_data
    
    def generate_all_diagrams(self) -> List[Dict]:
        """
        Generate all planned diagrams.
        
        Returns:
            List of diagram JSON data
        """
        if not self.diagram_plan:
            self.plan_diagrams()
        
        diagrams = []
        for spec in self.diagram_plan.get('diagrams', []):
            diagram_data = self.generate_diagram_data(spec)
            if diagram_data:
                diagrams.append(diagram_data)
        
        return diagrams
    
    def generate_documentation(self, diagrams: List[Dict]) -> str:
        """
        Generate markdown documentation.
        
        Args:
            diagrams: List of generated diagram data
            
        Returns:
            Markdown documentation string
        """
        diagram_summaries = "\n".join([
            f"- **{d.get('_meta', {}).get('title', 'Diagram')}**: {d.get('_meta', {}).get('description', '')}"
            for d in diagrams
        ])
        
        prompt = DOCUMENTATION_PROMPT.format(
            repo_name=self.repo_data['full_name'],
            analysis_json=json.dumps(self.overview, indent=2),
            diagram_summaries=diagram_summaries
        )
        
        response = self._call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
        return response
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline.
        
        Returns:
            Dictionary with overview, diagrams, and documentation
        """
        overview = self.analyze_overview()
        diagram_plan = self.plan_diagrams()
        diagrams = self.generate_all_diagrams()
        documentation = self.generate_documentation(diagrams)
        
        return {
            'overview': overview,
            'diagram_plan': diagram_plan,
            'diagrams': diagrams,
            'documentation': documentation
        }
