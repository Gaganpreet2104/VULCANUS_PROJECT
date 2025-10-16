# ✨ AI Code Generator & Analyzer
## Project Overview
The "AI Code Generator & Analyzer" is a production-level application designed to assist developers and data professionals with various code and data-related tasks. Built with a robust Streamlit-Python-JavaScript stack, Neo4j for graph data, and integrated with Google Gemini for AI capabilities, this application aims to streamline coding workflows, facilitate data analysis, provide insightful code/data flow visualizations, and now, generate UI wireframes.

The project is being developed through a step-by-step iterative process, ensuring stability and robust feature implementation.

## Current Features (Up to Iteration 3)
This section outlines the functionalities implemented so far:

### Iteration 1: Core Functionality & Basic AI
*   **Code Generation & Conversion:**
    *   Generate new code snippets based on user queries.
    *   Convert code between different programming languages (e.g., Python to JavaScript, Java, C#).
    *   Refactor and optimize existing Python code.
    *   Preview both the original and AI-generated/converted code side-by-side.
*   **Code Flow Mapping (Simplified):**
    *   Automatically analyze user-provided Python code (using AST) to extract function/class call relationships.
    *   Generate a JSON representation of the code's flow.
    *   **Note:** Direct JSON Crack integration has been removed. Users can manually copy JSON data.
*   **Data Analysis & Charting:**
    *   Upload CSV and XLSX files.
    *   Display uploaded data's head and column names.
    *   Query the AI (Google Gemini) with natural language to generate Python code for charts.
    *   Render dynamic charts using `streamlit_echarts5` (ECharts) based on AI-generated code.
*   **AI Performance Metrics (Mocked):**
    *   Display a "Confidence Score" and "Effort Estimation" for generated code. These metrics are currently mocked using the *concept* of Ragbits' unit test functionality, visualized with ECharts.
*   **Database Integration (Neo4j):**
    *   Store metadata about code generation events (original code, generated code, flow data) in a Neo4j graph database.
*   **User Interface (UI/UX):**
    *   Glassmorphic design theme with modern, minimal CSS-based background animations.
    *   Simple, placeholder authentication system (hardcoded credentials).

### Iteration 2: Enhanced AI & New Capabilities
*   **Enhanced Code Generation:**
    *   Added specific options for "Refactor: Python (Improve Readability)" and "Optimize: Python (Performance)".
    *   **AI Agent Persona:** Introduced a conceptual agent persona selection ("Senior Engineer", "Performance Expert", "Junior Coder") to influence the AI's code generation style and focus.
    *   **AI Creativity Control:** A slider to adjust the AI's `temperature` for code generation.
*   **Document Processing (Docling Concept):**
    *   New dedicated page to upload TXT and PDF documents.
    *   Extract text content from uploaded documents.
    *   Query the AI (Google Gemini) about the content of the uploaded document (basic RAG concept using LanceDB).
*   **Diagram Generation (Mermaid, PlantUML, Graphviz DOT):**
    *   **New dedicated page (`4_Project_Flow_Mapper.py`)**: Describe a data or process flow in natural language. The AI generates the corresponding diagram definition (Mermaid, PlantUML, or Graphviz DOT).
    *   **On Data Analysis page (`2_Data_Analysis.py`)**: Describe data entities for AI to generate Mermaid ERD syntax.
    *   All these diagrams are rendered directly within the Streamlit UI using the `diagram-renderer` library (via a local wrapper).
    *   All rendered diagrams include an **in-built button to download them as PNG images**.
*   **Cloud Code Converter:**
    *   New dedicated page (`5_Cloud_Code_Converter.py`) to convert code/configuration between cloud platforms/services (e.g., AWS Lambda Python to Azure Functions C#).
    *   Upload a code file, define source/target platforms/versions, and add instructions.
    *   Preview converted code with diff and associated metrics.
    *   Save conversion events to Neo4j.
*   **AI-Assisted Data Transformations:**
    *   On the Data Analysis page, users can now ask AI to suggest data transformations based on loaded data.
    *   Users can then describe a transformation, and the AI will generate and execute Polars Python code to apply it.
    *   Preview of original and transformed data.
    *   Save transformation events to Neo4j.
*   **Enhanced User Authentication & Management:**
    *   New user registration functionality.
    *   Admin approval system for new user accounts.
    *   Password policy validation for registration.
    *   `passlib` for secure password hashing.

### Iteration 3: AI Wireframe UI Generator
*   **AI-Driven Wireframe Generation:**
    *   New dedicated page (`6_Wireframe_Gen.py`).
    *   Users provide a natural language description of the desired UI.
    *   AI (Google Gemini) generates code in a custom lightweight markup language called **MukuroL**.
    *   **MukuroL Compiler:** A custom Python compiler (`src/utils/mukuro_compiler.py`) parses the MukuroL code and translates it into a self-contained HTML/CSS wireframe.
    *   **Live Preview:** The generated MukuroL code is displayed, and the compiled HTML wireframe is rendered directly within the Streamlit UI using `st.components.v1.html`.
    *   **Neo4j Integration:** Store wireframe generation events (description, MukuroL code) in Neo4j for auditing and tracking.
    *   **Wireframe Aesthetic:** The rendered wireframes have a distinct sketch-like, monochromatic appearance.

## Tech Stack
*   **Backend & Web Framework:** Python, Streamlit
*   **AI/LLM:** Google Gemini API (`google-generativeai`), Ollama Embeddings (`litellm`)
*   **Database:** Neo4j (`neo4j` Python driver)
*   **Charting:** `streamlit_echarts5` (Streamlit component for Apache ECharts)
*   **Vector Database:** `LanceDB`
*   **Data Handling:** `pandas`, `openpyxl` (for CSV/XLSX), `pypdf` (for PDF text extraction), `polars` (for efficient data manipulation)
*   **Environment Management:** `python-dotenv`
*   **Code Analysis:** `ast` (Python's Abstract Syntax Trees), `code-ast` (for language-agnostic AST/CST)
*   **Diagrams (Generation/Rendering):**
    *   `diagram-renderer`: A comprehensive library supporting Mermaid, PlantUML, and Graphviz diagrams. All rendering is self-contained.
    *   `tiktoken` (for token-aware text chunking)
*   **Code Difference Visualization:** `streamlit-code-diff`
*   **Authentication:** `passlib`, `streamlit-cookies-controller`
*   **Custom UI Markup:** MukuroL (custom language for wireframes) and its Python compiler.
*   **Package Managers:** `pip` (Python)
*   **UI/UX:** HTML/CSS (for glassmorphism and animations), Streamlit's native components, Google Fonts (`Press Start 2P`).

## Project Structure

Vulcan_X/
├── .env # Environment variables (API keys, DB creds)
├── requirements.txt # Python dependencies
├── src/ # Main application source code
│ ├── init.py # Makes 'src' a Python package
│ ├── assets/
│ │ ├── css/
│ │ │ └── style.css # Future custom CSS (currently integrated in ui_styles.py)
│ │ └── js/
│ │ └── animations.js # Future custom JS (e.g., Framer Motion integration)
│ ├── components/
│ │ ├── init.py # Makes 'components' a Python package
│ │ ├── apex_charts_component.py # Placeholder for custom ApexCharts component (using streamlit_echarts5 now)
│ │ ├── ui_styles.py # Custom CSS injection for glassmorphism and animations
│ │ └── streamlit_diagram.py # Wrapper for diagram-renderer Streamlit component
│ ├── core/
│ │ ├── init.py # Makes 'core' a Python package
│ │ ├── llm.py # Google Gemini API interaction and prompt engineering
│ │ ├── code_processor.py # Code AST analysis
│ │ ├── data_handler.py # CSV/XLSX/PDF/TXT file loading and processing
│ │ ├── ragbits_integration.py # Mocked confidence score and effort estimation
│ │ └── neo44j_handler.py # Neo4j database connection and operations
│ ├── lancedb_data/ # Directory for LanceDB vector store
│ ├── main.py # Main Streamlit application entry point (login, multi-page setup)
│ ├── pages/
│ │ ├── 1_Code_Gen.py # Code Generation & Conversion page
│ │ ├── 2_Data_Analysis.py # Data Analysis & Charting page
│ │ ├── 3_Document_Processor.py # Document Upload & Query page
│ │ ├── 4_Project_Flow_Mapper.py # Project Flow Diagram generation page
│ │ ├── 5_Cloud_Code_Converter.py # Cloud Code Conversion page
│ │ ├── 6_Wireframe_Gen.py # NEW: AI Wireframe UI Generation page
│ │ └── init.py # Makes 'pages' a Python package
│ └── utils/
│ ├── init.py # Makes 'utils' a Python package
│ ├── auth.py # Simple authentication logic
│ ├── helper.py # General utility functions
│ └── mukuro_compiler.py # NEW: MukuroL to HTML Compiler
└── test_I.csv # Sample data file for testing (optional)