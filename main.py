"""
Lexia AI Agent Starter Kit
==========================

A production-ready starter kit for building AI agents that integrate with the Lexia platform.
This demonstrates best practices for creating AI agents with proper memory management,
streaming responses, file processing, and search capabilities.

Key Features:
- Clean, maintainable architecture with separation of concerns
- Built-in conversation memory and thread management
- Support for image analysis
- Real-time response streaming via Lexia's infrastructure
- Google search functionality with Serper API
- Robust error handling and comprehensive logging
- Inherited endpoints from Lexia package for consistency

Architecture:
- Main processing logic in process_message() function
- Memory management via ConversationManager class
- Utility functions for OpenAI integration
- Standard Lexia endpoints inherited from package

Usage:
    python main.py

The server will start on http://localhost:8000 with the following endpoints:
- POST /api/v1/send_message - Main chat endpoint
- GET /api/v1/health - Health check
- GET /api/v1/ - Root information
- GET /api/v1/docs - Interactive API documentation

Author: Lexia Team
License: MIT
"""

import logging
from openai import OpenAI
import json

# Configure logging with informative format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import AI agent components
from memory import ConversationManager
from lexia import (
    LexiaHandler, 
    ChatResponse, 
    ChatMessage, 
    Variable, 
    create_success_response,
    create_lexia_app,
    add_standard_endpoints,
    Variables
)
from agent_utils import format_system_prompt, format_messages_for_openai
from search_handler import serper_first_link
import os
import re

# Initialize core services
conversation_manager = ConversationManager(max_history=10)  # Keep last 10 messages per thread
lexia = LexiaHandler()

# Create the FastAPI app using Lexia's web utilities
app = create_lexia_app(
    title="Lexia AI Agent Starter Kit",
    version="1.0.0",
    description="Production-ready AI agent starter kit with Lexia integration"
)

async def process_message(data: ChatMessage) -> None:
    """
    Process incoming chat messages using OpenAI and send responses via Lexia.
    
    This is the core AI processing function that you can customize for your specific use case.
    The function handles:
    1. Message validation and logging
    2. Environment variable setup
    3. OpenAI API communication
    4. Image file processing
    5. Google search functionality
    6. Response streaming and completion
    
    Args:
        data: ChatMessage object containing the incoming message and metadata
        
    Returns:
        None: Responses are sent via Lexia's streaming and completion APIs
        
    Raises:
        Exception: If message processing fails (errors are sent to Lexia)
        
    Customization Points:
        - Modify system prompts and context
        - Adjust OpenAI model parameters
        - Implement specialized image processing
        - Add custom search capabilities
        - Customize error handling and logging
    """
    try:
        # Log comprehensive request information for debugging
        logger.info("=" * 80)
        logger.info("📥 FULL REQUEST BODY RECEIVED:")
        logger.info("=" * 80)
        logger.info(f"Thread ID: {data.thread_id}")
        logger.info(f"Message: {data.message}")
        logger.info(f"Response UUID: {data.response_uuid}")
        logger.info(f"Model: {data.model}")
        logger.info(f"System Message: {data.system_message}")
        logger.info(f"Project System Message: {data.project_system_message}")
        logger.info(f"Variables: {data.variables}")
        logger.info(f"Stream URL: {getattr(data, 'stream_url', 'Not provided')}")
        logger.info(f"Stream Token: {getattr(data, 'stream_token', 'Not provided')}")
        logger.info(f"Full data object: {data}")
        logger.info("=" * 80)
        
        # Log key processing information
        logger.info(f"🚀 Processing message for thread {data.thread_id}")
        logger.info(f"📝 Message: {data.message[:100]}...")
        logger.info(f"🔑 Response UUID: {data.response_uuid}")
        
        # Get OpenAI API key using Variables helper class
        vars = Variables(data.variables)
        openai_api_key = vars.get("OPENAI_API_KEY")
        if not openai_api_key:
            missing_key_msg = "Sorry, the OpenAI API key is missing or empty. From menu right go to admin mode, then agents and edit the agent in last section you can set the openai key."
            logger.error("OpenAI API key not found or empty in variables")
            lexia.stream_chunk(data, missing_key_msg)
            lexia.complete_response(data, missing_key_msg)
            return
        
        # Initialize OpenAI client and conversation management
        client = OpenAI(api_key=openai_api_key)
        conversation_manager.add_message(data.thread_id, "user", data.message)
        thread_history = conversation_manager.get_history(data.thread_id)
        
        # Stream a quick processing indicator
        lexia.stream_chunk(data, "🔎 Analizando tu mensaje...\n")

        # Greetings flow
        msg_lower = (data.message or "").strip().lower()
        greetings = {"hi", "hello", "hola", "hey", "buenas", "buenos días", "buenas tardes", "buenas noches"}
        if msg_lower in greetings:
            greet_reply = "👋 Hola, dime qué plato quieres preparar (por ejemplo: 'tortilla de patata')."
            lexia.stream_chunk(data, greet_reply)
            lexia.complete_response(data, greet_reply)
            return

        # Custom workflow: extract ingredients via OpenAI (JSON array)
        sys_prompt = (
            "You are a culinary assistant. When the user mentions a dish, "
            "extract a concise list of core grocery ingredients needed to make it. "
            "Respond ONLY with a valid JSON array of strings in Spanish where appropriate, "
            "no extra text. Keep common items simple (e.g., 'huevos', 'patatas', 'cebolla', 'aceite de oliva', 'sal')."
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": data.message}
        ]
        logger.info(f"🤖 Asking OpenAI for ingredients. Model: {data.model}")
        completion = client.chat.completions.create(
            model=data.model,
            messages=messages,
            max_tokens=300,
            temperature=0
        )
        raw_content = completion.choices[0].message.content or "[]"

        def _extract_json_array(text: str) -> list:
            import json as _json
            try:
                return _json.loads(text)
            except Exception:
                match = re.search(r"\[.*\]", text, re.DOTALL)
                if match:
                    try:
                        return _json.loads(match.group(0))
                    except Exception:
                        return []
                return []

        ingredients = _extract_json_array(raw_content)
        if not isinstance(ingredients, list):
            ingredients = []
        seen = set()
        normalized = []
        for item in ingredients:
            if isinstance(item, str):
                name = item.strip()
            elif isinstance(item, dict) and "name" in item:
                name = str(item["name"]).strip()
            else:
                continue
            if name and name.lower() not in seen:
                seen.add(name.lower())
                normalized.append(name)

        if not normalized:
            msg = "No pude identificar ingredientes. Por favor, especifica el plato con más detalle."
            lexia.stream_chunk(data, msg)
            lexia.complete_response(data, msg)
            return

        # Save to /tmp/ingredients.txt and stream list
        target_path = os.path.join("/tmp", "ingredients.txt")
        with open(target_path, "w", encoding="utf-8") as f:
            for ing in normalized:
                f.write(ing + "\n")
        lexia.stream_chunk(data, "🍳 Ingredientes detectados:\n")
        for ing in normalized:
            lexia.stream_chunk(data, f"- {ing}\n")
        lexia.stream_chunk(data, f"\n🗂️ Guardados {len(normalized)} ingredientes en ingredients.txt\n\n")

        # Search Carrefour for each ingredient and stream result
        results_lines = ["🛒 Enlaces de Carrefour por ingrediente:"]
        for ing in normalized:
            query = f"{ing} site:carrefour.es"
            try:
                lexia.stream_chunk(data, f"🔎 Buscando en Carrefour: {ing}\n")
                link = serper_first_link(query, data.variables)
            except Exception as e:
                logger.error(f"Serper error for '{ing}': {e}")
                link = None
            if link:
                lexia.stream_chunk(data, f"➡️ { ing }: { link }\n")
                results_lines.append(f"- {ing}: {link}")
            else:
                lexia.stream_chunk(data, f"➡️ {ing}: No encontrado\n")
                results_lines.append(f"- {ing}: No encontrado")

        final_response = "\n".join([
            "🍳 Ingredientes detectados:",
            "- " + "\n- ".join(normalized),
            "",
            "\n".join(results_lines)
        ])

        conversation_manager.add_message(data.thread_id, "assistant", final_response)
        lexia.complete_response(data, final_response)
        
        logger.info(f"🎉 Message processing completed successfully for thread {data.thread_id}")
            
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        logger.error(error_msg, exc_info=True)
        lexia.send_error(data, error_msg)


# Add standard Lexia endpoints including the inherited send_message endpoint
# This provides all the standard functionality without additional code
add_standard_endpoints(
    app, 
    conversation_manager=conversation_manager,
    lexia_handler=lexia,
    process_message_func=process_message
)

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Lexia AI Agent Starter Kit...")
    print("=" * 60)
    print("📖 API Documentation: http://localhost:8002/docs")
    print("🔍 Health Check: http://localhost:8002/api/v1/health")
    print("💬 Chat Endpoint: http://localhost:8002/api/v1/send_message")
    print("=" * 60)
    print("\n✨ This starter kit demonstrates:")
    print("   - Clean integration with Lexia package")
    print("   - Inherited endpoints for common functionality")
    print("   - Customizable AI message processing")
    print("   - Conversation memory management")
    print("   - Image processing")
    print("   - Google search functionality")
    print("   - Proper data structure for Lexia communication")
    print("   - Comprehensive error handling and logging")
    print("\n🔧 Customize the process_message() function to add your AI logic!")
    print("=" * 60)
    
    # Start the FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8002)
