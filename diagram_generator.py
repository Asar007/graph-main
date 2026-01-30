"""
Diagram Generator Module
Extracted from app.py for reuse by the repo analyzer agent
"""

import json
import re
from typing import Dict, Any, Optional, Tuple
import google.generativeai as genai


def load_template(template_path: str) -> Optional[str]:
    """Load an HTML template file."""
    try:
        with open(template_path, "r", encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None


def load_prompt(prompt_path: str) -> Optional[str]:
    """Load a prompt template file."""
    try:
        with open(prompt_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None


def validate_json(json_str: str) -> Optional[Dict]:
    """
    Validate and parse JSON from LLM response.
    Handles multiple schema types: Graph, Mindmap, Sequence, Timeline
    """
    try:
        # Regex to find JSON block enclosed in ```json ... ``` or just { ... }
        match = re.search(r'```json\s*(\{.*?\})\s*```', json_str, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback: Try to find the first outer {} block
            match_fallback = re.search(r'\{.*\}', json_str, re.DOTALL)
            if match_fallback:
                json_str = match_fallback.group(0)
        
        data = json.loads(json_str)
        
        # Determine schema validation type
        if 'participants' in data and 'events' in data:
            # Sequence Diagram Schema
            if not isinstance(data.get('participants'), list):
                print("Validation Error: 'participants' must be a list")
                return None
            if not isinstance(data.get('events'), list):
                print("Validation Error: 'events' must be a list")
                return None
            return data

        # Timeline Schema
        if 'mermaid_syntax' in data:
            return data

        # Graph/Mindmap Schema (Fallback)
        required_fields = ['nodes', 'hierarchy', 'edges']
        for field in required_fields:
            if field not in data:
                print(f"Validation Error: Missing field '{field}'")
                return None
                
        if not isinstance(data.get('nodes'), list):
            print("Validation Error: 'nodes' must be a list")
            return None

        # Validate each node has an ID
        for i, node in enumerate(data['nodes']):
            if not isinstance(node, dict) or 'id' not in node:
                print(f"Validation Error: Node at index {i} missing 'id' or not an object")
                return None
                
        if not isinstance(data.get('edges'), list):
            print("Validation Error: 'edges' must be a list")
            return None

        # Validate each edge has source/target
        for i, edge in enumerate(data['edges']):
            if not isinstance(edge, dict) or 'source' not in edge or 'target' not in edge:
                print(f"Validation Error: Edge at index {i} missing source/target")
                return None
        
        return data
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        return None


def inject_data_into_html(html_content: str, json_data: Dict) -> str:
    """
    Inject JSON data into HTML template between markers.
    Markers: /* [INJECTION_START] */ and /* [INJECTION_END] */
    """
    json_str = json.dumps(json_data, indent=2)
    # Escape </script> to prevent breaking HTML
    json_str = json_str.replace("</", "<\\/")

    start_marker = "/* [INJECTION_START] */"
    end_marker = "/* [INJECTION_END] */"
    
    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker)
    
    if start_idx != -1 and end_idx != -1:
        pre_content = html_content[:start_idx]
        post_content = html_content[end_idx + len(end_marker):]
        
        new_block = f"{start_marker}\n            const architectureData = {json_str};\n            {end_marker}"
        return pre_content + new_block + post_content
    else:
        print("Could not find the insertion point in the HTML template.")
        return html_content


class DiagramGenerator:
    """Generator for various diagram types using Gemini."""
    
    # Template and prompt paths for each diagram type
    DIAGRAM_CONFIG = {
        "Graph": {
            "prompt": "json_only_prompt.txt",
            "template": "template.html",
            "modification_prompt": "modification_prompt.txt"
        },
        "Mindmap": {
            "prompt": "mindmap_prompt.txt",
            "template": "template.html",
            "modification_prompt": "mindmap_modification_prompt.txt"
        },
        "Sequence": {
            "prompt": "sequence_prompt.txt",
            "template": "sequence_template.html",
            "modification_prompt": "modification_prompt.txt"
        },
        "Timeline": {
            "prompt": "timeline_prompt.txt",
            "template": "timeline_template.html",
            "modification_prompt": "modification_prompt.txt"
        }
    }
    
    def __init__(self, api_key: str, base_path: str = "."):
        """
        Initialize the diagram generator.
        
        Args:
            api_key: Google API key for Gemini
            base_path: Base path for template and prompt files
        """
        self.api_key = api_key
        self.base_path = base_path
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def _get_path(self, filename: str) -> str:
        """Get full path for a file."""
        import os
        return os.path.join(self.base_path, filename)
    
    def generate_from_topic(self, topic: str, diagram_type: str = "Graph") -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """
        Generate a diagram from a topic string.
        
        Args:
            topic: The topic to generate a diagram for
            diagram_type: Type of diagram (Graph, Mindmap, Sequence, Timeline)
            
        Returns:
            Tuple of (html_content, json_data, error_message)
        """
        config = self.DIAGRAM_CONFIG.get(diagram_type)
        if not config:
            return None, None, f"Unknown diagram type: {diagram_type}"
        
        prompt_template = load_prompt(self._get_path(config["prompt"]))
        if not prompt_template:
            return None, None, f"Prompt template not found: {config['prompt']}"
        
        final_prompt = prompt_template.replace("[INSERT TOPIC HERE]", topic)
        
        try:
            response = self.model.generate_content(final_prompt)
            json_data = validate_json(response.text)
            
            if json_data:
                html_template = load_template(self._get_path(config["template"]))
                if html_template:
                    new_html = inject_data_into_html(html_template, json_data)
                    return new_html, json_data, None
                else:
                    return None, json_data, f"HTML template not found: {config['template']}"
            else:
                raw_snippet = response.text[:500].replace('\n', ' ')
                return None, None, f"Failed to generate valid JSON. Model output: {raw_snippet}..."
                
        except Exception as e:
            return None, None, f"Exception: {str(e)}"
    
    def generate_from_json(self, json_data: Dict, diagram_type: str = "Sequence") -> Tuple[Optional[str], Optional[str]]:
        """
        Generate HTML from pre-built JSON data (from agent).
        
        Args:
            json_data: The diagram JSON data
            diagram_type: Type of diagram for template selection
            
        Returns:
            Tuple of (html_content, error_message)
        """
        config = self.DIAGRAM_CONFIG.get(diagram_type)
        if not config:
            return None, f"Unknown diagram type: {diagram_type}"
        
        html_template = load_template(self._get_path(config["template"]))
        if not html_template:
            return None, f"HTML template not found: {config['template']}"
        
        try:
            html_content = inject_data_into_html(html_template, json_data)
            return html_content, None
        except Exception as e:
            return None, f"Error injecting data: {str(e)}"
    
    def modify_diagram(self, current_json: Dict, change_request: str, diagram_type: str = "Graph") -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """
        Modify an existing diagram based on user request.
        
        Args:
            current_json: Current diagram JSON data
            change_request: User's modification request
            diagram_type: Type of diagram
            
        Returns:
            Tuple of (html_content, json_data, error_message)
        """
        config = self.DIAGRAM_CONFIG.get(diagram_type)
        if not config:
            return None, None, f"Unknown diagram type: {diagram_type}"
        
        modification_prompt = load_prompt(self._get_path(config.get("modification_prompt", "modification_prompt.txt")))
        if not modification_prompt:
            return None, None, "Modification prompt template not found"
        
        final_prompt = modification_prompt.replace("[INSERT CURRENT JSON DATA HERE]", json.dumps(current_json))
        final_prompt = final_prompt.replace("[INSERT CHANGE REQUEST HERE]", change_request)
        
        try:
            response = self.model.generate_content(final_prompt)
            content = response.text
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*$', '', content)
            
            new_json_data = json.loads(content)
            
            html_template = load_template(self._get_path(config["template"]))
            if html_template:
                new_html = inject_data_into_html(html_template, new_json_data)
                return new_html, new_json_data, None
            else:
                return None, new_json_data, f"HTML template not found: {config['template']}"
                
        except Exception as e:
            return None, None, str(e)
