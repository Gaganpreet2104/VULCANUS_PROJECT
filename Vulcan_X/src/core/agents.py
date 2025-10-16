# src/core/agents.py
import asyncio
import json
import os
import tempfile
from typing import AsyncGenerator, Iterable, Type
import shutil
import streamlit as st
from pydantic import BaseModel # Ensure BaseModel is imported from pydantic
from collections.abc import Iterable # Keep this import, though direct Element usage is removed

# Ragbits Imports
from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt # Import Prompt
# from ragbits.core.embeddings import LiteLLMEmbedder # Not used directly in agents anymore, only litellm.embedding
from ragbits.agents import ToolCallResult

# Import get_ragbits_llm_client to ensure LLM is correctly initialized with temperature settings from Prompt
from core.llm import get_ragbits_llm_client 
# NEW: Import WireframePromptInput and WireframePrompt from core.llm
from core.llm import WireframePromptInput, WireframePrompt # THIS LINE IS ADDED

# --- Prompt Input Models (for base agents and specific tasks) ---
class AgentBaseInput(BaseModel):
    query: str = "" # Default to empty string for generic use

# FIX: Moved CodeGenerationPromptInput to agents.py as it's specific to CodeGenerationAgent's prompt
class CodeGenerationPromptInput(BaseModel):
    original_code: str
    conversion_type: str # This now describes the operation (Generate, Refactor, Optimize, Convert)
    user_instructions: str
    # New fields for 'Convert Language' operation
    source_language: str = ""
    source_framework: str = ""
    target_language: str = ""
    target_framework: str = ""

# FIX: CodeGenerationPrompt now correctly uses its specific InputModel.
# Temperature will be injected into this Prompt instance via its llm_settings before generation.
class CodeGenerationPrompt(Prompt[CodeGenerationPromptInput, str]):
    system_prompt = """
    You are an AI assistant specialized in code generation, refactoring, optimization, and conversion.
    Your responses should be the code directly, without any conversational filler or explanation,
    unless explicitly asked for by the user instructions.
    Ensure the generated code is syntactically correct for the target language/framework.
    If asked to refactor or optimize, focus solely on improving the provided code.
    If asked to convert, provide a complete, equivalent code in the target language/platform.
    Always wrap the generated code in appropriate markdown code blocks (e.g., ```python\\n...\\n```).
    """
    user_prompt = """
    Operation: {{ conversion_type }}
    Original Code:
    ```
    {{ original_code }}
    ```
    {% if source_language and target_language %}
    Source Language: {{ source_language }} ({{ source_framework }})
    Target Language: {{ target_language }} ({{ target_framework }})
    {% endif %}
    User Instructions: {{ user_instructions }}
    Please provide the generated or converted code:
    """
    # Define a default LLMSettings here, to be overridden when instantiated
    class LLMSettings(BaseModel):
        temperature: float = 0.7 # Default temperature for code gen
    llm_settings: LLMSettings = LLMSettings()

# FIX: Changed context to context_str (string) instead of Iterable[Element]
class DocumentQueryPromptInput(BaseModel):
    query: str
    context_str: str # Use a single string for context

class DocumentQueryPrompt(Prompt[DocumentQueryPromptInput, str]):
    system_prompt = """
    You are a highly accurate document question-answering assistant.
    Answer the user's question ONLY using the provided context.
    If the context does not contain enough information to answer the question, state that you cannot answer based on the given context.
    Do not make up information.
    """
    user_prompt = """
    QUESTION:
    {{ query }}
    CONTEXT:
    {{ context_str }}
    """
    # Default temperature for document query
    class LLMSettings(BaseModel):
        temperature: float = 0.5
    llm_settings: LLMSettings = LLMSettings()

class DataLineagePromptInput(BaseModel):
    code_or_description: str

class DataLineagePrompt(Prompt[DataLineagePromptInput, str]):
    system_prompt = (
        "You are an AI assistant specialized in analyzing code or natural language descriptions "
        "to identify data sources, data transformations (functions/classes), and data sinks. "
        "Your goal is to extract information suitable for constructing a data lineage graph. "
        "Provide the output as a JSON object with 'nodes' and 'edges'. If no data lineage can be determined, return an empty JSON structure. "
        "The node types should be 'data_source', 'transformation', 'data_sink', 'function', 'class', 'method', 'scope', 'process'. "
        "Each node must have an 'id', 'label', and 'type'. Each edge must have 'source', 'target', and 'label' (optional). "
        "Ensure the JSON output is valid and minimal. Always wrap JSON in a single ```json...``` block."
        "Example JSON structure: "
        "```json\n"
        "{\n"
        "  \"nodes\": [\n"
        "    {\"id\": \"source_db\", \"label\": \"Source Database\", \"type\": \"data_source\"},\n"
        "    {\"id\": \"transform_func\", \"label\": \"Transform Data\", \"type\": \"transformation\"},\n"
        "    {\"id\": \"target_report\", \"label\": \"Target Report\", \"type\": \"data_sink\"}\n"
        "  ],\n"
        "  \"edges\": [\n"
        "    {\"source\": \"source_db\", \"target\": \"transform_func\", \"label\": \"reads from\"},\n"
        "    {\"source\": \"transform_func\", \"target\": \"target_report\", \"label\": \"writes to\"}\n"
        "  ]\n"
        "}\n"
        "```"
    )
    user_prompt = """
    Analyze the following code or description and extract data lineage in JSON format:
    ```
    {{ code_or_description }}
    ```
    Provide ONLY the JSON output, wrapped in ```json...```.
    """
    # Default temperature for lineage analysis
    class LLMSettings(BaseModel):
        temperature: float = 0.5
    llm_settings: LLMSettings = LLMSettings()

class CloudCodeConverterPromptInput(BaseModel):
    original_code: str
    file_type: str
    source_platform: str
    source_version: str
    target_platform: str
    target_version: str
    user_instructions: str = ""

class CloudCodeConverterPrompt(Prompt[CloudCodeConverterPromptInput, str]):
    system_prompt = (
        "You are an expert cloud code converter. Your task is to accurately convert "
        "code snippets between different cloud platforms, services, and versions. "
        "Pay close attention to the source and target specifications, and user instructions. "
        "Provide the complete converted code directly, without conversational filler. "
        "Ensure the converted code is syntactically correct and idiomatic for the target. "
        "Always wrap the generated code in appropriate markdown code blocks."
    )
    user_prompt = """
    Original Code ({file_type}):
    ```
    {{ original_code }}
    ```
    Source Platform/Service: {{ source_platform }} (Version: {{ source_version }})
    Target Platform/Service: {{ target_platform }} (Version: {{ target_version }})
    User Instructions: {{ user_instructions }}
    Please provide the converted code:
    """
    # Default temperature for cloud code converter
    class LLMSettings(BaseModel):
        temperature: float = 0.7
    llm_settings: LLMSettings = LLMSettings()

# REMOVED: WireframePromptInput and WireframePrompt are no longer defined here.
# They are now imported from core.llm where all other prompts are defined.

# --- Agent Definitions ---
class RagbitsCodeGenerationAgent(Agent):
    def __init__(self, llm: LiteLLM, persona: str = "Standard"):
        self.persona = persona
        class BaseAgentPrompt(Prompt[AgentBaseInput]):
            system_prompt = "You are a versatile AI assistant."
            user_prompt = "{{ query }}"
        super().__init__(llm=llm, prompt=BaseAgentPrompt)

    def generate_code(self,
                      original_code: str,
                      conversion_type: str, # This now indicates operation like "Convert: Python to JS"
                      user_instructions: str = "",
                      source_language: str = "",
                      source_framework: str = "",
                      target_language: str = "",
                      target_framework: str = "",
                      temperature: float = 0.7 # This parameter is passed from UI slider
                      ) -> str:
        """
        Generates/converts code using the Ragbits agent.
        This method is synchronous and wraps the async llm call.
        """
        # FIX: Instantiate CodeGenerationPromptInput correctly
        code_prompt_input_data = CodeGenerationPromptInput(
            original_code=original_code,
            conversion_type=conversion_type,
            user_instructions=user_instructions,
            source_language=source_language,
            source_framework=source_framework,
            target_language=target_language,
            target_framework=target_framework
        )
        # FIX: Instantiate CodeGenerationPrompt and inject temperature via llm_settings
        code_gen_prompt_instance = CodeGenerationPrompt(code_prompt_input_data)
        code_gen_prompt_instance.llm_settings.temperature = temperature # Override default with UI slider value
        try:
            llm_client_for_this_call = get_ragbits_llm_client() # Get base LLM client
            response = asyncio.run(llm_client_for_this_call.generate(prompt=code_gen_prompt_instance))
            return response
        except Exception as e:
            return f"Error: An error occurred during code generation: {e}"

class RagbitsDataLineageAgent(Agent):
    def __init__(self, llm: LiteLLM):
        # DataLineagePrompt already defines its own LLMSettings, so we use that.
        super().__init__(llm=llm, prompt=DataLineagePrompt)

    def extract_lineage(self, code_or_description: str) -> dict:
        """
        Extracts data lineage information from code or description.
        Returns a dictionary with 'nodes' and 'edges'.
        """
        lineage_prompt_input_data = DataLineagePromptInput(code_or_description=code_or_description)
        lineage_prompt_instance = DataLineagePrompt(lineage_prompt_input_data) # Instantiate with input data
        try:
            llm_client_for_this_call = get_ragbits_llm_client()
            response_text = asyncio.run(llm_client_for_this_call.generate(prompt=lineage_prompt_instance))
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            if not json_str:
                return {"nodes": [], "edges": [], "data_sources_identified": [], "data_sinks_identified": []}
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            st.error(f"Error decoding JSON from AI response: {e}. AI response:\n{response_text}")
            return {"nodes": [], "edges": [], "data_sources_identified": [], "data_sinks_identified": []}
        except Exception as e:
            st.error(f"Unexpected error processing AI response for data lineage: {e}. AI response:\n{response_text}")
            return {"nodes": [], "edges": [], "data_sources_identified": [], "data_sinks_identified": []}

class RagbitsCloudCodeConverterAgent(Agent):
    def __init__(self, llm: LiteLLM):
        # CloudCodeConverterPrompt already defines its own LLMSettings, so we use that.
        super().__init__(llm=llm, prompt=CloudCodeConverterPrompt)

    def convert_code(self, original_code: str, file_type: str, source_platform: str,
                     source_version: str, target_platform: str, target_version: str,
                     user_instructions: str = "", temperature: float = 0.7) -> str: # Added temperature here from UI
        """
        Converts cloud-specific code using the Ragbits agent.
        This method is synchronous and wraps the async llm call.
        """
        conversion_prompt_input_data = CloudCodeConverterPromptInput(
            original_code=original_code,
            file_type=file_type,
            source_platform=source_platform,
            source_version=source_version,
            target_platform=target_platform,
            target_version=target_version,
            user_instructions=user_instructions
        )
        # FIX: Instantiate CloudCodeConverterPrompt and inject temperature via llm_settings
        conversion_prompt_instance = CloudCodeConverterPrompt(conversion_prompt_input_data)
        conversion_prompt_instance.llm_settings.temperature = temperature # Override default with UI slider value
        try:
            llm_client_for_this_call = get_ragbits_llm_client()
            response = asyncio.run(llm_client_for_this_call.generate(prompt=conversion_prompt_instance))
            return response
        except Exception as e:
            return f"Error: An error occurred during cloud code conversion: {e}"

# NEW: Ragbits Agent for Wireframe Generation
class RagbitsWireframeAgent(Agent):
    def __init__(self, llm: LiteLLM):
        # WireframePrompt is now imported from core.llm
        super().__init__(llm=llm, prompt=WireframePrompt) # Use the imported WireframePrompt

    def generate_wireframe_code(self, user_description: str, mukuro_reference: str, temperature: float = 0.8) -> str:
        """
        Generates MukuroL code for a UI wireframe based on user description.
        """
        wireframe_prompt_input = WireframePromptInput(
            user_description=user_description,
            mukuro_reference=mukuro_reference
        )
        wireframe_prompt_instance = WireframePrompt(wireframe_prompt_input)
        wireframe_prompt_instance.llm_settings.temperature = temperature # Apply temperature from UI

        try:
            llm_client_for_this_call = get_ragbits_llm_client()
            response = asyncio.run(llm_client_for_this_call.generate(prompt=wireframe_prompt_instance))
            return response
        except Exception as e:
            return f"Error: An error occurred during wireframe generation: {e}"