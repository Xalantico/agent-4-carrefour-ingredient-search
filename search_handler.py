"""
Search Handler Module
====================

This module handles Google search functionality using the Serper API.
It provides clean, organized functions for web search capabilities.

Key Features:
- Google search via Serper API
- Function schema definitions for OpenAI
- Function execution and error handling
- Streaming progress updates to Lexia

Author: Lexia Team
License: MIT
"""

import asyncio
import logging
import json
import os
import re
import requests
from typing import List
from lexia import Variables

# Configure logging
logger = logging.getLogger(__name__)

# Available functions schema for OpenAI
AVAILABLE_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "google_search",
            "description": "Search Google for current information on any topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on Google"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of search results to return (default: 5, max: 10)",
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "build_menu_gallery",
            "description": "Given menu text, write it to menu.txt and fetch an image for each item via Serper images. Streams results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "menu_text": {
                        "type": "string",
                        "description": "Raw menu text where each line is a menu item (extracted from an image or user input)."
                    },
                    "results_per_item": {
                        "type": "integer",
                        "description": "Number of images to fetch per item (default 1, max 3)",
                        "minimum": 1,
                        "maximum": 3
                    }
                },
                "required": ["menu_text"]
            }
        }
    }
]

async def google_search(query: str, num_results: int = 5, variables: list = None) -> str:
    """
    Search Google using Serper API for current information.
    
    Args:
        query: The search query
        num_results: Number of results to return (1-10)
        variables: Lexia variables containing API keys
    
    Returns:
        str: Formatted search results
        
    Raises:
        ValueError: If API key is missing or invalid
        Exception: If search request fails
    """
    try:
        # Get Serper API key from variables
        if not variables:
            raise ValueError("Variables not provided to google_search")
        
        vars = Variables(variables)
        serper_api_key = vars.get("SERPER_API_KEY")
        if not serper_api_key:
            raise ValueError("Serper API key not found in variables. Please add SERPER_API_KEY to your agent configuration.")
        
        logger.info(f"🔍 Searching Google for: {query}")
        
        # Serper API endpoint
        url = "https://google.serper.dev/search"
        
        headers = {
            "X-API-KEY": serper_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": min(num_results, 10)  # Cap at 10 results
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Format the results
        results = []
        if "organic" in data:
            for i, result in enumerate(data["organic"][:num_results], 1):
                title = result.get("title", "No title")
                link = result.get("link", "")
                snippet = result.get("snippet", "No description available")
                
                results.append(f"{i}. **{title}**\n   {snippet}\n   [Link]({link})\n")
        
        if not results:
            return f"🔍 **Search Results for: {query}**\n\nNo results found for your search query."
        
        formatted_results = f"🔍 **Search Results for: {query}**\n\n" + "\n".join(results)
        
        logger.info(f"✅ Google search completed. Found {len(results)} results")
        return formatted_results
        
    except Exception as e:
        error_msg = f"Error performing Google search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ **Search Error:** {error_msg}"

def _parse_menu_items(menu_text: str) -> List[str]:
    """
    Parse raw menu text into clean food item names only.
    - Splits by lines
    - Strips bullet characters, prices, and descriptions
    - Keeps only food names (removes prices, descriptions, categories)
    - Deduplicates while preserving order
    - Skips empty/very short lines
    """
    if not menu_text:
        return []
    seen = set()
    items: List[str] = []
    for raw in menu_text.splitlines():
        line = raw.strip()
        # Remove common bullet prefixes
        for prefix in ("- ", "* ", "• ", "· ", "•", "-"):
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
        
        # Skip empty or very short lines
        if not line or len(line) < 2:
            continue
            
        # Remove prices (common patterns: $5.99, 5.99€, £5.99, etc.)
        # Remove price patterns
        line = re.sub(r'[\$€£¥]\s*\d+\.?\d*', '', line)
        line = re.sub(r'\d+\.?\d*\s*[\$€£¥]', '', line)
        line = re.sub(r'\$\d+\.?\d*', '', line)
        
        # Remove common menu section headers (not food items)
        section_headers = ['appetizers', 'entrees', 'mains', 'desserts', 'drinks', 'beverages', 
                          'starters', 'salads', 'soups', 'sides', 'specials', 'menu', 'price']
        if any(header in line.lower() for header in section_headers):
            continue
            
        # Remove descriptions (lines that are too long or contain common description words)
        description_words = ['description', 'ingredients', 'served with', 'comes with', 'includes']
        if any(word in line.lower() for word in description_words):
            continue
            
        # Skip lines that are mostly numbers or symbols
        if len(re.sub(r'[^a-zA-Z\s]', '', line)) < len(line) * 0.5:
            continue
            
        # Clean up the line
        line = line.strip()
        if not line or len(line) < 2:
            continue
            
        # Skip if already seen
        if line in seen:
            continue
        seen.add(line)
        items.append(line)
    return items

def _write_menu_file(items: List[str], target_path: str) -> None:
    """Write menu items to a file, one per line."""
    with open(target_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(item + "\n")

def _serper_image_search(query: str, variables: list) -> str | None:
    """
    Use Serper Images API to get a food image URL for the query.
    Returns the first food image URL if available, else None.
    """
    vars = Variables(variables)
    api_key = vars.get("SERPER_API_KEY")
    if not api_key:
        raise ValueError("Serper API key not found in variables. Please add SERPER_API_KEY to your agent configuration.")

    # Enhance query to get food images specifically
    food_query = f"{query} food dish meal recipe"
    
    url = "https://google.serper.dev/images"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {
        "q": food_query,
        "num": 5,  # Get more results to filter for food images
        "safe": "active"  # Ensure safe search
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    images = data.get("images") or []
    
    if not images:
        return None
        
    # Filter for food-related images by checking titles and sources
    food_keywords = ['food', 'dish', 'meal', 'recipe', 'cooking', 'restaurant', 'kitchen', 'chef']
    
    for img in images:
        title = img.get("title", "").lower()
        source = img.get("source", "").lower()
        
        # Check if title or source contains food-related keywords
        if any(keyword in title or keyword in source for keyword in food_keywords):
            # Prefer original or imageUrl
            return img.get("imageUrl") or img.get("thumbnailUrl") or img.get("link")
    
    # If no food-specific image found, return the first image anyway
    first = images[0]
    return first.get("imageUrl") or first.get("thumbnailUrl") or first.get("link")

async def build_menu_gallery(menu_text: str, variables: list, lexia_handler, data, results_per_item: int = 1) -> str:
    """
    Build a menu gallery from menu text:
    - Parse items
    - Write to menu.txt
    - For each item, fetch image(s) via Serper and stream back to Lexia
    - Return a combined summary string
    """
    results_per_item = max(1, min(results_per_item or 1, 3))
    items = _parse_menu_items(menu_text)
    if not items:
        msg = "No menu items detected to build a gallery."
        logger.info(msg)
        return msg

    # Write file to a writable location in the container
    target_path = os.path.join("/tmp", "menu.txt")
    _write_menu_file(items, target_path)
    lexia_handler.stream_chunk(data, f"\n🗂️ Saved menu items to menu.txt ({len(items)} items)")

    combined = [f"\n🍽️ **Menu Gallery** ({len(items)} items)\n"]
    for idx, item in enumerate(items, start=1):
        lexia_handler.stream_chunk(data, f"\n{idx}. {item}")
        # Show loading indicator
        #lexia_handler.stream_chunk(data, "[lexia.loading.image.start]")
        found_any = False
        for n in range(results_per_item):
            try:
                image_url = _serper_image_search(item, variables)
                if image_url:
                    found_any = True
                    # Stream the image URL wrapped in Lexia image tags
                    lexia_handler.stream_chunk(data, f"[lexia.image.start]{image_url}[lexia.image.end]")
                    # Also include the wrapped URL in the final response
                    combined.append(f"{idx}. {item}: [lexia.image.start]{image_url}[lexia.image.end]")
                else:
                    logger.info(f"No image found for item: {item}")
                    break
            except Exception as e:
                logger.error(f"Image search failed for '{item}': {e}", exc_info=True)
                break
        # End loading indicator
        #lexia_handler.stream_chunk(data, "[lexia.loading.image.end]")
        if not found_any:
            lexia_handler.stream_chunk(data, f"⚠️ No image found for: {item}")

    return "\n".join(combined)

async def execute_function_call(function_call: dict, lexia_handler, data) -> tuple[str, str]:
    """
    Execute a function call and return the result.
    
    Args:
        function_call: The function call object from OpenAI
        lexia_handler: The Lexia handler instance for streaming updates
        data: The original chat message data
        
    Returns:
        tuple: (result_message, None)
    """
    try:
        function_name = function_call['function']['name']
        logger.info(f"🔧 Processing function: {function_name}")
        
        # Stream function processing start to Lexia
        processing_msg = f"\n⚙️ **Processing function:** {function_name}"
        lexia_handler.stream_chunk(data, processing_msg)
        
        if function_name == "google_search":
            args = json.loads(function_call["function"]["arguments"])
            query = args.get("query")
            num_results = args.get("num_results", 5)
            
            # Stream search start
            search_msg = f"\n🔍 **Searching Google for:** {query}"
            lexia_handler.stream_chunk(data, search_msg)
            
            # Perform the search
            result = await google_search(query, num_results, data.variables)
            
            # Stream the results
            lexia_handler.stream_chunk(data, result)
            
            return result, None
        elif function_name == "build_menu_gallery":
            args = json.loads(function_call["function"]["arguments"])
            menu_text = args.get("menu_text", "")
            results_per_item = args.get("results_per_item", 1)
            if not menu_text:
                err = "menu_text is required for build_menu_gallery"
                logger.error(err)
                return f"\n\n❌ **Function Error:** {err}", None

            # Stream start
            lexia_handler.stream_chunk(data, "\n📋 **Building menu gallery**")
            summary = await build_menu_gallery(menu_text, data.variables, lexia_handler, data, results_per_item)
            # Stream summary
            lexia_handler.stream_chunk(data, f"\n✅ **Menu gallery built**\n{summary}")
            return summary, None
        else:
            error_msg = f"Unknown function: {function_name}"
            logger.error(error_msg)
            return f"\n\n❌ **Function Error:** {error_msg}", None
            
    except Exception as e:
        error_msg = f"Error executing function {function_call['function']['name']}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        function_error = f"\n\n❌ **Function Execution Error:** {error_msg}"
        return function_error, None

async def process_function_calls(function_calls: list, lexia_handler, data) -> tuple[str, str]:
    """
    Process a list of function calls and return the combined result.
    
    Args:
        function_calls: List of function call objects from OpenAI
        lexia_handler: The Lexia handler instance for streaming updates
        data: The original chat message data
        
    Returns:
        tuple: (combined_result_message, None)
    """
    if not function_calls:
        logger.info("🔧 No function calls to process")
        return "", None
    
    logger.info(f"🔧 Processing {len(function_calls)} function calls...")
    
    combined_result = ""
    
    for function_call in function_calls:
        try:
            result, _ = await execute_function_call(function_call, lexia_handler, data)
            combined_result += result
                
        except Exception as e:
            error_msg = f"Error processing function call: {str(e)}"
            logger.error(error_msg, exc_info=True)
            combined_result += f"\n\n❌ **Function Processing Error:** {error_msg}"
    
    return combined_result, None

def get_available_functions() -> list:
    """
    Get the list of available functions for OpenAI.
    
    Returns:
        list: List of function schemas
    """
    return AVAILABLE_FUNCTIONS

def serper_first_link(query: str, variables: list) -> str | None:
    """Return the first organic result link for a Serper web search.

    Args:
        query: Search query
        variables: Lexia variables containing SERPER_API_KEY

    Returns:
        The first result link if found, else None.
    """
    vars = Variables(variables)
    api_key = vars.get("SERPER_API_KEY")
    if not api_key:
        raise ValueError("Serper API key not found in variables. Please add SERPER_API_KEY to your agent configuration.")

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5}

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    organic = data.get("organic") or []
    if not organic:
        return None
    return organic[0].get("link")
