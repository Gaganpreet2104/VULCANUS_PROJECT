# src/pages/6_Wireframe_Gen.py
import streamlit as st
import uuid
from datetime import datetime
from core.llm import get_ragbits_llm_client, generate_mukuro_wireframe_code
from core.agents import RagbitsWireframeAgent # Import the new agent
from utils.mukuro_compiler import MukuroLCompiler, MukuroLError
from core.neo4j_handler import Neo4jHandler
from components.ui_styles import apply_custom_styles
import streamlit.components.v1 as components # For rendering HTML
import asyncio # NEW: Import asyncio

# NEW: Page Configuration with icon
st.set_page_config(
    page_title="AI Wireframe UI Generator",
    page_icon="🖼️", # Icon for Wireframe page
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

st.header("AI Wireframe UI Generator")
st.markdown("---")

# Initialize LLM client (once per session)
if "ragbits_llm_wireframe" not in st.session_state:
    st.session_state.ragbits_llm_wireframe = get_ragbits_llm_client()

# Initialize Wireframe Agent (once per session)
if "wireframe_agent" not in st.session_state:
    st.session_state.wireframe_agent = RagbitsWireframeAgent(llm=st.session_state.ragbits_llm_wireframe)

# Initialize MukuroL Compiler (once per session)
if "mukuro_compiler" not in st.session_state:
    st.session_state.mukuro_compiler = MukuroLCompiler()

# Initialize Neo4j Handler (once per session)
if "neo4j_handler_wireframe" not in st.session_state:
    st.session_state.neo4j_handler_wireframe = Neo4jHandler()

# Session states for wireframe generation
if "wireframe_description" not in st.session_state:
    st.session_state.wireframe_description = ""
if "generated_mukuro_code" not in st.session_state:
    st.session_state.generated_mukuro_code = ""
if "rendered_wireframe_html" not in st.session_state:
    st.session_state.rendered_wireframe_html = ""
if "last_wireframe_details" not in st.session_state:
    st.session_state.last_wireframe_details = None

# MukuroL Language Reference for the AI
# This reference will be passed to the LLM to guide its MukuroL generation.
MUKUROL_REFERENCE = """
MukuroL supports the following commands:
`page`
  Represents a single screen and must be the root element.
  - `title`: Specifies the page title.

`box`
  A rectangular box rendered on the screen. Except for form components, wireframes are described by placing boxes.
  - `id`: Assigns a unique ID to the box's HTML element. (Optional, generated if not provided)
  - `class`: Specifies the CSS class applied to the box. (Optional)
  - `style`: Specifies inline styles applied to the box. (Optional)
  - `label`: Label text displayed inside the box (alternative to `text`).
  - `text`: Text displayed inside the box.
  - `size:{NxN}`: Specifies the width and height of the box in `NxN` format (e.g., `300pxx200px`).
  - `gpos:{col_start-col_end/row_start-row_end}`: Specifies the position of the box within a grid. Example: `gpos:1-10/1` (columns 1 through 10, row 1).
  - `scroll:[x|y|both]`: Specifies scroll behavior.

`textfield`
  A text field form component.
  - `id`: Assigns a unique ID. (Optional, generated if not provided)
  - `class`: CSS class. (Optional)
  - `style`: Inline styles. (Optional)
  - `label`: Label text associated with the text field.
  - `text`: Placeholder text displayed in the text field.
  - `cols`: Specifies the width of the text field as if it were a textarea (e.g., `50`).

`textarea`
  A textarea form component.
  - `id`: Assigns a unique ID. (Optional, generated if not provided)
  - `class`: CSS class. (Optional)
  - `style`: Inline styles. (Optional)
  - `label`: Label text associated with the textarea.
  - `text`: Placeholder text displayed in the textarea.
  - `cols`: Number of columns.
  - `rows`: Number of rows.

`select`
  A select box form component.
  - `id`: Assigns a unique ID. (Optional, generated if not provided)
  - `class`: CSS class. (Optional)
  - `style`: Inline styles. (Optional)
  - `label`: Label text associated with the select box.
  - `text`: Initial option text displayed in the select box.

`radio`
  A radio button form component.
  - `id`: Assigns a unique ID. (Optional, generated if not provided)
  - `class`: CSS class. (Optional)
  - `style`: Inline styles. (Optional)
  - `label`: Label text associated with the radio button.

`checkbox`
  A checkbox form component.
  - `id`: Assigns a unique ID. (Optional, generated if not provided)
  - `class`: CSS class. (Optional)
  - `style`: Inline styles. (Optional)
  - `label`: Label text associated with the checkbox.

`button`
  A button form component.
  - `id`: Assigns a unique ID. (Optional, generated if not provided)
  - `class`: CSS class. (Optional)
  - `style`: Inline styles. (Optional)
  - `label`: Label text displayed on the button.

`grid`
  A block for grid layouts. The internal area of this block is divided into specified-sized cells, and child boxes use the `gpos` helper to specify their display position and size.
  - `id`: Assigns a unique ID. (Optional, generated if not provided)
  - `class`: CSS class. (Optional)
  - `style`: Inline styles. (Optional)
  - `label`: Label text displayed inside the grid.
  - `text`: Text displayed inside the grid.
  - `size:[full | NxN]`: Specifies the overall size of the grid (`full` for full width and height, or `NxN` format like `800pxx600px`).
  - `tile:{NxN}`: Specifies the arrangement of tiles within the grid in `NxN` format (e.g., `2x1` for 2 columns, 1 row).

`flex`
  Represents a flexbox block. Child boxes are laid out according to the flex attributes specified.
  - `id`: Assigns a unique ID. (Optional, generated if not provided)
  - `class`: CSS class. (Optional)
  - `style`: Inline styles. (Optional)
  - `label`: Label text displayed inside the flexbox.
  - `text`: Text displayed inside the flexbox.
  - `size:[full | NxN]`: Specifies the width and height of the flexbox (`full` or `NxN` format).
  - `direction:[row | column]`: Specifies the direction of the flexbox.
  - `wrap:[wrap|nowrap]`: Specifies whether the flexbox wraps.
  - `align:[start | center | end]`: Specifies vertical alignment of items within the flexbox.
  - `justify:[start | center | end]`: Specifies horizontal alignment of items within the flexbox.

Important:
- Indentation (using spaces) defines nesting. Each level of indentation represents a child element.
- The first element on the first line MUST be `page`.
- Elements within a `grid` MUST use the `gpos` attribute to define their position.
- For form components, use the `label` or `text` attribute for the display text.
- If a line is intended as plain text content (e.g., list items for a sidebar menu), simply write the text content on that indented line without a command or attributes.
- Ensure all explicit `id` attributes are unique across the entire MukuroL code.
"""

st.subheader("1. Describe the UI you want to design")
user_description = st.text_area(
    "Describe your wireframe UI (e.g., 'A simple login page with username and password fields, a remember me checkbox, and a login button. Include a header at the top and a footer at the bottom.'):",
    value=st.session_state.wireframe_description,
    height=200,
    key="wireframe_description_input"
)
st.session_state.wireframe_description = user_description

ai_temperature = st.slider("AI Creativity (Temperature):", min_value=0.0, max_value=1.0, value=0.8, step=0.1, help="Adjust the AI's creativity for UI design (higher values may lead to more varied layouts).")

if st.button("Generate Wireframe", key="generate_wireframe_button", disabled=not user_description.strip()):
    st.session_state.generated_mukuro_code = ""
    st.session_state.rendered_wireframe_html = ""
    st.session_state.last_wireframe_details = None
    with st.spinner("Generating MukuroL code..."):
        # Pass the full MukuroL language reference to the AI
        # FIX: Await the async function call using asyncio.run()
        mukuro_code_raw = asyncio.run(generate_mukuro_wireframe_code(user_description, MUKUROL_REFERENCE, ai_temperature))
        
        # The AI is instructed to provide ONLY MukuroL code, no markdown block.
        # However, to be safe, check if it accidentally wrapped it.
        if "```" in mukuro_code_raw:
            # Attempt to strip any markdown code block wrappers
            parts = mukuro_code_raw.split("```")
            mukuro_code = mukuro_code_raw # Default if no valid block found
            if len(parts) > 1:
                # Prioritize content if it explicitly states 'mukuro' as language, otherwise just take the first block
                # Check the first line of the block for language hint (e.g., 'mukuro', 'text')
                first_line_of_block = parts[1].split('\n', 1)[0].strip().lower()
                if first_line_of_block in ['mukuro', 'text', '']: # Empty string for no language hint
                    mukuro_code = '\n'.join(parts[1].split('\n')[1:]) if first_line_of_block != '' else parts[1].strip()
                else: # Assume it's a generic code block but content is still MukuroL
                    mukuro_code = parts[1].strip()
            else:
                mukuro_code = mukuro_code_raw.strip() # No code block found, assume direct code
        else:
            mukuro_code = mukuro_code_raw.strip() # Assume raw MukuroL if no markdown syntax

        st.session_state.generated_mukuro_code = mukuro_code
        st.success("MukuroL code generated!")

        with st.spinner("Compiling MukuroL to HTML and rendering wireframe..."):
            try:
                compiler = st.session_state.mukuro_compiler # Get the cached instance
                html_output = compiler.compile(st.session_state.generated_mukuro_code)
                st.session_state.rendered_wireframe_html = html_output
                st.success("Wireframe rendered successfully!")

                # Prepare details for Neo4j logging
                event_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                st.session_state.last_wireframe_details = {
                    "event_id": event_id,
                    "description": user_description,
                    "generated_mukuro_code": mukuro_code,
                    "timestamp": timestamp
                }
                st.info("Wireframe generated. Click 'Save Wireframe to Neo4j' to persist this event.")

            except MukuroLError as e:
                st.error(f"MukuroL Compilation Error: {e}")
                st.session_state.rendered_wireframe_html = f"<div><p style='color:red;'>MukuroL Compilation Error: {e}</p></div>"
            except Exception as e:
                st.error(f"An unexpected error occurred during rendering: {e}")
                st.session_state.rendered_wireframe_html = f"<div><p style='color:red;'>Error rendering wireframe: {e}</p></div>"
    st.rerun() # Rerun to update the display


st.markdown("---")
col_code, col_render = st.columns(2)

with col_code:
    st.subheader("2. Generated MukuroL Code")
    if st.session_state.generated_mukuro_code:
        st.code(st.session_state.generated_mukuro_code, language="text", height=500)
    else:
        st.info("MukuroL code will appear here after generation.")

with col_render:
    st.subheader("3. Rendered Wireframe UI")
    if st.session_state.rendered_wireframe_html:
        # Use streamlit.components.v1.html to render the HTML string directly
        try:
            # Set a fixed height for the iframe to contain the wireframe
            # Adjust height as needed, consider the content
            components.html(st.session_state.rendered_wireframe_html, height=600, scrolling=True)
        except Exception as e:
            st.error(f"Error rendering HTML component: {e}")
            st.info("This might happen if the generated HTML is malformed or if the content is too large for the iframe.")
    else:
        st.info("The generated wireframe UI will be displayed here.")

# Save to Neo4j button
if st.session_state.last_wireframe_details:
    if st.button("Save Wireframe to Neo4j", key="save_wireframe_neo4j_button"):
        with st.spinner("Saving wireframe generation event to Neo4j..."):
            details = st.session_state.last_wireframe_details
            if st.session_state.neo4j_handler_wireframe.store_wireframe_event(
                details["event_id"],
                details["description"],
                details["generated_mukuro_code"],
                details["timestamp"]
            ):
                st.success("Wireframe generation event saved to Neo4j!")
            else:
                st.error("Failed to save wireframe generation event to Neo4j.")
            st.session_state.last_wireframe_details = None # Clear after saving
        st.rerun()