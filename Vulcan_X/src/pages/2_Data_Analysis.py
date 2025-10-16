# pages/2_Data_Analysis.py
import streamlit as st
import pandas as pd
from streamlit_echarts5 import st_echarts # CHANGED: Import st_echarts
import uuid
import json
import io # Added for multi-file upload processing
import re # Import re for regex operations in generated code
import numpy as np # Import numpy
import warnings # Import warnings module
import polars as pl # NEW: Import polars
from core.data_handler import load_data_from_upload, extract_text_from_document
from core.llm import generate_chart_code_with_ragbits, get_ragbits_llm_client, generate_er_diagram_code, generate_er_diagram_for_multiple_dfs, suggest_data_transformations_prompt, generate_transformation_code_prompt
from core.ragbits_integration import get_confidence_score, get_effort_estimation # Metrics are mock/heuristic here, not directly tied to AST
from core.neo4j_handler import Neo4jHandler
from datetime import datetime
from components.streamlit_diagram import StreamlitDiagramRenderer
import asyncio
from components.ui_styles import apply_custom_styles

# NEW: Page Configuration with icon
st.set_page_config(
    page_title="Data Analysis & Charting",
    page_icon="📊", # Icon for Data Analysis page
    layout="wide"
)

# Apply custom glassmorphic and animation styles (MUST be called on every page)
apply_custom_styles()

# Ensure authentication state is set
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.warning("Please log in to access this page.")
    st.stop()

st.header("Data Analysis & Charting")
st.markdown("---")

# Initialize Neo4j Handler (once per session)
if "neo4j_handler_da" not in st.session_state:
    st.session_state.neo4j_handler_da = Neo4jHandler()
# Initialize LLM client (once per session)
if "ragbits_llm_da" not in st.session_state:
    st.session_state.ragbits_llm_da = get_ragbits_llm_client()
# Initialize StreamlitDiagramRenderer (once per session)
if "diagram_renderer_da" not in st.session_state:
    st.session_state.diagram_renderer_da = StreamlitDiagramRenderer()

# Initialize session state variables
if "uploaded_files_info" not in st.session_state: # Stores (filename, size) tuples
    st.session_state.uploaded_files_info = []
if "uploaded_dfs" not in st.session_state: # Stores {'filename': df} -- now stores Polars DFs
    st.session_state.uploaded_dfs = {}
if "selected_df_name" not in st.session_state:
    st.session_state.selected_df_name = None
if "df" not in st.session_state: # Current selected/active DataFrame -- now stores Polars DF
    st.session_state.df = None
if "generated_chart_code" not in st.session_state:
    st.session_state.generated_chart_code = ""
if "last_chart_query" not in st.session_state:
    st.session_state.last_chart_query = ""
if "last_chart_generation_details" not in st.session_state:
    st.session_state.last_chart_generation_details = None
if "er_diagram_description" not in st.session_state:
    st.session_state.er_diagram_description = ""
if "er_mermaid_code" not in st.session_state:
    st.session_state.er_mermaid_code = ""
if "last_er_diagram_details" not in st.session_state:
    st.session_state.last_er_diagram_details = None
if "multi_df_er_description" not in st.session_state:
    st.session_state.multi_df_er_description = ""
if "multi_df_er_mermaid_code" not in st.session_state:
    st.session_state.multi_df_er_mermaid_code = ""
if "suggested_transformations" not in st.session_state:
    st.session_state.suggested_transformations = ""
if "transformation_code" not in st.session_state:
    st.session_state.transformation_code = ""
if "transformation_applied_df" not in st.session_state:
    st.session_state.transformation_applied_df = None
if "transformation_original_df_preview" not in st.session_state:
    st.session_state.transformation_original_df_preview = None # Store preview of DF BEFORE transformation
if "transformation_details" not in st.session_state:
    st.session_state.transformation_details = None

st.subheader("1. Upload Your Data (CSV or XLSX)")
uploaded_files = st.file_uploader(
    "Choose CSV or XLSX files (multiple files can be uploaded)",
    type=["csv", "xlsx"],
    accept_multiple_files=True,
    key="data_uploader_multiple"
)

# Process uploaded files
if uploaded_files:
    current_files_info = [(f.name, f.size) for f in uploaded_files]
    if current_files_info != st.session_state.uploaded_files_info:
        st.session_state.uploaded_files_info = current_files_info
        st.session_state.uploaded_dfs = {}
        st.session_state.selected_df_name = None
        st.session_state.df = None # Reset current DF selection
        st.session_state.generated_chart_code = ""
        st.session_state.last_chart_query = ""
        st.session_state.last_chart_generation_details = None
        st.session_state.er_mermaid_code = ""
        st.session_state.last_er_diagram_details = None
        st.session_state.multi_df_er_mermaid_code = ""
        st.session_state.suggested_transformations = ""
        st.session_state.transformation_code = ""
        st.session_state.transformation_applied_df = None
        st.session_state.transformation_original_df_preview = None
        st.session_state.transformation_details = None
        
        with st.spinner("Loading uploaded dataframes..."):
            for uploaded_file in uploaded_files:
                df_loaded = load_data_from_upload(uploaded_file) # This now returns Polars DF
                if df_loaded is not None:
                    st.session_state.uploaded_dfs[uploaded_file.name] = df_loaded
            if st.session_state.uploaded_dfs:
                st.success(f"Successfully loaded {len(st.session_state.uploaded_dfs)} files.")
                # Set the first uploaded file as the default selected DF
                st.session_state.selected_df_name = list(st.session_state.uploaded_dfs.keys())[0]
                st.session_state.df = st.session_state.uploaded_dfs[st.session_state.selected_df_name]
                st.rerun() # Rerun to update selectbox and display
else:
    # If file uploader is empty, clear all related session states
    if st.session_state.uploaded_dfs:
        st.session_state.uploaded_files_info = []
        st.session_state.uploaded_dfs = {}
        st.session_state.selected_df_name = None
        st.session_state.df = None
        st.session_state.generated_chart_code = ""
        st.session_state.last_chart_query = ""
        st.session_state.last_chart_generation_details = None
        st.session_state.er_mermaid_code = ""
        st.session_state.last_er_diagram_details = None
        st.session_state.multi_df_er_mermaid_code = ""
        st.session_state.suggested_transformations = ""
        st.session_state.transformation_code = ""
        st.session_state.transformation_applied_df = None
        st.session_state.transformation_original_df_preview = None
        st.session_state.transformation_details = None
        st.info("Upload CSV or XLSX files to begin data analysis.")
        st.rerun() # Rerun to clear displayed data

# Display list of uploaded files and allow selection
if st.session_state.uploaded_dfs:
    st.subheader("Loaded DataFrames")
    df_names = list(st.session_state.uploaded_dfs.keys())
    selected_df_name = st.selectbox("Select DataFrame to work with:", df_names, key="df_selector")
    if selected_df_name != st.session_state.selected_df_name:
        st.session_state.selected_df_name = selected_df_name
        st.session_state.df = st.session_state.uploaded_dfs[selected_df_name]
        st.session_state.generated_chart_code = "" # Clear chart on DF switch
        st.session_state.last_chart_query = ""
        st.session_state.transformation_code = "" # Clear transformation on DF switch
        st.session_state.transformation_applied_df = None
        st.session_state.transformation_original_df_preview = None
        st.session_state.transformation_details = None
        st.rerun()
    st.write(f"Currently viewing: **{st.session_state.selected_df_name}**")
    st.write(f"Columns: {', '.join(st.session_state.df.columns)}")
    # Display Polars DataFrame by converting to Pandas for st.dataframe
    st.dataframe(st.session_state.df.head().to_pandas()) 
    
    st.markdown("---") # Visual separator

    # --- Single File ER Diagram ---
    st.subheader("2. Entity-Relationship (ER) Diagrams for single file")
    st.info("Describe your data entities and their relationships. AI will generate a Mermaid ERD syntax, which is rendered visually by `diagram-renderer` and includes a PNG download option.")
    # Convert Polars columns to list for prompt
    er_diagram_description_sample = f"Analyze the schema of the DataFrame '{st.session_state.selected_df_name}' with columns {st.session_state.df.columns} and infer an ER Diagram. Assume primary keys for ID columns if present, e.g., 'id', 'user_id', 'product_id'."
    er_diagram_description = st.text_area(
        "Describe your ER Diagram for AI (e.g., 'Product has productId (PK), name, price. Order has orderId (PK), productId (FK).'):",
        value=st.session_state.er_diagram_description if st.session_state.er_diagram_description else er_diagram_description_sample,
        height=150,
        key="ai_er_diagram_description_input"
    )
    st.session_state.er_diagram_description = er_diagram_description
    if st.button("Generate AI ER Diagram (Single File)", key="generate_ai_er_diagram_button", disabled=not er_diagram_description.strip()):
        st.session_state.last_er_diagram_details = None
        with st.spinner("Generating AI ER diagram code..."):
            try:
                er_mermaid_code = asyncio.run(generate_er_diagram_code(er_diagram_description))
                if not er_mermaid_code.strip().startswith("erDiagram"):
                    # Attempt to extract if wrapped in markdown code block
                    if "```mermaid" in er_mermaid_code:
                        er_mermaid_code = er_mermaid_code.split("```mermaid")[1].split("```")[0].strip()
                    elif "```" in er_mermaid_code: # Fallback for generic code block
                         er_mermaid_code = er_mermaid_code.split("```")[1].split("```")[0].strip()
                    # After extraction, ensure it starts correctly for rendering, otherwise warn
                    if not er_mermaid_code.strip().startswith("erDiagram"):
                        st.warning("AI did not return a valid Mermaid ERD starting with 'erDiagram'. Attempting to render anyway, but results may vary. Check the generated code format.")
                st.session_state.er_mermaid_code = er_mermaid_code
                st.success("AI ER Diagram code generated!")
                event_id_er = str(uuid.uuid4())
                timestamp_er = datetime.now().isoformat()
                st.session_state.last_er_diagram_details = {
                    "event_id": event_id_er,
                    "description": er_diagram_description,
                    "mermaid_code": er_mermaid_code,
                    "timestamp": timestamp_er
                }
                st.info("ER Diagram generated. Click 'Save ER Diagram to Neo4j' to persist this event.")
            except Exception as e:
                st.error(f"Error generating AI ER diagram code: {e}")
                st.session_state.er_mermaid_code = ""
    if st.session_state.er_mermaid_code:
        st.subheader("Generated AI ER Diagram Code Preview")
        st.code(st.session_state.er_mermaid_code, language="mermaid")
        st.subheader("Rendered AI ER Diagram")
        try:
            success = st.session_state.diagram_renderer_da.render_diagram_auto(
                st.session_state.er_mermaid_code,
                height=400,
            )
            if not success:
                st.warning("Diagram could not be rendered. Please check the code above for syntax errors.")
        except Exception as e:
            st.error(f"Error rendering AI ER Diagram with diagram-renderer: {e}")
            st.info("Make sure 'diagram-renderer' is installed correctly and your Mermaid code is valid.")
        def save_er_diagram_to_neo4j():
            if st.session_state.last_er_diagram_details:
                with st.spinner("Saving ER diagram details to Neo4j..."):
                    details = st.session_state.last_er_diagram_details
                    if st.session_state.neo4j_handler_da.store_project_flow_event(
                        details["event_id"],
                        details["description"],
                        details["mermaid_code"],
                        {"nodes": [], "edges": []},
                        details["timestamp"],
                        "Mermaid (ER Diagram)"
                    ):
                        st.success("AI ER Diagram details saved to Neo4j!")
                    else:
                        st.error("Failed to save AI ER Diagram details to Neo4j.")
                    st.session_state.last_er_diagram_details = None
            st.rerun()
        if st.session_state.last_er_diagram_details:
            st.button("Save AI ER Diagram to Neo4j", key="save_ai_er_neo4j_button", on_click=save_er_diagram_to_neo4j)

    st.markdown("---")
    
    # --- Chart Generation ---
    st.subheader("3. Query AI to Generate Chart") # Subheader number changed
    user_query_chart = st.text_area(
        "Describe the chart you want to generate (e.g., 'Show total sales by product as a bar chart'):",
        value=st.session_state.last_chart_query,
        key="chart_query_input"
    )

    def get_dataframe_preview(df: pl.DataFrame) -> str: # Change type hint to pl.DataFrame
        if df is None or df.is_empty(): # Use .is_empty() for Polars
            return "DataFrame is empty or not loaded."
        preview = f"DataFrame Name: {st.session_state.selected_df_name}\n"
        preview += f"DataFrame Columns: {df.columns}\n" # Polars columns property is already a list of strings
        preview += "First 5 rows (CSV format):\n"
        preview += df.head(5).write_csv(file=None) # Polars equivalent of to_csv(index=False)
        return preview

    if st.button("Generate Chart", key="generate_chart_button", disabled=st.session_state.df is None):
        if user_query_chart:
            st.session_state.last_chart_query = user_query_chart
            st.session_state.last_chart_generation_details = None
            with st.spinner("Generating chart code..."):
                # Pass Pandas DataFrame preview to chart generation, as LLM is trained on Pandas structures
                data_preview_str = get_dataframe_preview(st.session_state.df)
                # The LLM will generate Python code defining 'options_dict' for ECharts
                chart_code_raw = generate_chart_code_with_ragbits(st.session_state.df.head().to_pandas().to_csv(index=False), user_query_chart)
                
                # Extract code if wrapped in markdown
                if "```python" in chart_code_raw:
                    chart_code = chart_code_raw.split("```python")[1].split("```")[0].strip()
                elif "```" in chart_code_raw:
                    chart_code = chart_code_raw.split("```")[1].split("```")[0].strip()
                else:
                    chart_code = chart_code_raw.strip()
                
                if chart_code.startswith("Error: "):
                    st.error(chart_code)
                    st.session_state.generated_chart_code = ""
                else:
                    st.session_state.generated_chart_code = chart_code
                    st.success("Chart code generated successfully!")
                    event_id = str(uuid.uuid4())
                    timestamp = datetime.now().isoformat()
                    st.session_state.last_chart_generation_details = {
                        "event_id": event_id,
                        "query": user_query_chart,
                        "generated_code": chart_code,
                        "data_preview": data_preview_str,
                        "timestamp": timestamp
                    }
                    st.info("Chart code generated. Click 'Save Chart Details to Neo4j' to persist this event.")
        else:
            st.warning("Please enter a query to generate a chart.")

    if st.session_state.generated_chart_code:
        st.subheader("Generated Chart Code Preview")
        with st.expander("Click to view generated code"):
            st.code(st.session_state.generated_chart_code, language="python")
        
        st.subheader("Generated Chart")
        if st.session_state.df is None:
            st.error("Cannot render chart: No data DataFrame loaded in session state. Please upload a CSV or XLSX file first.")
            st.session_state.generated_chart_code = ""
            st.session_state.last_chart_query = ""
        else:
            try:
                exec_globals = {
                    '__builtins__': __builtins__,
                    'pd': pd,
                    'df': st.session_state.df.to_pandas(), # Pass Pandas DataFrame for LLM's exec context
                }
                exec_locals = {}
                
                # The AI-generated code will now define 'options_dict'
                exec(st.session_state.generated_chart_code, exec_globals, exec_locals)
                
                echarts_options = exec_locals.get('options_dict') # Get the ECharts options
                
                if echarts_options:
                    st_echarts(
                        options=echarts_options,
                        height="400px", # Use a fixed height for ECharts
                        width="100%",  # Use 100% width
                        key="ai_generated_echart" # Use a unique key
                    )
                else:
                    st.error("AI-generated code did not produce a valid `options_dict` variable for `streamlit-echarts5`.")
                    st.info("Please instruct the AI to define `options_dict` (a dictionary) in its output.")
            except Exception as e:
                st.error(f"Error executing chart code: {e}")
                st.error("Please refine your query or check the generated code for issues.")
                st.code(str(e), language="text")
    else:
        st.info("A chart will appear here after you generate the chart code.")

    def save_chart_details_to_neo4j():
        if st.session_state.last_chart_generation_details:
            with st.spinner("Saving chart generation event to Neo4j..."):
                details = st.session_state.last_chart_generation_details
                if st.session_state.neo4j_handler_da.store_chart_event(
                    details["event_id"],
                    details["query"],
                    details["generated_code"],
                    details["data_preview"],
                    details["timestamp"]
                ):
                    st.success("Chart generation event saved to Neo4j!")
                else:
                    st.error("Failed to save chart generation event to Neo4j.")
                st.session_state.last_chart_generation_details = None
            st.rerun()
    if st.session_state.last_chart_generation_details:
        st.button("Save Chart Details to Neo4j", key="save_chart_neo4j_button", on_click=save_chart_details_to_neo4j)

    st.markdown("---")
    
    # --- Multi-File ER Diagram ---
    if len(st.session_state.uploaded_dfs) > 1:
        st.subheader("4. Entity-Relationship (ER) Diagram for Multiple Files") # Subheader number changed
        st.info("Describe the relationships between your uploaded DataFrames. AI will infer schemas and generate a Mermaid ERD.")
        # Pass Polars columns to list for prompt
        all_df_schemas = {name: df.columns for name, df in st.session_state.uploaded_dfs.items()}
        multi_df_er_description_sample = f"Generate an ER Diagram for the following DataFrames and infer relationships: {json.dumps(all_df_schemas, indent=2)}. Focus on common ID columns to link them."
        multi_df_er_description = st.text_area(
            "Describe your ER Diagram for AI (e.g., 'Link products.csv and orders.csv on product_id'):",
            value=st.session_state.multi_df_er_description if st.session_state.multi_df_er_description else multi_df_er_description_sample,
            height=150,
            key="multi_df_er_description_input"
        )
        st.session_state.multi_df_er_description = multi_df_er_description
        if st.button("Generate AI ER Diagram (Multiple Files)", key="generate_multi_df_er_diagram_button", disabled=not multi_df_er_description.strip()):
            with st.spinner("Generating AI ER diagram for multiple files..."):
                try:
                    df_schemas_str = json.dumps(all_df_schemas)
                    multi_df_er_mermaid_code = asyncio.run(generate_er_diagram_for_multiple_dfs(multi_df_er_description, df_schemas_str))
                    if not multi_df_er_mermaid_code.strip().startswith("erDiagram"):
                        if "```mermaid" in multi_df_er_mermaid_code:
                            multi_df_er_mermaid_code = multi_df_er_mermaid_code.split("```mermaid")[1].split("```")[0].strip()
                        elif "```" in multi_df_er_mermaid_code:
                            multi_df_er_mermaid_code = multi_df_er_mermaid_code.split("```")[1].split("```")[0].strip()
                        if not multi_df_er_mermaid_code.strip().startswith("erDiagram"):
                            st.warning("AI did not return a valid Mermaid ERD starting with 'erDiagram'. Attempting to render anyway, but results may vary. Check the generated code format.")
                    st.session_state.multi_df_er_mermaid_code = multi_df_er_mermaid_code
                    st.success("AI ER Diagram for multiple files generated!")
                except Exception as e:
                    st.error(f"Error generating AI ER diagram for multiple files: {e}")
                    st.session_state.multi_df_er_mermaid_code = ""
        if st.session_state.multi_df_er_mermaid_code:
            st.subheader("Generated Multi-File ER Diagram Code Preview")
            st.code(st.session_state.multi_df_er_mermaid_code, language="mermaid")
            st.subheader("Rendered Multi-File ER Diagram")
            try:
                success = st.session_state.diagram_renderer_da.render_diagram_auto(
                    st.session_state.multi_df_er_mermaid_code,
                    height=500,
                )
                if not success:
                    st.warning("Diagram could not be rendered. Please check the code above for syntax errors.")
            except Exception as e:
                st.error(f"Error rendering AI ER Diagram with diagram-renderer: {e}")
                st.info("Make sure 'diagram-renderer' is installed correctly and your Mermaid code is valid.")
    else:
        st.info("Upload multiple CSV or XLSX files to enable multi-file ER Diagram generation.")

    st.markdown("---")

    # --- AI-Assisted Data Transformations ---
    st.subheader("5. AI-Assisted Data Transformations") # Subheader number changed
    st.markdown(
        """
        Use AI to suggest and apply data transformations.
        **Note on Annotations:** The `annotate-transform` library is designed for JAX array shape validation.
        Here, the AI will provide a *conceptual* `(Input Shape) -> (Output Output)` annotation for clarity of data flow,
        but `annotate-transform` is not used for runtime validation of pandas DataFrames.
        """
    )
    col_suggest, col_apply = st.columns(2)
    with col_suggest:
        if st.button("Suggest Transformations", key="suggest_transforms_button", disabled=st.session_state.df is None):
            st.session_state.suggested_transformations = "" # Reset
            with st.spinner("Asking AI for transformation suggestions..."):
                current_df_preview = get_dataframe_preview(st.session_state.df) # Now returns Polars CSV preview
                suggestions_raw = asyncio.run(suggest_data_transformations_prompt(current_df_preview))
                if "```" in suggestions_raw: # Extract if markdown
                    suggestions = suggestions_raw.split("```")[1].strip()
                else:
                    suggestions = suggestions_raw.strip()
                st.session_state.suggested_transformations = suggestions
        if st.session_state.suggested_transformations:
            st.info("**AI Suggestions:**")
            st.markdown(st.session_state.suggested_transformations)
        else:
            st.info("Click 'Suggest Transformations' to get AI ideas.")
    with col_apply:
        transform_description = st.text_area(
            "Describe the transformation you want to apply:",
            placeholder="e.g., 'Group by Region and sum Sales', 'Merge with orders_df on ProductID', 'Filter where Age > 30'",
            height=100,
            key="transform_description_input",
            disabled=st.session_state.df is None
        )
        if st.button("Apply Transformation", key="apply_transform_button", disabled=not transform_description.strip()):
            st.session_state.transformation_code = "" # Reset
            st.session_state.transformation_applied_df = None
            st.session_state.transformation_original_df_preview = None
            st.session_state.transformation_details = None
            with st.spinner("Generating and applying transformation code..."):
                current_df_preview = get_dataframe_preview(st.session_state.df) # Now returns Polars CSV preview
                # Pass a Pandas DataFrame preview to the LLM, as it's trained on Pandas conventions
                # The LLM will convert it to Polars internally in its generated code.
                current_pandas_df_preview_for_llm = st.session_state.df.head().to_pandas().to_csv(index=False)
                all_df_schemas = {name: df.columns for name, df in st.session_state.uploaded_dfs.items()} # Polars columns property
                
                transform_details_raw = asyncio.run(generate_transformation_code_prompt(
                    current_pandas_df_preview_for_llm, # Pass Pandas preview for LLM's understanding
                    transform_description,
                    json.dumps(all_df_schemas) # Pass all available schemas (Polars columns)
                ))
                # Expected format: JSON with "code": [...], "annotation": "", "description": ""
                try:
                    # Extraction logic for JSON from markdown block (more robust)
                    json_str_to_parse = transform_details_raw.strip()
                    start_idx = -1
                    if "```json" in json_str_to_parse:
                        start_idx = json_str_to_parse.find("```json") + len("```json")
                    elif "```" in json_str_to_parse:
                        start_idx = json_str_to_parse.find("```") + len("```")
                    
                    end_idx = json_str_to_parse.rfind("```")
                    
                    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                        json_content = json_str_to_parse[start_idx:end_idx].strip()
                        # Some LLMs might add extra stuff like `json` or `python`
                        # in the content itself after the initial ```. Remove if present.
                        if json_content.startswith("json"):
                            json_content = json_content[len("json"):].strip()
                        elif json_content.startswith("python"):
                             json_content = json_content[len("python"):].strip()
                        
                        transform_output = json.loads(json_content)
                    else:
                        st.error(f"AI response did not contain a valid JSON markdown block (```json...``` or ```...```). Raw output: {transform_details_raw}")
                        generated_code = ""
                        conceptual_annotation = "N/A -> N/A"
                        transform_long_description = transform_description
                        # Raise an error to fall through to the general exception handling
                        raise json.JSONDecodeError("Invalid JSON block structure from AI", transform_details_raw, 0)
                    
                    # Handle `code` as a list of strings OR fall back to single string
                    generated_code_list = transform_output.get("code", [])
                    if isinstance(generated_code_list, list):
                        generated_code = "\n".join(generated_code_list)
                    else: # Fallback if AI doesn't return a list, try to use it directly as a string
                        generated_code = str(generated_code_list).strip()
                        st.warning("AI did not return 'code' as a list of strings. Attempting to parse as single string.")
                    
                    conceptual_annotation = transform_output.get("annotation", "N/A -> N/A")
                    transform_long_description = transform_output.get("description", transform_description)
                except json.JSONDecodeError as e:
                    st.error(f"AI returned invalid JSON for transformation. Error: {e}. Raw output: {transform_details_raw}. Ensure AI returns valid JSON.")
                    generated_code = ""
                    conceptual_annotation = "N/A -> N/A"
                    transform_long_description = transform_description
                except Exception as e: # Catch any other unexpected errors during parsing/extraction
                    st.error(f"An unexpected error occurred during AI response parsing: {e}. Raw output: {transform_details_raw}")
                    generated_code = ""
                    conceptual_annotation = "N/A -> N/A"
                    transform_long_description = transform_description
                
                if generated_code:
                    st.session_state.transformation_original_df_preview = st.session_state.df.head(5).to_pandas() # Store Polars preview as Pandas
                    try:
                        # Convert the currently selected Polars DF to Pandas for the exec context.
                        # The AI's generated code will handle converting this df (Pandas) to Polars.
                        df_for_exec = st.session_state.df.clone().to_pandas() 
                        exec_transform_globals = {
                            '__builtins__': __builtins__,
                            'pd': pd,
                            'df': df_for_exec, # Pass Pandas DataFrame here for exec
                            're': re, 
                            'np': np,
                            'warnings': warnings,
                            'pl': pl # Pass Polars module to the execution scope
                        }
                        # Add other uploaded DFs (which are Polars) to the scope after converting to Pandas
                        for name, other_pl_df in st.session_state.uploaded_dfs.items():
                            var_name = name.replace('.', '_').replace('-', '_').replace(' ', '_').lower()
                            if var_name.endswith('_csv') or var_name.endswith('_xlsx'):
                                var_name = var_name[:-4] 
                            # Convert other Polars DFs to Pandas too, as the LLM is instructed to convert df (Pandas) to polars.
                            # This ensures all input DFs for AI's code are consistently Pandas initially.
                            if var_name not in exec_transform_globals:
                                exec_transform_globals[var_name] = other_pl_df.to_pandas() 
                        exec_transform_locals = exec_transform_globals 
                        exec(generated_code, exec_transform_globals, exec_transform_locals)
                        
                        # The transformed DataFrame from the AI's code is expected to be `transformed_df`.
                        # This `transformed_df` should be in Pandas format from the AI's code, so no further conversion needed here.
                        transformed_df_result_from_exec = exec_transform_locals.get('transformed_df')
                        
                        if isinstance(transformed_df_result_from_exec, pd.DataFrame):
                            st.session_state.transformation_applied_df = transformed_df_result_from_exec
                            st.session_state.transformation_code = generated_code
                            st.session_state.transformation_details = {
                                "original_df_name": st.session_state.selected_df_name,
                                "transform_description": transform_long_description,
                                "conceptual_annotation": conceptual_annotation,
                                "generated_code": generated_code,
                                "timestamp": datetime.now().isoformat()
                            }
                            st.success("Transformation applied successfully!")
                            st.info("Transformation details stored. Click 'Save Transformation to Neo4j' to persist this event.")
                        else:
                            st.error("AI-generated code did not produce a valid pandas DataFrame as `transformed_df`. Check the output variable name and its type.")
                            st.info("Ensure the AI's output assigns the resulting DataFrame to a variable named `transformed_df` and converts it to Pandas format (e.g., `.to_pandas()`) at the end.")
                            st.code(generated_code, language="python") # Show the code that failed
                            st.info(f"Type of transformed_df from AI: {type(transformed_df_result_from_exec)}")
                    except Exception as e:
                        st.error(f"Error executing transformation code: {e}")
                        st.code(generated_code, language="python")
                        st.error("Please refine your transformation description or check the generated code for issues. Full traceback above.")
                else:
                    st.error("AI failed to generate transformation code. Please try a different description.")

    if st.session_state.transformation_code:
        st.subheader("Generated Transformation Code")
        with st.expander("View Code & Annotation"):
            st.markdown(f"**Conceptual Annotation:** `{st.session_state.transformation_details['conceptual_annotation']}`")
            st.code(st.session_state.transformation_code, language="python")
        if st.session_state.transformation_applied_df is not None:
            st.subheader("Transformed Data Preview")
            col_orig, col_trans = st.columns(2)
            with col_orig:
                st.markdown(f"**Original Data ({st.session_state.selected_df_name}):**")
                # Original preview is already stored as Pandas
                st.dataframe(st.session_state.transformation_original_df_preview)
            with col_trans:
                st.markdown("**Transformed Data (First 5 Rows):**")
                st.dataframe(st.session_state.transformation_applied_df.head()) # Ensure this is Pandas
        def save_transformation_to_neo4j():
            if st.session_state.transformation_details:
                with st.spinner("Saving transformation event to Neo4j..."):
                    details = st.session_state.transformation_details
                    # Store transformation as a specialized project flow event
                    if st.session_state.neo4j_handler_da.store_project_flow_event(
                        str(uuid.uuid4()), # New event ID for transformation
                        details["transform_description"],
                        details["generated_code"],
                        {
                            "nodes": [
                                {"id": f"df_{details['original_df_name']}", "label": details['original_df_name'], "type": "DataFrame"},
                                {"id": f"transformation_op", "label": details['conceptual_annotation'], "type": "Transformation"},
                                {"id": f"df_transformed", "label": "Transformed DataFrame", "type": "DataFrame"}
                            ],
                            "edges": [
                                {"source": f"df_{details['original_df_name']}", "target": "transformation_op", "label": "input_to"},
                                {"source": "transformation_op", "target": "df_transformed", "label": "produces"}
                            ]
                        },
                        details["timestamp"],
                        "Data Transformation"
                    ):
                        st.success("Transformation event saved to Neo4j!")
                    else:
                        st.error("Failed to save transformation event to Neo4j.")
                    st.session_state.transformation_details = None
            st.rerun()
        if st.session_state.transformation_details:
            st.button("Save Transformation to Neo4j", key="save_transform_neo4j_button", on_click=save_transformation_to_neo4j)