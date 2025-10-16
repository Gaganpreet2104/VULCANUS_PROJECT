# pages/1_Code_Gen.py
import streamlit as st
import pandas as pd
from streamlit_echarts5 import st_echarts # CHANGED: Import st_echarts
import uuid
import json
from streamlit_code_diff import st_code_diff # Import streamlit-code-diff
from core.agents import RagbitsCodeGenerationAgent
from core.llm import get_ragbits_llm_client
from core.neo4j_handler import Neo4jHandler
from components.ui_styles import apply_custom_styles
from core.ragbits_integration import get_confidence_score, get_effort_estimation, get_original_time_estimate, get_time_saved_estimate, _get_code_ast_lang_from_display_lang # Using _get_code_ast_lang_from_display_lang for metrics logic
from datetime import datetime

# NEW: Page Configuration with icon
st.set_page_config(
    page_title="Code Generation & Conversion",
    page_icon="💻", # Icon for Code Gen page
    layout="wide"
)

# Apply custom glassmorphic and animation styles (MUST be called on every page)
apply_custom_styles()

# Define the comprehensive language and framework options for Code Gen page
LANGUAGE_OPTIONS = {
    # General Programming Languages
    "Python": ["Python 2.x", "Python 3.x (General)", "Python 3.8", "Python 3.9", "Python 3.10", "Python 3.11", "Python 3.12", "Flask", "Django", "FastAPI", "Pandas", "NumPy"],
    "JavaScript": ["Node.js (General)", "Node.js 16", "Node.js 18", "Node.js 20", "ES6+", "React", "Vue.js", "Angular", "Express.js", "jQuery"],
    "TypeScript": ["Node.js (General)", "ES6+", "React/TS", "Angular/TS", "NestJS"],
    "Java": ["Java 8", "Java 11", "Java 17", "Java 21", "Spring Boot", "Maven", "Gradle"],
    "C#": [".NET 5", ".NET 6", ".NET 7", ".NET 8", "ASP.NET Core"],
    "Go": ["Go 1.18", "Go 1.19", "Go 1.20", "Go 1.21", "Gin", "Echo"],
    "Ruby": ["Ruby 2.7", "Ruby 3.0", "Ruby 3.1", "Ruby 3.2", "Ruby on Rails"],
    "PHP": ["PHP 7.x", "PHP 8.0", "PHP 8.1", "PHP 8.2", "Laravel", "Symfony"],
    "Rust": ["Rust 2021 Edition", "Actix Web", "Tokio", "Rocket"],
    "Kotlin": ["Kotlin 1.x (JVM)", "Kotlin 1.x (Native)", "Ktor"],
    "Swift": ["Swift 5.x", "iOS", "macOS"],
    "C++": ["C++11", "C++14", "C++17", "C++20", "CMake", "Boost"],
    "C": ["C99", "C11", "GNU C"],
    "Dart": ["Dart 2.x", "Flutter"],
    "Scala": ["Scala 2.x", "Scala 3.x", "Akka", "Spark"],
    "Perl": ["Perl 5.x"],
    "R": ["R (General)", "Tidyverse"],
    "Julia": ["Julia 1.x"],
    "Haskell": ["Haskell (General)", "Yesod"],
    "Elixir": ["Elixir 1.x", "Phoenix"],
    "Erlang": ["Erlang/OTP"],
    "Lua": ["Lua (General)"],
    "Assembly": ["x86", "ARM"],
    # Data/Config Languages
    "SQL": ["ANSI SQL", "PostgreSQL", "MySQL", "SQL Server", "Oracle SQL", "SQLite"],
    "Shell Script": ["Bash", "Zsh", "PowerShell", "Batch (.bat)"],
    "YAML": ["YAML 1.1", "YAML 1.2", "Kubernetes Manifest", "Ansible YAML"],
    "JSON": ["JSON (Standard)", "JSON Schema"],
    "XML": ["XML (Standard)", "XSD", "XPath", "XSLT"],
    "Markdown": ["CommonMark", "GitHub Flavored Markdown"],
    # DevOps/Infrastructure
    "Dockerfile": ["Docker 1.x"],
    "Terraform HCL": ["Terraform 0.12+", "Terraform 1.x"],
    "Ansible Playbook": ["Ansible 2.9+", "Ansible Core 2.12+"],
    "CloudFormation YAML/JSON": ["AWS CloudFormation"],
    "Azure ARM Templates": ["Azure Resource Manager"],
    # Frontend/Markup
    "HTML": ["HTML5", "XHTML", "Jinja2", "Handlebars"],
    "CSS": ["CSS3", "Sass", "Less", "Tailwind CSS", "Bootstrap CSS"],
}
# Supported file extensions for previewing generated code
SUPPORTED_GEN_CODE_EXTENSIONS = {
    "py": "python", "js": "javascript", "ts": "typescript", "java": "java", "cs": "csharp",
    "go": "go", "rb": "ruby", "php": "php", "rs": "rust", "kt": "kotlin", "swift": "swift",
    "cpp": "cpp", "c": "c", "sql": "sql", "sh": "bash", "yaml": "yaml", "yml": "yaml",
    "json": "json", "json": "json", "xml": "xml", "md": "markdown", "dockerfile": "dockerfile",
    "hcl": "hcl", "html": "html", "css": "css", "ini": "ini", "txt": "text"
}
# Helper to map display languages to streamlit-code-diff supported languages
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
        "generic json": "json",
        "generic xml": "xml",
    }
    normalized_lang = display_lang.lower().replace(" ", "_").replace(".", "")
    return lang_map.get(normalized_lang, "plaintext") # Default to 'plaintext'

# Ensure authentication state is set
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.warning("Please log in to access this page.")
    st.stop()

st.header("Code Generator & Converter")
st.markdown("---")

# Initialize LLM client (once per session)
if "ragbits_llm" not in st.session_state:
    st.session_state.ragbits_llm = get_ragbits_llm_client()
# Initialize Neo4j Handler (once per session)
if "neo4j_handler" not in st.session_state:
    st.session_state.neo4j_handler = Neo4jHandler()

# Initialize session state for code and agent
if "original_code" not in st.session_state:
    st.session_state.original_code = ""
if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""
if "conversion_successful" not in st.session_state:
    st.session_state.conversion_successful = False
if "code_flow_data" not in st.session_state:
    st.session_state.code_flow_data = None
if "original_code_for_flow" not in st.session_state:
    st.session_state.original_code_for_flow = ""
# New session states for language conversion
if "selected_source_language" not in st.session_state:
    st.session_state.selected_source_language = list(LANGUAGE_OPTIONS.keys())[0]
if "selected_target_language" not in st.session_state:
    st.session_state.selected_target_language = list(LANGUAGE_OPTIONS.keys())[0]
if "selected_source_framework" not in st.session_state:
    st.session_state.selected_source_framework = LANGUAGE_OPTIONS[st.session_state.selected_source_language][0]
if "selected_target_framework" not in st.session_state:
    st.session_state.selected_target_framework = LANGUAGE_OPTIONS[st.session_state.selected_target_language][0]
# New session state for storing generation details for Neo4j
if "last_code_generation_details" not in st.session_state:
    st.session_state.last_code_generation_details = None
# New session states for metrics
if "code_gen_metrics" not in st.session_state:
    st.session_state.code_gen_metrics = {
        "confidence": 0.0,
        "effort": 0.0,
        "original_time": 0.0,
        "time_saved": 0.0
    }

# --- Code Input Section ---
st.subheader("1. Enter Your Code")
# Sample code for initial display
sample_python_code = """
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)
def fibonacci(n):
    a, b = 0, 1
    for i in range(n):
        # print(a) # Commented out to avoid direct console output
        a, b = b, a + b
    return a # Return last Fibonacci number for example
# Example usage (uncomment to test):
# result_fact = factorial(5)
# print(f"Factorial of 5: {result_fact}")
# result_fib = fibonacci(5)
# print(f"Fibonacci number at 5: {result_fib}")
"""
original_code = st.text_area(
    "Paste your code here:",
    value=st.session_state.original_code if st.session_state.original_code else sample_python_code, # Use session state or sample
    height=300,
    key="original_code_input"
)
st.session_state.original_code = original_code # Update session state

st.subheader("2. Define Operation & Target")
col_op, col_persona = st.columns(2)
with col_op:
    conversion_operation = st.selectbox(
        "Select Operation Type:",
        ["Generate Code", "Refactor Code", "Optimize Code", "Convert Language"],
        key="conversion_operation_select"
    )
with col_persona:
    agent_persona_choice = st.selectbox(
        "AI Agent Persona / Focus:",
        ["Standard", "Senior Engineer (Robust, Idiomatic)", "Performance Expert (Highly Optimized)", "Junior Coder (Simple, Explicit)"],
        key="agent_persona_select"
    )

# Re-initialize agent if persona changes or if not yet created
if "code_gen_agent" not in st.session_state or \
   st.session_state.code_gen_agent.persona != agent_persona_choice:
    st.session_state.code_gen_agent = RagbitsCodeGenerationAgent(
        llm=st.session_state.ragbits_llm,
        persona=agent_persona_choice
    )

# Enabled Temperature slider
ai_temperature = st.slider("AI Creativity (Temperature):", min_value=0.0, max_value=1.0, value=0.7, step=0.1, help="Adjust the AI's creativity (higher values mean more varied, potentially less accurate output).")

# Conditional language selection for "Convert Language" operation
if conversion_operation == "Convert Language":
    st.markdown("---")
    st.subheader("3. Select Source and Target Languages/Frameworks")
    col_source_lang, col_target_lang = st.columns(2)
    with col_source_lang:
        source_language = st.selectbox(
            "Source Language:",
            options=list(LANGUAGE_OPTIONS.keys()),
            key="source_language_select",
            index=list(LANGUAGE_OPTIONS.keys()).index(st.session_state.selected_source_language)
        )
        st.session_state.selected_source_language = source_language
        source_framework = st.selectbox(
            "Source Framework/Version:",
            options=LANGUAGE_OPTIONS[source_language],
            key="source_framework_select",
            index=0 if st.session_state.selected_source_framework not in LANGUAGE_OPTIONS[source_language] else \
                    LANGUAGE_OPTIONS[source_language].index(st.session_state.selected_source_framework)
        )
        st.session_state.selected_source_framework = source_framework
    with col_target_lang:
        target_language = st.selectbox(
            "Target Language:",
            options=list(LANGUAGE_OPTIONS.keys()),
            key="target_language_select",
            index=list(LANGUAGE_OPTIONS.keys()).index(st.session_state.selected_target_language)
        )
        st.session_state.selected_target_language = target_language
        target_framework = st.selectbox(
            "Target Framework/Version:",
            options=LANGUAGE_OPTIONS[target_language],
            key="target_framework_select",
            index=0 if st.session_state.selected_target_framework not in LANGUAGE_OPTIONS[target_language] else \
                    LANGUAGE_OPTIONS[target_language].index(st.session_state.selected_target_framework)
        )
        st.session_state.selected_target_framework = target_framework
else:
    # Set placeholders/defaults if not in "Convert Language" mode
    source_language = ""
    source_framework = ""
    target_language = ""
    target_framework = ""

user_instructions = st.text_area(
    "Additional Instructions for AI (Optional):",
    placeholder="e.g., 'Make sure to include error handling', 'Use specific library X for Y task', 'Explain the changes in comments'",
    key="user_instructions_input"
)

if st.button("Generate/Convert Code", key="generate_code_button"):
    # Determine the actual conversion_type string to pass to the agent
    if conversion_operation == "Convert Language":
        conversion_type_agent = f"Convert: {source_language} ({source_framework}) to {target_language} ({target_framework})"
    elif conversion_operation == "Refactor Code":
        conversion_type_agent = "Refactor: Python (Improve Readability)" # Can be expanded to other languages
    elif conversion_operation == "Optimize Code":
        conversion_type_agent = "Optimize: Python (Performance)" # Can be expanded
    else: # "Generate Code"
        conversion_type_agent = "Generate Code"
    
    # Validate input based on operation
    if (conversion_operation != "Generate Code" and not original_code):
        st.error(f"Please enter some code to {conversion_operation.lower()}.")
    elif (conversion_operation == "Convert Language" and (not source_language or not target_language)):
        st.error("Please select both source and target languages/frameworks for conversion.")
    else:
        st.session_state.last_code_generation_details = None # Reset
        st.session_state.code_gen_metrics = {
            "confidence": 0.0, "effort": 0.0, "original_time": 0.0, "time_saved": 0.0
        } # Reset metrics
        with st.spinner("Generating code with AI... This may take a moment."):
            generated_code = st.session_state.code_gen_agent.generate_code(
                original_code=original_code if original_code else "User wants new code", # Provide a placeholder
                conversion_type=conversion_type_agent,
                user_instructions=user_instructions,
                temperature=ai_temperature # Pass temperature from slider
            )
            if generated_code.startswith("Error: "):
                st.error(generated_code)
                st.session_state.generated_code = ""
                st.session_state.conversion_successful = False
            else:
                st.session_state.generated_code = generated_code.strip('`').strip()
                st.session_state.original_code_for_flow = original_code if original_code else "Newly Generated Code Context"
                st.session_state.conversion_successful = True
                st.success("Code generation/conversion successful!")
                
                # Determine language for generated code for metrics and diff
                if conversion_operation == "Convert Language":
                    # Use target language for streamlit-code-diff display if converting
                    metrics_and_diff_lang = target_language 
                else:
                    # For refactor/optimize/generate, assume input language if not empty, else Python
                    metrics_and_diff_lang = source_language if source_language else "Python"
                
                # Determine language for original code metrics (use source language)
                original_code_lang_for_metrics = source_language if source_language else "Python"
                # Calculate and store metrics using the ragbits_integration functions
                confidence = get_confidence_score(st.session_state.generated_code, _get_code_ast_lang_from_display_lang(metrics_and_diff_lang))
                effort = get_effort_estimation(st.session_state.generated_code, _get_code_ast_lang_from_display_lang(metrics_and_diff_lang))
                
                code_for_original_time = original_code if original_code.strip() else "def placeholder(): pass"
                original_time = get_original_time_estimate(code_for_original_time, _get_code_ast_lang_from_display_lang(original_code_lang_for_metrics))
                time_saved = get_time_saved_estimate(original_time, effort)
                
                st.session_state.code_gen_metrics = {
                    "confidence": confidence,
                    "effort": effort,
                    "original_time": original_time,
                    "time_saved": time_saved
                }
                # Prepare generation details for optional Neo4j storage
                generation_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                
                # Dynamic flow_data for Neo4j lineage based on operation (conceptual flow for Code Gen still there)
                if conversion_operation == "Convert Language":
                    flow_data_for_neo4j = {
                        "nodes": [
                            {"id": f"source_{source_language.replace(' ', '_')}_{source_framework.replace(' ', '_')}", "label": f"{source_language} ({source_framework})", "type": "language_source"},
                            {"id": "ai_conversion_process", "label": "AI Conversion", "type": "process"},
                            {"id": f"target_{target_language.replace(' ', '_')}_{target_framework.replace(' ', '_')}", "label": f"{target_language} ({target_framework})", "type": "language_target"},
                        ],
                        "edges": [
                            {"source": f"source_{source_language.replace(' ', '_')}_{source_framework.replace(' ', '_')}", "target": "ai_conversion_process", "label": "input_to"},
                            {"source": "ai_conversion_process", "target": f"target_{target_language.replace(' ', '_')}_{target_framework.replace(' ', '_')}", "label": "output_to"}
                        ]
                    }
                else: # For Generate, Refactor, Optimize
                    flow_data_for_neo4j = {
                        "nodes": [
                            {"id": "user_input", "label": "User Input Code", "type": "code_input"},
                            {"id": "ai_process", "label": f"AI {conversion_operation}", "type": "process"},
                            {"id": "generated_output", "label": "Generated/Modified Code", "type": "code_output"}
                        ],
                        "edges": [
                            {"source": "user_input", "target": "ai_process", "label": "processed_by"} if original_code else {"source": "user_query", "target": "ai_process", "label": "guided_by_query"},
                            {"source": "ai_process", "target": "generated_output", "label": "produces"}
                        ]
                    }
                st.session_state.last_code_generation_details = {
                    "generation_id": generation_id,
                    "original_code": st.session_state.original_code_for_flow,
                    "generated_code": st.session_state.generated_code,
                    "timestamp": timestamp,
                    "flow_data": flow_data_for_neo4j,
                    "metrics": st.session_state.code_gen_metrics # Store metrics with generation details
                }
                st.info("Code generated. Click 'Save Code Generation to Neo4j' to persist this event.")

st.markdown("---")
st.subheader("4. Generated Code Preview")
if st.session_state.generated_code:
    # Use the selected target language for highlighting if converting, else try to infer from input or default to python
    if conversion_operation == "Convert Language":
        display_lang = SUPPORTED_GEN_CODE_EXTENSIONS.get(st.session_state.selected_target_language.lower(), "python")
    else:
        # Try to guess language from original code if available, else default to python
        input_lang_guess = st.session_state.original_code_for_flow.split('\n')[0].strip().replace('```', '') if st.session_state.original_code_for_flow.startswith('```') else ''
        if not input_lang_guess or input_lang_guess not in SUPPORTED_GEN_CODE_EXTENSIONS.values():
            input_lang_guess = "python" # Default if no hint or unknown
        display_lang = input_lang_guess
    st.code(st.session_state.generated_code, language=display_lang)
else:
    st.info("Generated code will appear here after conversion.")

# New: Display Metrics and Save Code Generation Event to Neo4j button
if st.session_state.code_gen_metrics["confidence"] > 0 or st.session_state.generated_code: # Only show if some metrics are calculated or code generated
    st.subheader("Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="AI Confidence", value=f"{st.session_state.code_gen_metrics['confidence']*100:.1f}%")
    with col2:
        st.metric(label="Estimated Refinement Effort (Hrs)", value=f"{st.session_state.code_gen_metrics['effort']:.2f}")
    with col3:
        st.metric(label="Original Dev Time (Hrs)", value=f"{st.session_state.code_gen_metrics['original_time']:.2f}")
    with col4:
        st.metric(label="Time Saved (Hrs)", value=f"{st.session_state.code_gen_metrics['time_saved']:.2f}")

    st.markdown("##### Metrics Visualization")

    # --- AI Confidence Doughnut Chart (using ECharts) ---
    st.markdown("###### AI Confidence Score")
    confidence_value = st.session_state.code_gen_metrics['confidence'] * 100
    
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
            key="confidence_echart" # key is supported in st_echarts
        )
    except Exception as e:
        st.error(f"Error rendering AI Confidence chart with ECharts: {e}")

    # --- Estimated Refinement Effort Bar Chart (using ECharts) ---
    st.markdown("###### Estimated Refinement Effort")
    effort_value = st.session_state.code_gen_metrics['effort']
    
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
            key="effort_echart"
        )
    except Exception as e:
        st.error(f"Error rendering Estimated Refinement Effort chart with ECharts: {e}")

    # --- Original Dev Time & Time Saved Bar Chart (using ECharts) ---
    st.markdown("###### Original Development Time vs. Time Saved")
    original_time_value = st.session_state.code_gen_metrics['original_time']
    time_saved_value = st.session_state.code_gen_metrics['time_saved']
    
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
            key="time_metrics_echart"
        )
    except Exception as e:
        st.error(f"Error rendering Time Metrics chart with ECharts: {e}")

if st.session_state.last_code_generation_details:
    if st.button("Save Code Generation to Neo4j", key="save_code_gen_neo4j_button"):
        with st.spinner("Saving code generation event to Neo4j..."):
            details = st.session_state.last_code_generation_details
            if st.session_state.neo4j_handler.store_code_generation_with_lineage(
                details["generation_id"],
                details["original_code"],
                details["generated_code"],
                details["timestamp"],
                details["flow_data"],
                details["metrics"] # Pass metrics to Neo4j handler
            ):
                st.success("Code generation event saved to Neo4j!")
            else:
                st.error("Failed to save code generation event to Neo4j.")
            st.session_state.last_code_generation_details = None # Clear after saving or attempting

# NEW: Code Difference Analysis Section (using streamlit-code-diff)
st.markdown("---")
st.subheader("5. Code Difference Analysis")
# Determine language for streamlit-code-diff
diff_lang_for_display = "plaintext"
if conversion_operation == "Convert Language":
    diff_lang_for_display = _get_streamlit_code_diff_lang(target_language)
else:
    diff_lang_for_display = _get_code_ast_lang_from_display_lang(source_language if source_language else "Python") # Using _get_code_ast_lang_from_display_lang here as it's more comprehensive for code-ast

if st.session_state.original_code.strip() or st.session_state.generated_code.strip():
    try:
        st_code_diff(
            old_string=st.session_state.original_code,
            new_string=st.session_state.generated_code,
            language=diff_lang_for_display,
            output_format="side-by-side", # or "line-by-line"
            diff_style="word",
            height="500px", # Set a fixed height for consistency
            key="code_diff_component" # Unique key for the component
        )
        if not st.session_state.original_code.strip() and not st.session_state.generated_code.strip():
             st.info("No code to compare.")
    except Exception as e:
        st.error(f"Error displaying code diff: {e}")
        st.info("The `streamlit-code-diff` component encountered an issue. Ensure the language selected is supported or try with 'plaintext'.")
else:
    st.info("Generate code to see a visual difference analysis.")