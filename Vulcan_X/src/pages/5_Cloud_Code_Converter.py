# pages/5_Cloud_Code_Converter.py
import streamlit as st
import os
import uuid
from datetime import datetime
from streamlit_code_diff import st_code_diff # NEW: Import streamlit-code-diff
from streamlit_echarts5 import st_echarts # NEW: Import st_echarts for metrics visualization
from core.data_handler import save_uploaded_file_to_temp
from core.llm import get_ragbits_llm_client
from core.agents import RagbitsCloudCodeConverterAgent
from core.neo4j_handler import Neo4jHandler
from core.ragbits_integration import get_confidence_score, get_effort_estimation, get_original_time_estimate, get_time_saved_estimate, _get_code_ast_lang_from_display_lang
from components.ui_styles import apply_custom_styles

# NEW: Page Configuration with icon
st.set_page_config(
    page_title="Cloud Code Converter",
    page_icon="☁️", # Icon for Cloud Code Converter page
    layout="wide"
)

# Apply custom glassmorphic and animation styles (MUST be called on every page)
apply_custom_styles()

# Constants for supported file types and CLOUD_OPTIONS (reverted to original focus)
SUPPORTED_FILE_TYPES = ["py", "yaml", "yml", "json", "xml", "txt", "tf", "java", "js", "ts", "cs", "go", "rb", "php"] # Expanded for more code types

# Helper to map display languages to streamlit-code-diff supported languages (replicated for this file)
def _get_streamlit_code_diff_lang(display_lang: str) -> str:
    # Based on streamlit-code-diff documentation and common mappings
    lang_map = {
        "python": "python", "javascript": "javascript", "js": "javascript",
        "typescript": "typescript", "ts": "typescript", "java": "java",
        "c#": "csharp", "csharp": "csharp", "go": "go", "ruby": "ruby", # go, ruby are not directly supported by s-c-d, but better to try
        "php": "php", "rust": "plaintext", "kotlin": "plaintext", "swift": "plaintext",
        "c++": "cpp", "cpp": "cpp", "c": "c", "sql": "sql", "bash": "bash",
        "sh": "bash", "shell script": "bash", "yaml": "yaml", "yml": "yaml",
        "json": "json", "xml": "xml", "markdown": "markdown", "md": "markdown",
        "dockerfile": "plaintext", "hcl": "plaintext", "html": "html", "css": "css",
        "text": "plaintext", "r": "plaintext", "julia": "plaintext", "haskell": "plaintext",
        "elixir": "plaintext", "erlang": "plaintext", "lua": "plaintext", "assembly": "plaintext",
        "general python": "python", "general javascript": "javascript",
        "general typescript": "typescript", "general java": "java",
        "general c#": "csharp", "general go": "go", "generic yaml": "yaml",
        "generic json": "json", "generic xml": "xml",
    }
    normalized_lang = display_lang.lower().replace(" ", "_").replace(".", "")
    return lang_map.get(normalized_lang, "plaintext") # Default to 'plaintext'

# FIX 4: Expanded CLOUD_OPTIONS
CLOUD_OPTIONS = {
    # Serverless Compute
    "AWS Lambda": ["Python 3.8", "Python 3.9", "Python 3.10", "Python 3.11", "Node.js 18.x", "Node.js 20.x", "Java 11", "Go 1.x", "Ruby 2.7"],
    "Google Cloud Functions": ["Python 3.9", "Python 3.10", "Python 3.11", "Node.js 16", "Node.js 18", "Node.js 20", "Go 1.x", "Java 11", "PHP 7.4", "Ruby 2.7"],
    "Azure Functions": ["Python 3.9", "Python 3.10", "Python 3.11", "Node.js 16", "Node.js 18", "Node.js 20", "C# (.NET 6)", "Java 11", "PowerShell Core 7"],
    # Orchestration / Infrastructure as Code
    "AWS CloudFormation": ["YAML", "JSON", "CDK (Python)", "CDK (TypeScript)"],
    "AWS CDK": ["Python", "TypeScript", "Java", "Go"],
    "Terraform": ["HCL (AWS)", "HCL (Azure)", "HCL (GCP)", "HCL (Kubernetes)"],
    "Azure Resource Manager (ARM) Templates": ["JSON"],
    "Google Cloud Deployment Manager": ["YAML", "Python Jinja2"],
    "Kubernetes Manifests": ["YAML (Deployment)", "YAML (Service)", "YAML (Ingress)", "YAML (Pod)", "Helm Chart"],
    # Data Processing / ETL
    "AWS Glue": ["PySpark (Glue 2.0)", "PySpark (Glue 3.0)", "Scala (Glue 2.0)", "Scala (Glue 3.0)"],
    "Google Cloud Dataflow": ["Apache Beam (Python)", "Apache Beam (Java)"],
    "Azure Data Factory": ["JSON (Pipelines)", "JSON (Datasets)", "JSON (Linked Services)"],
    # Database & Storage Configurations
    "AWS S3 Config": ["JSON Policy", "YAML Bucket Config"],
    "AWS DynamoDB Config": ["JSON Table Schema", "CloudFormation"],
    "Google Cloud Storage Config": ["JSON Policy"],
    "Azure Blob Storage Config": ["JSON Policy"],
    # Messaging & Streaming
    "AWS SQS Config": ["JSON Queue Policy"],
    "AWS Kinesis Config": ["JSON Stream Config"],
    "Google Pub/Sub Config": ["YAML Topic/Subscription"],
    "Azure Service Bus Config": ["JSON Topic/Queue"],
    # General Purpose / Containerization
    "Docker": ["Dockerfile (Basic)", "Dockerfile (Multi-stage)", "Docker Compose"],
    # Generic code/config types
    "General Python": ["Python 2.x", "Python 3.x (General)", "Flask", "Django", "FastAPI", "Pandas", "NumPy"],
    "General JavaScript": ["Node.js (General)", "ES6+", "React", "Vue.js", "Angular", "Express.js", "jQuery"],
    "General TypeScript": ["Node.js (General)", "ES6+", "React/TS", "Angular/TS", "NestJS"],
    "General Java": ["Java 8", "Java 11", "Java 17", "Java 21", "Spring Boot", "Maven", "Gradle"],
    "General C#": [".NET 5", ".NET 6", ".NET 7", ".NET 8", "ASP.NET Core"],
    "General Go": ["Go 1.18", "Go 1.19", "Go 1.20", "Go 1.21", "Gin", "Echo"],
    "Generic YAML": ["Standard YAML", "Ansible Playbook", "GitLab CI/CD", "GitHub Actions"],
    "Generic JSON": ["Standard JSON", "JSON Schema", "REST API Payload"],
    "Generic XML": ["Standard XML", "XML Schema", "SOAP", "REST"],
    "Shell Script": ["Bash", "Zsh", "PowerShell"],
    "SQL": ["ANSI SQL", "PostgreSQL", "MySQL", "SQL Server", "Oracle SQL", "SQLite"],
}
  
# Ensure authentication state is set
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.warning("Please log in to access this page.")
    st.stop()

st.header("Cloud Code Converter")
st.markdown("---")

# Initialize LLM client (once per session)
if "ragbits_llm_cloud" not in st.session_state:
    st.session_state.ragbits_llm_cloud = get_ragbits_llm_client()
# Initialize Cloud Code Converter Agent (once per session)
if "cloud_converter_agent" not in st.session_state:
    st.session_state.cloud_converter_agent = RagbitsCloudCodeConverterAgent(llm=st.session_state.ragbits_llm_cloud)
# Initialize Neo4j Handler (once per session)
if "neo4j_handler_cloud" not in st.session_state:
    st.session_state.neo4j_handler_cloud = Neo4jHandler()

# Initialize session state for code and platforms
if "original_cloud_code" not in st.session_state:
    st.session_state.original_cloud_code = ""
if "converted_cloud_code" not in st.session_state:
    st.session_state.converted_cloud_code = ""
if "selected_source_platform" not in st.session_state:
    st.session_state.selected_source_platform = list(CLOUD_OPTIONS.keys())[0]
if "selected_target_platform" not in st.session_state:
    st.session_state.selected_target_platform = list(CLOUD_OPTIONS.keys())[0]
if "uploaded_file_extension" not in st.session_state: # Ensure this is always initialized
    st.session_state.uploaded_file_extension = ""
# New session state for storing cloud conversion details for Neo4j
if "last_cloud_conversion_details" not in st.session_state:
    st.session_state.last_cloud_conversion_details = None
# New session states for metrics (copied from 1_Code_Gen.py)
if "cloud_code_gen_metrics" not in st.session_state: # Using a different key for this page
    st.session_state.cloud_code_gen_metrics = {
        "confidence": 0.0,
        "effort": 0.0,
        "original_time": 0.0,
        "time_saved": 0.0
    }

st.subheader("1. Upload Your Code")
uploaded_file = st.file_uploader(
    "Upload your code file (.py, .yaml, .yml, .json, .xml, .txt, .tf, .java, .js, .ts, .cs, .go, .rb, .php)",
    type=SUPPORTED_FILE_TYPES,
    key="cloud_code_uploader"
)

if uploaded_file is not None:
    # Read file content
    file_content = uploaded_file.getvalue().decode("utf-8")
    file_extension = uploaded_file.name.split('.')[-1].lower()
    # Update session state if a new file is uploaded or content changes
    if st.session_state.original_cloud_code != file_content or \
       st.session_state.uploaded_file_extension != file_extension:
        st.session_state.original_cloud_code = file_content
        st.session_state.uploaded_file_extension = file_extension
        st.session_state.converted_cloud_code = "" # Clear previous conversion
        st.session_state.last_cloud_conversion_details = None # Clear details
        # Reset metrics on new upload
        st.session_state.cloud_code_gen_metrics = {
            "confidence": 0.0, "effort": 0.0, "original_time": 0.0, "time_saved": 0.0
        }
        # Attempt to set default platforms based on file type
        if file_extension == "py":
            st.session_state.selected_source_platform = "General Python"
        elif file_extension in ["yaml", "yml"]:
            st.session_state.selected_source_platform = "Generic YAML"
        elif file_extension == "json":
            st.session_state.selected_source_platform = "Generic JSON"
        elif file_extension == "xml":
            st.session_state.selected_source_platform = "Generic XML"
        elif file_extension == "tf":
            st.session_state.selected_source_platform = "Terraform"
        elif file_extension == "js":
            st.session_state.selected_source_platform = "General JavaScript"
        elif file_extension == "ts":
            st.session_state.selected_source_platform = "General TypeScript"
        elif file_extension == "java":
            st.session_state.selected_source_platform = "General Java"
        elif file_extension == "cs":
            st.session_state.selected_source_platform = "General C#"
        elif file_extension == "go":
            st.session_state.selected_source_platform = "General Go"
        # st.rerun() # Rerun to update selectbox defaults immediately - consider if desirable or too aggressive
else:
    # If no file is uploaded, clear session state
    if st.session_state.original_cloud_code:
        st.session_state.original_cloud_code = ""
        st.session_state.converted_cloud_code = ""
        st.session_state.uploaded_file_extension = ""
        st.session_state.last_cloud_conversion_details = None # Clear details
        st.session_state.cloud_code_gen_metrics = { # Clear metrics
            "confidence": 0.0, "effort": 0.0, "original_time": 0.0, "time_saved": 0.0
        }
        # st.rerun() # Rerun to clear display
  
# Display original code if available
if st.session_state.original_cloud_code:
    st.subheader("Original Code Preview")
    st.code(st.session_state.original_cloud_code, language=st.session_state.uploaded_file_extension)
else:
    st.info("Upload a code file to begin the conversion process.")
  
st.subheader("2. Define Conversion Parameters")
col_source, col_target = st.columns(2)
with col_source:
    source_platform = st.selectbox(
        "Source Platform/Service:",
        options=list(CLOUD_OPTIONS.keys()),
        key="source_platform_select",
        index=list(CLOUD_OPTIONS.keys()).index(st.session_state.selected_source_platform) # Persist selection
    )
    st.session_state.selected_source_platform = source_platform # Update session state
    
    # Ensure source_version options are dynamically loaded based on selected_source_platform
    source_version_options = CLOUD_OPTIONS.get(source_platform, [])
    current_source_version_index = 0
    # Try to find current selected version in new options, otherwise default to first
    if "selected_source_version" in st.session_state and st.session_state.selected_source_version in source_version_options:
        current_source_version_index = source_version_options.index(st.session_state.selected_source_version)
    source_version = st.selectbox(
        "Source Version:",
        options=source_version_options,
        index=current_source_version_index,
        key="source_version_select"
    )
    st.session_state.selected_source_version = source_version
with col_target:
    target_platform = st.selectbox(
        "Target Platform/Service:",
        options=list(CLOUD_OPTIONS.keys()),
        key="target_platform_select",
        index=list(CLOUD_OPTIONS.keys()).index(st.session_state.selected_target_platform) # Persist selection
    )
    st.session_state.selected_target_platform = target_platform # Update session state
    # Ensure target_version options are dynamically loaded based on selected_target_platform
    target_version_options = CLOUD_OPTIONS.get(target_platform, [])
    current_target_version_index = 0
    if "selected_target_version" in st.session_state and st.session_state.selected_target_version in target_version_options:
        current_target_version_index = target_version_options.index(st.session_state.selected_target_version)
    target_version = st.selectbox(
        "Target Version:",
        options=target_version_options,
        index=current_target_version_index,
        key="target_version_select"
    )
    st.session_state.selected_target_version = target_version

user_instructions = st.text_area(
    "Additional Conversion Instructions (Optional):",
    placeholder="e.g., 'Use AWS SDK v3 for Python', 'Refactor into smaller functions'",
    key="cloud_user_instructions"
)
  
if st.button("Convert Code", key="convert_code_button", disabled=not st.session_state.original_cloud_code):
    if st.session_state.original_cloud_code:
        st.session_state.cloud_code_gen_metrics = { # Reset metrics on new conversion attempt
            "confidence": 0.0, "effort": 0.0, "original_time": 0.0, "time_saved": 0.0
        }
        with st.spinner("Converting code with AI... This may take a moment."):
            # Call the Ragbits cloud converter agent's convert_code method
            converted_code_raw = st.session_state.cloud_converter_agent.convert_code(
                original_code=st.session_state.original_cloud_code,
                file_type=st.session_state.uploaded_file_extension,
                source_platform=source_platform,
                source_version=source_version,
                target_platform=target_platform,
                target_version=target_version,
                user_instructions=user_instructions
            )
            # Check for error messages from the LLM function (via agent)
            if converted_code_raw.startswith("Error: "):
                st.error(converted_code_raw)
                st.session_state.converted_cloud_code = ""
                st.session_state.last_cloud_conversion_details = None # Clear details on error
            else:
                # Extract code from markdown block if present
                if "```" in converted_code_raw:
                    parts = converted_code_raw.split("```")
                    if len(parts) > 1:
                        # Take the content of the first code block
                        converted_code = parts[1].strip()
                        # If a language is specified (e.g., ```python), remove it
                        first_line = converted_code.split('\n')[0].strip()
                        supported_langs = ["python", "javascript", "typescript", "java", "csharp", "go", "ruby", "php", "rust", "kotlin", "swift", "c", "cpp", "sql", "bash", "yaml", "yml", "json", "xml", "markdown", "dockerfile", "hcl", "html", "css", "ini", "txt"]
                        if first_line in supported_langs:
                            converted_code = '\n'.join(converted_code.split('\n')[1:])
                    else:
                        converted_code = converted_code_raw.strip() # No code block found, assume direct code
                else:
                    converted_code = converted_code_raw.strip()
                st.session_state.converted_cloud_code = converted_code
                st.success("Code converted successfully!")

                # Calculate and store metrics (similar to Code Gen page)
                # Determine language for generated code for metrics and diff
                metrics_and_diff_lang = target_platform if target_platform else st.session_state.uploaded_file_extension
                original_code_lang_for_metrics = source_platform if source_platform else st.session_state.uploaded_file_extension
                
                confidence = get_confidence_score(st.session_state.converted_cloud_code, _get_code_ast_lang_from_display_lang(metrics_and_diff_lang))
                effort = get_effort_estimation(st.session_state.converted_cloud_code, _get_code_ast_lang_from_display_lang(metrics_and_diff_lang))
                
                code_for_original_time = st.session_state.original_cloud_code if st.session_state.original_cloud_code.strip() else "def placeholder(): pass"
                original_time = get_original_time_estimate(code_for_original_time, _get_code_ast_lang_from_display_lang(original_code_lang_for_metrics))
                time_saved = get_time_saved_estimate(original_time, effort)
                
                st.session_state.cloud_code_gen_metrics = {
                    "confidence": confidence,
                    "effort": effort,
                    "original_time": original_time,
                    "time_saved": time_saved
                }

                # Prepare conversion details for optional Neo4j storage
                generation_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                st.session_state.last_cloud_conversion_details = {
                    "generation_id": generation_id,
                    "original_code": st.session_state.original_cloud_code,
                    "converted_code": st.session_state.converted_cloud_code,
                    "timestamp": timestamp,
                    "flow_data": {
                        "nodes": [
                            {"id": f"source_{source_platform.replace(' ', '_')}_{source_version.replace(' ', '_')}", "label": f"{source_platform} {source_version}", "type": "platform_source"},
                            {"id": f"target_{target_platform.replace(' ', '_')}_{target_version.replace(' ', '_')}", "label": f"{target_platform} {target_version}", "type": "platform_target"}
                        ],
                        "edges": [
                            {"source": f"source_{source_platform.replace(' ', '_')}_{source_version.replace(' ', '_')}", "target": f"target_{target_platform.replace(' ', '_')}_{target_version.replace(' ', '_')}", "label": "converted_to"}
                        ]
                    },
                    "metrics": st.session_state.cloud_code_gen_metrics # Store metrics with conversion details
                }
                st.info("Code converted. Click 'Save Conversion to Neo4j' to persist this event.")
    else:
        st.error("Please upload code to convert.")

st.markdown("---")
st.subheader("3. Converted Code Preview")
if st.session_state.converted_cloud_code:
    # Attempt to use the target file type extension for syntax highlighting
    display_lang = st.session_state.uploaded_file_extension # Default to uploaded file extension
    # Better logic for guessing target language for highlighting
    if "python" in target_platform.lower() or "python" in target_version.lower():
        display_lang = "python"
    elif "node.js" in target_platform.lower() or "javascript" in target_version.lower() or "js" in target_version.lower() or "react" in target_version.lower():
        display_lang = "javascript"
    elif "typescript" in target_platform.lower() or "ts" in target_version.lower():
        display_lang = "typescript"
    elif "java" in target_platform.lower() or "java" in target_version.lower():
        display_lang = "java"
    elif "c#" in target_platform.lower() or ".net" in target_version.lower():
        display_lang = "csharp"
    elif "go" in target_platform.lower() or "go" in target_version.lower():
        display_lang = "go"
    elif "ruby" in target_platform.lower():
        display_lang = "ruby"
    elif "php" in target_platform.lower():
        display_lang = "php"
    elif "yaml" in target_platform.lower() or "yml" in target_version.lower():
        display_lang = "yaml"
    elif "json" in target_platform.lower():
        display_lang = "json"
    elif "xml" in target_platform.lower():
        display_lang = "xml"
    elif "terraform" in target_platform.lower() or "hcl" in target_version.lower():
        display_lang = "hcl"
    elif "dockerfile" in target_platform.lower() or "docker" in target_version.lower():
        display_lang = "dockerfile"
    elif "sql" in target_platform.lower():
        display_lang = "sql"
    elif "shell script" in target_platform.lower() or "bash" in target_version.lower() or "powershell" in target_version.lower():
        display_lang = "bash" # Use bash for generic shell scripts
    st.code(st.session_state.converted_cloud_code, language=display_lang)
else:
    st.info("Converted code will appear here after conversion.")

# NEW: Performance Metrics section for Cloud Code Converter (copied and adapted from 1_Code_Gen.py)
if st.session_state.cloud_code_gen_metrics["confidence"] > 0 or st.session_state.converted_cloud_code:
    st.subheader("Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="AI Confidence", value=f"{st.session_state.cloud_code_gen_metrics['confidence']*100:.1f}%")
    with col2:
        st.metric(label="Estimated Refinement Effort (Hrs)", value=f"{st.session_state.cloud_code_gen_metrics['effort']:.2f}")
    with col3:
        st.metric(label="Original Dev Time (Hrs)", value=f"{st.session_state.cloud_code_gen_metrics['original_time']:.2f}")
    with col4:
        st.metric(label="Time Saved (Hrs)", value=f"{st.session_state.cloud_code_gen_metrics['time_saved']:.2f}")

    st.markdown("##### Metrics Visualization")

    # --- AI Confidence Doughnut Chart (using ECharts) ---
    st.markdown("###### AI Confidence Score")
    confidence_value = st.session_state.cloud_code_gen_metrics['confidence'] * 100
    
    echarts_confidence_options = {
        "title": {"text": "AI Confidence Score", "left": "center", "textStyle": {"color": "#FFF"}},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b}: {c}%"},
        "legend": {"bottom": "bottom", "data": ["Confidence", "Remaining"], "textStyle": {"color": "#CCC"}},
        "series": [
            {
                "name": "Confidence Breakdown",
                "type": "pie",
                "radius": ["40%", "60%"], # Inner and outer radius for doughnut
                "center": ["50%", "50%"],
                "avoidLabelOverlap": False,
                "label": {
                    "show": False,
                    "position": "center"
                },
                "emphasis": {
                    "label": {
                        "show": True,
                        "fontSize": '20',
                        "fontWeight": 'bold',
                        "color": "#FFF"
                    }
                },
                "labelLine": {
                    "show": False
                },
                "data": [
                    {"value": confidence_value, "name": "Confidence", "itemStyle": {"color": "rgba(75, 192, 192, 0.7)"}},
                    {"value": 100 - confidence_value, "name": "Remaining", "itemStyle": {"color": "rgba(200, 200, 200, 0.3)"}}
                ],
                "itemStyle": {
                    "borderColor": "#0e0d12", # Background color to blend with theme
                    "borderWidth": 2
                }
            }
        ]
    }
    
    try:
        st_echarts(
            options=echarts_confidence_options,
            height="280px", # Adjusted height for doughnut, give it enough space
            width="100%", # Use 100% width to adapt to columns
            key="cloud_confidence_echart" # Unique key for this page
        )
    except Exception as e:
        st.error(f"Error rendering AI Confidence chart with ECharts: {e}")

    # --- Estimated Refinement Effort Bar Chart (using ECharts) ---
    st.markdown("###### Estimated Refinement Effort")
    effort_value = st.session_state.cloud_code_gen_metrics['effort']
    
    echarts_effort_options = {
        "title": {"text": "Estimated Refinement Effort (Hrs)", "left": "center", "textStyle": {"color": "#FFF"}},
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": ["Effort (Hrs)"],
            "axisLabel": {"color": "#CCC"}, # Axis label color
            "axisLine": {"lineStyle": {"color": "#444"}} # Axis line color
        },
        "yAxis": {
            "type": "value",
            "name": "Hours",
            "nameTextStyle": {"color": "#CCC"}, # Y-axis name color
            "axisLabel": {"color": "#CCC"},
            "splitLine": {"lineStyle": {"color": "#333"}} # Grid line color
        },
        "series": [
            {
                "name": "Estimated Effort",
                "type": "bar",
                "data": [effort_value],
                "itemStyle": {"color": "rgba(255, 159, 64, 0.7)"}
            }
        ]
    }
    try:
        st_echarts(
            options=echarts_effort_options,
            height="250px", # Adjusted height for bar chart
            width="100%", # Use 100% width
            key="cloud_effort_echart" # Unique key for this page
        )
    except Exception as e:
        st.error(f"Error rendering Estimated Refinement Effort chart with ECharts: {e}")

    # --- Original Dev Time & Time Saved Bar Chart (using ECharts) ---
    st.markdown("###### Original Development Time vs. Time Saved")
    original_time_value = st.session_state.cloud_code_gen_metrics['original_time']
    time_saved_value = st.session_state.cloud_code_gen_metrics['time_saved']
    
    echarts_time_metrics_options = {
        "title": {"text": "Original Dev Time & Time Saved", "left": "center", "textStyle": {"color": "#FFF"}},
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": "bottom", "data": ["Original Dev Time (Hrs)", "Time Saved (Hrs)"], "textStyle": {"color": "#CCC"}},
        "xAxis": {
            "type": "category",
            "data": ["Time Metrics"], # Single category for comparison
            "axisLabel": {"color": "#CCC"},
            "axisLine": {"lineStyle": {"color": "#444"}}
        },
        "yAxis": {
            "type": "value",
            "name": "Hours",
            "nameTextStyle": {"color": "#CCC"},
            "axisLabel": {"color": "#CCC"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": [
            {
                "name": "Original Dev Time (Hrs)",
                "type": "bar",
                "data": [original_time_value],
                "itemStyle": {"color": "rgba(54, 162, 235, 0.7)"}
            },
            {
                "name": "Time Saved (Hrs)",
                "type": "bar",
                "data": [time_saved_value],
                "itemStyle": {"color": "rgba(153, 102, 255, 0.7)"}
            }
        ]
    }
    try:
        st_echarts(
            options=echarts_time_metrics_options,
            height="250px", # Adjusted height for bar chart
            width="100%", # Use 100% width
            key="cloud_time_metrics_echart" # Unique key for this page
        )
    except Exception as e:
        st.error(f"Error rendering Time Metrics chart with ECharts: {e}")


# NEW: Code Difference Analysis Section (using streamlit-code-diff)
st.markdown("---")
st.subheader("4. Cloud Code Difference Analysis")
# Determine language for streamlit-code-diff
diff_lang_for_display = _get_streamlit_code_diff_lang(target_platform)
if st.session_state.original_cloud_code.strip() or st.session_state.converted_cloud_code.strip():
    try:
        st_code_diff(
            old_string=st.session_state.original_cloud_code,
            new_string=st.session_state.converted_cloud_code,
            language=diff_lang_for_display,
            output_format="side-by-side",
            diff_style="word",
            height="500px",
            key="cloud_code_diff_component"
        )
        if not st.session_state.original_cloud_code.strip() and not st.session_state.converted_cloud_code.strip():
            st.info("No code to compare.")
    except Exception as e:
        st.error(f"Error displaying code diff: {e}")
        st.info("The `streamlit-code-diff` component encountered an issue. Ensure the language selected is supported or try with 'plaintext'.")
else:
    st.info("Convert cloud code to see a visual difference analysis.")