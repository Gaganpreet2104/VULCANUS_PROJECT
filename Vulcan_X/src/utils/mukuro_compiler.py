# src/utils/mukuro_compiler.py
import re
from collections import defaultdict

class MukuroLError(Exception):
    """Custom exception for MukuroL compilation errors."""
    pass

class MukuroLCompiler:
    def __init__(self):
        self.html_parts = []
        self.css_rules = defaultdict(dict) # Stores CSS rules: {selector: {prop: value}}
        self.indent_stack = [] # Stores (indent_level, html_tag_name) for closing
        self.element_id_counter = defaultdict(int) # To ensure unique HTML IDs (e.g., mkl_box_1, mkl_box_2)
        self.used_ids = set() # To track explicitly provided IDs and prevent duplicates
        self.page_title = "MukuroL Wireframe" # Default page title

    def _generate_unique_id(self, prefix="mkl_element"):
        """Generates a unique ID for HTML elements, based on type prefix."""
        self.element_id_counter[prefix] += 1
        return f"{prefix}_{self.element_id_counter[prefix]}"

    def _parse_attributes(self, attr_string):
        """
        Parses 'key:value' attributes from a string.
        Handles labels/texts that can contain spaces.
        Returns (attributes_dict, remaining_text_content)
        """
        attrs = {}
        remaining_text_parts = []
        
        # Split by space, then check each part. If it contains ':', it's a key-value pair.
        # Otherwise, it's part of the implicit text content.
        parts = attr_string.split(' ')
        
        i = 0
        while i < len(parts):
            part = parts[i]
            if ':' in part:
                key, value_fragment = part.split(':', 1)
                
                # Reconstruct value if it contains spaces (e.g., 'label:My Label Text')
                current_value = [value_fragment]
                j = i + 1
                while j < len(parts) and ':' not in parts[j]:
                    current_value.append(parts[j])
                    j += 1
                
                attrs[key.strip()] = ' '.join(current_value).strip()
                i = j
            else:
                remaining_text_parts.append(part)
                i += 1
        
        return attrs, ' '.join(remaining_text_parts).strip()


    def _add_css_rule(self, selector, properties):
        """Adds CSS properties to a given selector."""
        self.css_rules[selector].update(properties)

    def _compile_gpos_to_css(self, gpos_str, html_id):
        """Converts gpos string (e.g., '1-10/1') to CSS grid properties."""
        parts = gpos_str.split('/')
        if len(parts) != 2:
            raise MukuroLError(f"Invalid gpos format: {gpos_str}. Expected 'col_range/row_range'.")
        
        col_part, row_part = parts
        
        def parse_range(range_str):
            if '-' in range_str:
                start, end = map(int, range_str.split('-'))
                return start, end + 1 # CSS grid end is exclusive
            else:
                val = int(range_str)
                return val, val + 1 # Single cell
        
        try:
            col_start, col_end_css = parse_range(col_part)
            row_start, row_end_css = parse_range(row_part)
            
            self._add_css_rule(f"#{html_id}", {
                "grid-column": f"{col_start} / {col_end_css}",
                "grid-row": f"{row_start} / {row_end_css}"
            })
        except ValueError:
            raise MukuroLError(f"Invalid gpos number format: {gpos_str}")

    def _process_line(self, line):
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith('#'):
            return

        current_line_indent = len(line) - len(stripped_line)
        
        # Close tags for higher or equal indentation levels
        while self.indent_stack and current_line_indent <= self.indent_stack[-1][0]:
            _, tag_to_close = self.indent_stack.pop()
            self.html_parts.append(f"</{tag_to_close}>")

        # Parse command and attributes/content
        parts = stripped_line.split(' ', 1)
        command = parts[0]
        attr_string = parts[1] if len(parts) > 1 else ""
        
        attrs, implicit_text_content = self._parse_attributes(attr_string)
        
        # Determine actual content text: explicit 'text' > explicit 'label' > implicit text
        content_text = attrs.pop('text', None)
        if content_text is None:
            content_text = attrs.pop('label', None)
        if content_text is None:
            content_text = implicit_text_content
        
        html_tag = None
        unique_id = attrs.get('id')
        if not unique_id:
            unique_id = self._generate_unique_id(command if command not in ["text_content_line"] else "text")
        else:
            if unique_id in self.used_ids:
                raise MukuroLError(f"Duplicate ID '{unique_id}' found. IDs must be unique across the wireframe.")
            self.used_ids.add(unique_id)

        element_attrs_str = f'id="{unique_id}"'
        if 'class' in attrs:
            element_attrs_str += f' class="{attrs["class"]}"'
        if 'style' in attrs:
            element_attrs_str += f' style="{attrs["style"]}"'

        # Apply general wireframe element styles (can be overridden by specific element styles)
        self._add_css_rule(f"#{unique_id}", {
            "border": "1px dashed #555",
            "background-color": "rgba(255, 255, 255, 0.05)",
            "padding": "10px",
            "margin": "5px",
            "box-sizing": "border-box",
            "color": "#CCC",
            "font-size": "0.8em",
            "position": "relative",
            "word-wrap": "break-word", # Ensure text wraps within boxes
            "overflow": "hidden" # Prevent content overflowing by default
        })

        if command == "page":
            html_tag = "div"
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-page-container">')
            if 'title' in attrs:
                self.page_title = attrs['title']
            self._add_css_rule(f".mkl-page-container", {
                "background-color": "#555", "border": "2px solid #AAA",
                "box-shadow": "0 0 10px rgba(0, 0, 0, 0.5)",
                "margin": "20px auto", "min-height": "calc(100vh - 40px)",
                "width": "90%", "max-width": "1200px", "padding": "10px",
                "box-sizing": "border-sizing", "position": "relative", "display": "block",
                "font-family": "'Press Start 2P', monospace", # Apply font to page
            })
        elif command == "box":
            html_tag = "div"
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-box">')
            if 'size' in attrs and 'x' in attrs['size']:
                width, height = attrs['size'].split('x')
                self._add_css_rule(f"#{unique_id}", {"width": width, "height": height})
            if 'gpos' in attrs:
                self._compile_gpos_to_css(attrs['gpos'], unique_id)
            if 'scroll' in attrs:
                if attrs['scroll'] == 'x': self._add_css_rule(f"#{unique_id}", {"overflow-x": "scroll", "overflow-y": "hidden"})
                elif attrs['scroll'] == 'y': self._add_css_rule(f"#{unique_id}", {"overflow-y": "scroll", "overflow-x": "hidden"})
                elif attrs['scroll'] == 'both': self._add_css_rule(f"#{unique_id}", {"overflow": "scroll"})
            if content_text: # Display content within the box
                self.html_parts.append(f'<p class="mkl-label">{content_text}</p>')
        elif command == "textfield":
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-form-group">')
            if attrs.get('label'):
                self.html_parts.append(f'<label for="{unique_id}_input" class="mkl-input-label">{attrs["label"]}</label>')
            input_attrs = f'id="{unique_id}_input" type="text" placeholder="{content_text}"'
            if 'cols' in attrs:
                self._add_css_rule(f"#{unique_id}_input", {"width": f"{int(attrs['cols']) * 8}px", "max-width": "100%"})
            self.html_parts.append(f'<input {input_attrs} class="mkl-textfield">')
            self.html_parts.append('</div>')
        elif command == "textarea":
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-form-group">')
            if attrs.get('label'):
                self.html_parts.append(f'<label for="{unique_id}_area" class="mkl-input-label">{attrs["label"]}</label>')
            textarea_attrs = f'id="{unique_id}_area" placeholder="{content_text}"'
            if 'cols' in attrs:
                textarea_attrs += f' cols="{attrs["cols"]}"'
                self._add_css_rule(f"#{unique_id}_area", {"width": f"{int(attrs['cols']) * 8}px", "max-width": "100%"})
            if 'rows' in attrs:
                textarea_attrs += f' rows="{attrs["rows"]}"'
                self._add_css_rule(f"#{unique_id}_area", {"height": f"{int(attrs['rows']) * 20}px", "min-height": "40px"})
            self.html_parts.append(f'<textarea {textarea_attrs} class="mkl-textarea"></textarea>')
            self.html_parts.append('</div>')
        elif command == "select":
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-form-group">')
            if attrs.get('label'):
                self.html_parts.append(f'<label for="{unique_id}_select" class="mkl-input-label">{attrs["label"]}</label>')
            select_attrs = f'id="{unique_id}_select"'
            self.html_parts.append(f'<select {select_attrs} class="mkl-select">')
            if content_text:
                self.html_parts.append(f'<option value="">{content_text}</option>')
            self.html_parts.append('</select>')
            self.html_parts.append('</div>')
        elif command == "radio":
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-form-group mkl-radio-group">')
            # Group name for radio buttons based on immediate parent's indentation for simple grouping
            radio_group_name = f"radio_group_{self.indent_stack[-1][0] if self.indent_stack else 'global'}"
            input_attrs = f'id="{unique_id}_radio" type="radio" name="{radio_group_name}"'
            self.html_parts.append(f'<input {input_attrs} class="mkl-radio"><label for="{unique_id}_radio" class="mkl-radio-label">{content_text}</label>')
            self.html_parts.append('</div>')
        elif command == "checkbox":
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-form-group mkl-checkbox-group">')
            input_attrs = f'id="{unique_id}_checkbox" type="checkbox"'
            self.html_parts.append(f'<input {input_attrs} class="mkl-checkbox"><label for="{unique_id}_checkbox" class="mkl-checkbox-label">{content_text}</label>')
            self.html_parts.append('</div>')
        elif command == "button":
            self.html_parts.append(f'<button {element_attrs_str} class="mkl-button">{content_text}</button>')
        elif command == "grid":
            html_tag = "div"
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-grid">')
            self._add_css_rule(f"#{unique_id}", {"display": "grid", "gap": "5px"})
            if 'tile' in attrs and 'x' in attrs['tile']:
                cols, rows = map(int, attrs['tile'].split('x'))
                self._add_css_rule(f"#{unique_id}", {
                    "grid-template-columns": f"repeat({cols}, 1fr)",
                    "grid-template-rows": f"repeat({rows}, 1fr)"
                })
            elif 'size' in attrs and attrs['size'] == 'full':
                 self._add_css_rule(f"#{unique_id}", {"width": "100%", "height": "100%"})
            if content_text:
                self.html_parts.append(f'<p class="mkl-label">{content_text}</p>')
        elif command == "flex":
            html_tag = "div"
            self.html_parts.append(f'<div {element_attrs_str} class="mkl-flex">')
            self._add_css_rule(f"#{unique_id}", {"display": "flex", "gap": "5px"})
            if 'direction' in attrs:
                self._add_css_rule(f"#{unique_id}", {"flex-direction": attrs['direction']})
            if 'wrap' in attrs:
                self._add_css_rule(f"#{unique_id}", {"flex-wrap": attrs['wrap']})
            if 'align' in attrs:
                justify_map = {"start": "flex-start", "center": "center", "end": "flex-end"}
                self._add_css_rule(f"#{unique_id}", {"align-items": justify_map.get(attrs['align'], 'stretch')})
            if 'justify' in attrs:
                justify_map = {"start": "flex-start", "center": "center", "end": "flex-end"}
                self._add_css_rule(f"#{unique_id}", {"justify-content": justify_map.get(attrs['justify'], 'flex-start')})
            if content_text:
                self.html_parts.append(f'<p class="mkl-label">{content_text}</p>')
        else: # Unrecognized command or pure text content
            if content_text: # This condition catches lines that are just text or unrecognized commands with attributes
                # If the immediate parent is a box, flex, or grid, and it's not a known command,
                # treat it as a list item if it's within a sidebar-like context or general text.
                # This is a heuristic based on the example of 'Sidebar' containing 'Dashboard', 'Search', etc.
                if self.indent_stack and self.indent_stack[-1][1] in ["div"]: # If parent is a div (box, grid, flex)
                    # A more robust way would be to pass a 'context' parameter, but for this example,
                    # we can assume simple indented text are list items or general paragraphs.
                    # For simplicity, let's make them list items or general paragraphs.
                    # If the content text contains newlines, preserve them with pre-wrap
                    if "\n" in content_text:
                         self.html_parts.append(f'<p class="mkl-text-content">{content_text}</p>')
                    else:
                        # Try to determine if it's a list context
                        parent_command = stripped_line.split(' ')[0] # Heuristic to get parent command
                        if self.indent_stack and "box" == self.indent_stack[-1][1] and "Sidebar" in self.html_parts[-1]: # Crude check for sidebar list
                             self.html_parts.append(f'<li>{content_text}</li>') # Wrap in ul/li later
                        else:
                             self.html_parts.append(f'<p class="mkl-text-content">{content_text}</p>')
            # For unhandled commands that might have attributes, just add the raw line as a comment
            else:
                self.html_parts.append(f'<!-- Unhandled MukuroL line: {stripped_line} -->')
        
        if html_tag and command not in ["textfield", "textarea", "select", "radio", "checkbox", "button"]:
            # Only push to stack if an opening tag was added that needs explicit closing by indentation
            self.indent_stack.append((current_line_indent, html_tag))

    def compile(self, mukuro_code: str) -> str:
        self.html_parts = []
        self.css_rules = defaultdict(dict)
        self.indent_stack = []
        self.element_id_counter = defaultdict(int)
        self.used_ids = set()
        self.page_title = "MukuroL Wireframe"
        
        lines = mukuro_code.splitlines()
        
        # Initial pass for page title (if it's the very first line and a page command)
        if lines and lines[0].strip().startswith("page"):
            title_match = re.search(r'title:([^\n]+)', lines[0])
            if title_match:
                self.page_title = title_match.group(1).strip()

        # Group lines by indentation to potentially handle lists better
        indent_groups = defaultdict(list)
        for line_num, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                continue
            indent_level = len(line) - len(stripped_line)
            indent_groups[indent_level].append((line_num, line))

        # Process lines in order
        processed_line_numbers = set()
        for indent_level in sorted(indent_groups.keys()):
            for line_num, line in indent_groups[indent_level]:
                if line_num not in processed_line_numbers:
                    try:
                        self._process_line(line)
                        processed_line_numbers.add(line_num)
                    except MukuroLError as e:
                        return f"<!-- MukuroL Compilation Error: {e} in line: {line.strip()} -->"
                    except Exception as e:
                        import traceback
                        return f"<!-- Unexpected MukuroL Compilation Error: {e}\nTraceback: {traceback.format_exc()} -->"
        
        # Close any remaining open tags
        while self.indent_stack:
            _, tag_to_close = self.indent_stack.pop()
            self.html_parts.append(f"</{tag_to_close}>")
        
        # Post-processing to wrap list items if detected (heuristic)
        final_html_parts = []
        in_ul = False
        for part in self.html_parts:
            if '<p class="mkl-text-content">' in part and self.indent_stack and self.indent_stack[-1][1] == 'div' and not in_ul: # Heuristic: if inside a box/flex/grid and seems like a list start
                # This is a weak heuristic, a better approach needs parsing explicit list commands
                # For this implementation, let's keep it simple and just treat all content text as paragraphs or labels
                final_html_parts.append(part) # Already handled in _process_line as <p> or <li> (if specific parent check passes)
            elif '<li>' in part and not in_ul:
                final_html_parts.append('<ul>')
                final_html_parts.append(part)
                in_ul = True
            elif '<li>' in part and in_ul:
                final_html_parts.append(part)
            elif '</li>' in part and in_ul: # This logic should be handled by _process_line itself or not generated
                final_html_parts.append(part)
                if not any('<li>' in p for p in self.html_parts[self.html_parts.index(part)+1:]): # If no more list items follow
                    final_html_parts.append('</ul>')
                    in_ul = False
            else:
                if in_ul: # Close <ul> if we're exiting a list context unexpectedly
                    final_html_parts.append('</ul>')
                    in_ul = False
                final_html_parts.append(part)
        if in_ul: # If <ul> still open at the end
            final_html_parts.append('</ul>')
        
        # Build the final CSS string from css_rules
        css_output = ""
        for selector, properties in self.css_rules.items():
            css_output += f"{selector} {{\n"
            for prop, value in properties.items():
                css_output += f"  {prop}: {value};\n"
            css_output += "}\n"
        
        # Base CSS for wireframe look and feel
        base_css = """
        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: auto; /* Allow scrolling for the whole page if content overflows */
            background-color: #333; /* Dark background for wireframe container */
        }
        /* Page container, acts as the "canvas" for the wireframe */
        .mkl-page-container {
            background-color: #555; /* Page background within the container */
            border: 2px solid #AAA;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
            margin: 20px auto;
            min-height: calc(100vh - 40px); /* Fill most of viewport height */
            width: 90%;
            max-width: 1200px; /* Constrain page width */
            padding: 10px;
            box-sizing: border-box;
            position: relative;
            display: block;
            font-family: 'Press Start 2P', monospace; /* Apply font to page */
        }
        /* Generic box styles */
        .mkl-box, .mkl-grid, .mkl-flex {
            border: 1px dashed #AAA;
            background-color: rgba(255, 255, 255, 0.08); /* Transparent white */
            color: #DDD;
            padding: 8px;
            font-size: 0.85em;
            display: flex; /* Default to flex for internal content alignment */
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            position: relative;
            box-sizing: border-box;
            word-wrap: break-word; /* Ensure text wraps */
            overflow: hidden; /* Prevent content overflowing by default unless scroll is specified */
        }
        .mkl-label {
            font-weight: bold;
            color: #FFF;
            margin-bottom: 5px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            z-index: 1; /* Ensure label is above other content */
        }
        .mkl-text-content {
            font-size: 0.8em;
            color: #CCC;
            margin-top: 5px;
            text-align: left;
            width: 100%;
            white-space: pre-wrap; /* Preserve whitespace/line breaks */
            z-index: 1;
        }
        .mkl-form-group {
            display: flex;
            flex-direction: column;
            margin-bottom: 10px;
            width: 100%;
            align-items: flex-start; /* Align label/input to start */
            padding: 5px;
            border: 1px dotted rgba(255,255,255,0.2); /* Subtle form group border */
            box-sizing: border-box;
        }
        .mkl-input-label {
            color: #FFF;
            margin-bottom: 3px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .mkl-textfield, .mkl-textarea, .mkl-select {
            border: 1px solid #AAA;
            background-color: #EEE;
            color: #333;
            padding: 5px;
            width: calc(100% - 10px); /* Account for padding */
            box-sizing: border-box;
            font-family: monospace;
            font-size: 0.9em;
        }
        .mkl-textarea {
            resize: vertical; /* Allow vertical resizing for textareas */
        }
        .mkl-button {
            background-color: #AAA;
            color: #333;
            border: 1px solid #777;
            padding: 8px 15px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.9em;
            margin-top: 10px;
        }
        .mkl-radio-group, .mkl-checkbox-group {
            flex-direction: row;
            align-items: center;
            padding: 5px 0;
            width: fit-content; /* Don't take full width by default */
        }
        .mkl-radio, .mkl-checkbox {
            margin-right: 5px;
        }
        .mkl-radio-label, .mkl-checkbox-label {
            color: #FFF;
            font-size: 0.85em;
            cursor: pointer;
        }
        /* Specific adjustments for grid/flex items to fill space */
        .mkl-grid > *, .mkl-flex > * {
            flex-grow: 1;
            flex-shrink: 1;
            flex-basis: auto;
            min-height: 50px; /* Minimum height for visual distinction */
        }
        .mkl-grid > .mkl-box {
            display: flex; /* Ensure boxes inside grid can center content */
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }
        /* Styling for list items in sidebar-like structures */
        .mkl-box ul {
            list-style: none; /* Remove default bullet points */
            padding: 0;
            margin: 0;
            width: 100%;
        }
        .mkl-box ul li {
            text-align: left;
            padding: 5px 0;
            color: #CCC;
            font-size: 0.8em;
            border-bottom: 1px dotted rgba(255,255,255,0.1);
            cursor: pointer;
        }
        .mkl-box ul li:last-child {
            border-bottom: none;
        }
        .mkl-box ul li:hover {
            color: #FFF;
            background-color: rgba(255,255,255,0.05);
        }
        """
        
        final_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.page_title}</title>
            <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
            <style>
                {base_css}
                {css_output}
            </style>
        </head>
        <body>
            {''.join(final_html_parts)}
        </body>
        </html>
        """
        return final_html