import streamlit as st
import os
import tempfile
import shutil
from dotenv import load_dotenv
from github import Github, GithubException
from pathlib import Path

from agent.repo_agent import RepoAnalysisAgent
from diagram_generator import DiagramGenerator

# Load environment variables
load_dotenv(override=True)

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="GitHub Repo Analyzer",
    page_icon="🔍",
    initial_sidebar_state="expanded"
)

# File extensions to include (code files)
INCLUDED_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.rb', '.php',
    '.c', '.cpp', '.h', '.hpp', '.cs', '.swift', '.kt', '.scala', '.clj',
    '.html', '.css', '.scss', '.sass', '.less',
    '.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.cfg',
    '.md', '.txt', '.rst',
    '.sql', '.graphql',
    '.sh', '.bash', '.zsh', '.ps1',
    '.dockerfile', '.docker-compose.yml'
}

# Directories to ignore
IGNORED_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
    '.idea', '.vscode', 'dist', 'build', 'target', 'out', 'bin', 'obj',
    '.next', '.nuxt', 'coverage', '.pytest_cache', '.mypy_cache',
    'vendor', 'packages', '.gradle', '.maven'
}

# Files to ignore
IGNORED_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'Cargo.lock',
    'poetry.lock', 'Gemfile.lock', 'composer.lock'
}

# Maximum file size to process (in bytes)
MAX_FILE_SIZE = 100 * 1024  # 100KB


def should_include_file(file_path: str, file_size: int) -> bool:
    """Check if a file should be included in analysis."""
    path = Path(file_path)
    
    # Check if in ignored directory
    for part in path.parts:
        if part in IGNORED_DIRS:
            return False
    
    # Check if ignored file
    if path.name in IGNORED_FILES:
        return False
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        return False
    
    # Check extension (also include files without extension like Dockerfile, Makefile)
    ext = path.suffix.lower()
    name = path.name.lower()
    
    if ext in INCLUDED_EXTENSIONS:
        return True
    
    # Include common config files without extensions
    if name in {'dockerfile', 'makefile', 'rakefile', 'gemfile', 'procfile', 
                'vagrantfile', 'jenkinsfile', '.gitignore', '.env.example'}:
        return True
    
    return False


def fetch_repo_contents(repo_url: str, github_token: str = None) -> dict:
    """Fetch repository contents from GitHub."""
    # Parse repo URL to get owner/repo
    # Handle formats: https://github.com/owner/repo or owner/repo
    repo_url = repo_url.strip()
    if repo_url.startswith('https://github.com/'):
        repo_path = repo_url.replace('https://github.com/', '').rstrip('/')
    elif repo_url.startswith('github.com/'):
        repo_path = repo_url.replace('github.com/', '').rstrip('/')
    else:
        repo_path = repo_url.rstrip('/')
    
    # Remove .git suffix if present
    if repo_path.endswith('.git'):
        repo_path = repo_path[:-4]
    
    # Initialize GitHub client
    if github_token:
        g = Github(github_token)
    else:
        g = Github()  # Anonymous access (rate limited)
    
    try:
        repo = g.get_repo(repo_path)
    except GithubException as e:
        if e.status == 404:
            raise ValueError(f"Repository not found: {repo_path}. Check the URL or provide a GitHub token for private repos.")
        elif e.status == 403:
            raise ValueError("Rate limit exceeded or access denied. Please provide a GitHub token.")
        else:
            raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")
    
    files = {}
    file_count = 0
    skipped_count = 0
    
    def fetch_contents(path=""):
        nonlocal file_count, skipped_count
        try:
            contents = repo.get_contents(path)
        except GithubException:
            return
        
        for content in contents:
            if content.type == "dir":
                # Skip ignored directories
                if content.name in IGNORED_DIRS:
                    continue
                fetch_contents(content.path)
            else:
                if should_include_file(content.path, content.size):
                    try:
                        file_content = content.decoded_content.decode('utf-8', errors='ignore')
                        files[content.path] = {
                            'content': file_content,
                            'size': content.size,
                            'sha': content.sha
                        }
                        file_count += 1
                    except Exception:
                        skipped_count += 1
                else:
                    skipped_count += 1
    
    fetch_contents()
    
    return {
        'name': repo.name,
        'full_name': repo.full_name,
        'description': repo.description or "No description",
        'language': repo.language,
        'stars': repo.stargazers_count,
        'default_branch': repo.default_branch,
        'files': files,
        'file_count': file_count,
        'skipped_count': skipped_count
    }


def main():
    st.title("🔍 GitHub Repository Analyzer")
    st.markdown("Analyze any GitHub repository and generate architecture documentation with diagrams.")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Keys
        st.subheader("API Keys")
        google_api_key = os.getenv("GOOGLE_API_KEY") or st.text_input(
            "Google API Key",
            type="password",
            help="Required for Gemini LLM"
        )
        
        github_token = os.getenv("GITHUB_TOKEN") or st.text_input(
            "GitHub Token (optional)",
            type="password",
            help="Required for private repos, increases rate limit"
        )
        
        st.divider()
        
        # Analysis options
        st.subheader("Analysis Options")
        analysis_depth = st.select_slider(
            "Analysis Depth",
            options=["Quick", "Standard", "Deep"],
            value="Standard",
            help="Deep analysis generates more detailed diagrams"
        )
        
        include_tests = st.checkbox("Include test files", value=False)
        
        st.divider()
        st.markdown("**Diagram Types:**")
        st.markdown("- 🔄 Sequence (Primary)")
        st.markdown("- 🗺️ Mindmap")
        st.markdown("- 📊 Graph")
        st.markdown("- 📅 Timeline")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        repo_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repository",
            help="Enter the full URL or owner/repo format"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        analyze_button = st.button("🚀 Analyze Repository", type="primary", use_container_width=True)
    
    # Session state initialization
    if 'repo_data' not in st.session_state:
        st.session_state.repo_data = None
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'diagrams' not in st.session_state:
        st.session_state.diagrams = []
    if 'documentation' not in st.session_state:
        st.session_state.documentation = None
    
    # Analysis workflow
    if analyze_button and repo_url:
        if not google_api_key:
            st.error("Please provide a Google API Key in the sidebar.")
            return
        
        # Step 1: Fetch repository
        with st.status("Analyzing repository...", expanded=True) as status:
            st.write("📥 Fetching repository contents...")
            
            try:
                repo_data = fetch_repo_contents(repo_url, github_token)
                st.session_state.repo_data = repo_data
                st.write(f"✅ Found {repo_data['file_count']} files ({repo_data['skipped_count']} skipped)")
                
                # Display repo info
                st.write(f"📦 **{repo_data['full_name']}**")
                st.write(f"   {repo_data['description']}")
                st.write(f"   Language: {repo_data['language']} | ⭐ {repo_data['stars']}")
                
                # Step 2: Initialize agent and build RAG index
                st.write("🔨 Building knowledge base...")
                agent = RepoAnalysisAgent(google_api_key)
                doc_count = agent.ingest_repository(repo_data)
                st.write(f"✅ Indexed {doc_count} document chunks")
                
                # Step 3: Analyze architecture
                st.write("🧠 Analyzing architecture...")
                overview = agent.analyze_overview()
                st.session_state.analysis_results = overview
                st.write(f"✅ Identified: {overview.get('project_type', 'Unknown')} ({overview.get('architecture_pattern', 'Unknown')})")
                
                # Step 4: Plan diagrams
                st.write("📋 Planning diagrams...")
                diagram_plan = agent.plan_diagrams()
                planned_count = len(diagram_plan.get('diagrams', []))
                st.write(f"✅ Planned {planned_count} diagrams")
                
                # Step 5: Generate diagram data
                st.write("📊 Generating diagrams...")
                diagram_data_list = agent.generate_all_diagrams()
                
                # Step 6: Render diagrams to HTML
                diagram_generator = DiagramGenerator(google_api_key)
                rendered_diagrams = []
                
                for diagram_data in diagram_data_list:
                    if diagram_data:
                        diagram_type = diagram_data.get('_meta', {}).get('type', 'Sequence')
                        html, error = diagram_generator.generate_from_json(diagram_data, diagram_type)
                        if html:
                            rendered_diagrams.append({
                                'html': html,
                                'data': diagram_data,
                                'title': diagram_data.get('_meta', {}).get('title', 'Diagram'),
                                'type': diagram_type
                            })
                
                st.session_state.diagrams = rendered_diagrams
                st.write(f"✅ Rendered {len(rendered_diagrams)} diagrams")
                
                # Step 7: Generate documentation
                st.write("📄 Generating documentation...")
                documentation = agent.generate_documentation(diagram_data_list)
                st.session_state.documentation = documentation
                st.write("✅ Documentation ready")
                
                status.update(label="Analysis complete!", state="complete", expanded=False)
                
            except ValueError as e:
                st.error(str(e))
                status.update(label="Analysis failed", state="error")
                return
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                status.update(label="Analysis failed", state="error")
                return
    
    # Display results if available
    if st.session_state.repo_data:
        st.divider()
        
        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Diagrams", "📄 Documentation", "📁 Files"])
        
        with tab1:
            if st.session_state.diagrams:
                for i, diagram in enumerate(st.session_state.diagrams):
                    st.subheader(f"{diagram['type']}: {diagram['title']}")
                    st.components.v1.html(diagram['html'], height=700, scrolling=True)
                    
                    # Download button for each diagram
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.download_button(
                            f"⬇️ Download HTML",
                            diagram['html'],
                            f"{diagram['title'].replace(' ', '_')}.html",
                            "text/html",
                            key=f"download_diagram_{i}"
                        )
                    st.divider()
            else:
                st.info("No diagrams generated yet. Click 'Analyze Repository' to start.")
        
        with tab2:
            if st.session_state.documentation:
                st.markdown(st.session_state.documentation)
                st.divider()
                st.download_button(
                    "⬇️ Download Documentation (Markdown)",
                    st.session_state.documentation,
                    f"{st.session_state.repo_data['name']}_architecture.md",
                    "text/markdown"
                )
            elif st.session_state.analysis_results:
                st.markdown("### Architecture Analysis")
                st.json(st.session_state.analysis_results)
            else:
                st.info("Documentation will appear here after analysis.")
        
        with tab3:
            st.markdown(f"### Repository Files ({st.session_state.repo_data['file_count']} files)")
            
            # Display file tree
            files = st.session_state.repo_data['files']
            for file_path in sorted(files.keys()):
                with st.expander(f"📄 {file_path}"):
                    st.code(files[file_path]['content'][:2000], language=Path(file_path).suffix[1:] or 'text')
                    if len(files[file_path]['content']) > 2000:
                        st.caption("(Truncated to 2000 characters)")


if __name__ == "__main__":
    main()
