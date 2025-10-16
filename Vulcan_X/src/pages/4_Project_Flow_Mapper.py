# pages/4_Project_Flow_Mapper.py
import streamlit as st
import json
import uuid
from datetime import datetime
from core.agents import RagbitsDataLineageAgent
from core.llm import get_ragbits_llm_client, generate_flow_diagram_code
from core.neo4j_handler import Neo4jHandler
from components.streamlit_diagram import StreamlitDiagramRenderer
import asyncio
from components.ui_styles import apply_custom_styles

# NEW: Page Configuration with icon
st.set_page_config(
    page_title="Project Flow Mapper",
    page_icon="🗺️", # Icon for Project Flow Mapper page
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
st.header("Project Flow Mapper") # Renamed header
st.markdown("---")
# Initialize LLM client (once per session)
if "ragbits_llm_flow" not in st.session_state:
    st.session_state.ragbits_llm_flow = get_ragbits_llm_client()
# Initialize Data Lineage Agent (once per session)
if "data_lineage_agent_flow" not in st.session_state:
    st.session_state.data_lineage_agent_flow = RagbitsDataLineageAgent(llm=st.session_state.ragbits_llm_flow) # Pass llm to the custom agent's init
# Initialize Neo4j Handler (once per session)
if "neo4j_handler_flow" not in st.session_state:
    st.session_state.neo4j_handler_flow = Neo4jHandler()
# Initialize StreamlitDiagramRenderer (once per session)
if "diagram_renderer_flow" not in st.session_state:
    st.session_state.diagram_renderer_flow = StreamlitDiagramRenderer()
# Session state for diagram definition and flow data
if "diagram_definition" not in st.session_state: # Renamed from mermaid_definition for generic use
    st.session_state.diagram_definition = ""
if "flow_diagram_data" not in st.session_state:
    st.session_state.flow_diagram_data = {"nodes": [], "edges": []}
# New session state for storing project flow details for Neo4j
if "last_project_flow_details" not in st.session_state:
    st.session_state.last_project_flow_details = None
# New session state for diagram type selection
if "selected_diagram_type" not in st.session_state:
    st.session_state.selected_diagram_type = "Mermaid (Flowchart)"
st.subheader("1. Describe Your Data/Process Flow")
sample_flow_description = """
User authenticates via OAuth.
Authentication service validates token.
If valid, user is granted access to Application API.
Application API requests data from Database.
Database returns data to Application API.
Application API returns response to User.
"""
flow_description = st.text_area(
    "Describe the data or process flow (e.g., 'Data flows from customer database to analytics service, then to reporting dashboard.' or paste code):",
    value=st.session_state.flow_description if "flow_description" in st.session_state and st.session_state.flow_description else sample_flow_description,
    height=200,
    key="flow_description_input"
)
st.session_state.flow_description = flow_description # Ensure session state reflects current input
# Select diagram type
selected_diagram_type = st.selectbox(
    "Select Diagram Type:",
    ["Mermaid (Flowchart)", "Mermaid (ER Diagram)", "PlantUML", "Graphviz DOT"],
    key="diagram_type_select"
)
st.session_state.selected_diagram_type = selected_diagram_type
# The button should be enabled if the text area is not empty (after stripping whitespace)
if st.button("Generate Flow Diagram", key="generate_flow_diagram_button", disabled=not flow_description.strip()):
    st.session_state.last_project_flow_details = None # Reset
    with st.spinner("Generating diagram definition..."):
        # The AI needs to generate syntax specific to the chosen diagram type
        diagram_syntax_type_for_llm = "" # What LLM should generate
        if selected_diagram_type == "Mermaid (Flowchart)":
            diagram_syntax_type_for_llm = "Mermaid flowchart"
        elif selected_diagram_type == "Mermaid (ER Diagram)":
            diagram_syntax_type_for_llm = "Mermaid ER Diagram"
        elif selected_diagram_type == "PlantUML":
            diagram_syntax_type_for_llm = "PlantUML"
        elif selected_diagram_type == "Graphviz DOT":
            diagram_syntax_type_for_llm = "Graphviz DOT"
        try:
            # Call the new async function for general flow diagram generation
            generated_diagram_code = asyncio.run(generate_flow_diagram_code(flow_description, diagram_syntax_type_for_llm))
            # For Mermaid Flowchart, we still analyze to extract nodes/edges for Neo4j
            if selected_diagram_type == "Mermaid (Flowchart)":
                extracted_lineage = st.session_state.data_lineage_agent_flow.extract_lineage(flow_description) # Use description for lineage
                st.session_state.flow_diagram_data = extracted_lineage
            else:
                st.session_state.flow_diagram_data = {"nodes": [], "edges": []} # No automatic JSON conversion for other types
            st.session_state.diagram_definition = generated_diagram_code # Store for display
            if generated_diagram_code: # Check if something was generated
                st.success(f"{selected_diagram_type} diagram definition generated!")
                # Prepare project flow details for optional Neo4j storage
                event_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                st.session_state.last_project_flow_details = {
                    "event_id": event_id,
                    "description": flow_description,
                    "diagram_type": selected_diagram_type, # Store chosen type
                    "generated_code": generated_diagram_code, # Store the generated syntax
                    "flow_data": st.session_state.flow_diagram_data, # Only for Mermaid Flowchart
                    "timestamp": timestamp
                }
                st.info(f"{selected_diagram_type} diagram definition generated. Click 'Save Diagram Details to Neo4j' to persist this event.")
            else:
                st.warning(f"Could not generate {selected_diagram_type} diagram from the description. AI returned empty output. Please refine your description or try a different type.")
        except Exception as e:
            st.error(f"Error generating diagram: {e}")
            st.session_state.diagram_definition = ""
st.markdown("---")
# Renamed from "Generated Mermaid.js Definition"
st.subheader(f"2. Generated {st.session_state.selected_diagram_type} Definition")
if st.session_state.diagram_definition:
    # Adjust language hint for st.code based on selected type
    code_display_lang = "text"
    if "Mermaid" in st.session_state.selected_diagram_type:
        code_display_lang = "mermaid"
    elif st.session_state.selected_diagram_type == "PlantUML":
        code_display_lang = "plantuml"
    elif st.session_state.selected_diagram_type == "Graphviz DOT":
        code_display_lang = "dot"
    st.code(st.session_state.diagram_definition, language=code_display_lang)
    st.subheader(f"3. Rendered {st.session_state.selected_diagram_type} Diagram")
    try:
        # Use diagram_renderer to render the diagram. It handles auto-detection.
        # It also includes zoom, pan, and PNG download buttons automatically
        success = st.session_state.diagram_renderer_flow.render_diagram_auto(
            st.session_state.diagram_definition,
            height=400, # Adjust height as needed
            # Removed 'key' argument here as it's not accepted by the wrapped components.html
        )
        if not success:
            st.warning("Diagram could not be rendered. Please check the code above for syntax errors.")
    except Exception as e:
        st.error(f"Error rendering {st.session_state.selected_diagram_type} Diagram with diagram-renderer: {e}")
        st.info("Make sure 'diagram-renderer' is installed correctly and your diagram code is valid.")
    st.markdown("---")
    st.subheader("4. Extracted Flow Data (JSON - for Mermaid Flowchart)")
    if st.session_state.selected_diagram_type == "Mermaid (Flowchart)" and st.session_state.flow_diagram_data:
        st.json(st.session_state.flow_diagram_data)
        st.markdown(
            """
            **Note:** JSON Crack integration has been removed from the UI.
            To visualize this JSON interactively with JSON Crack, you would typically:
            1.  Save the JSON above to a file (e.g., `flow_diagram.json`).
            2.  Go to a running JSON Crack instance (e.g., `http://localhost:3000` if you have it running locally).
            3.  Upload or paste the JSON content there.
            """
        )
    else:
        st.info("JSON flow data extraction is currently only available for Mermaid Flowcharts.")
    # New: Save Project Flow Diagram Event to Neo4j button
    def save_flow_diagram_to_neo4j():
        if st.session_state.last_project_flow_details:
            with st.spinner("Saving project flow diagram details to Neo4j..."):
                details = st.session_state.last_project_flow_details
                if st.session_state.neo4j_handler_flow.store_project_flow_event(
                    details["event_id"],
                    details["description"],
                    details["generated_code"], # Store the raw generated code
                    details["flow_data"],
                    details["timestamp"],
                    details["diagram_type"] # Pass the diagram type
                ):
                    st.success("Project flow diagram details saved to Neo4j!")
                else:
                    st.error("Failed to save project flow diagram details to Neo4j.")
                st.session_state.last_project_flow_details = None
        st.rerun() # Rerun to clear the button state and messages
    if st.session_state.last_project_flow_details:
        st.button("Save Diagram Details to Neo4j", key="save_flow_diagram_neo4j_button", on_click=save_flow_diagram_to_neo4j)
else:
    st.info("Enter a description and click 'Generate Flow Diagram' to see the output.")