import json
import os
import hashlib
import hmac
import base64
import logging
import requests
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import re

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# LINE Bot credentials from environment variables
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')

# OpenRouter API configuration
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL')

# Debug option - set to 'false' to disable signature validation for testing
ENABLE_SIGNATURE_VALIDATION = os.environ.get('ENABLE_SIGNATURE_VALIDATION', 'true').lower() == 'true'

# Debug logging for environment variables
logger.info(f"Environment variables status:")
logger.info(f"CHANNEL_ACCESS_TOKEN exists: {bool(CHANNEL_ACCESS_TOKEN)}")
logger.info(f"CHANNEL_SECRET exists: {bool(CHANNEL_SECRET)}")
logger.info(f"OPENROUTER_API_KEY exists: {bool(OPENROUTER_API_KEY)}")
logger.info(f"OPENROUTER_MODEL: {OPENROUTER_MODEL}")
logger.info(f"ENABLE_SIGNATURE_VALIDATION: {ENABLE_SIGNATURE_VALIDATION}")

# Load search configuration
def load_search_config():
    """Load search configuration from JSON file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'search_config.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load search config: {e}")
        return {
            "search_topics": {},
            "search_settings": {"max_results": 3, "summary_length": 200}
        }

SEARCH_CONFIG = load_search_config()

# Initialize LINE Bot API and Webhook Handler
if CHANNEL_ACCESS_TOKEN:
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
else:
    logger.error("CHANNEL_ACCESS_TOKEN is missing!")
    line_bot_api = None

# Determine channel secret for handler based on validation flag
# The actual CHANNEL_SECRET from env is still used for our custom validate_signature if enabled
handler_channel_secret = CHANNEL_SECRET if ENABLE_SIGNATURE_VALIDATION else ""
if not ENABLE_SIGNATURE_VALIDATION:
    logger.warning(f"Signature validation is DISABLED. Initializing WebhookHandler with empty secret.")
    handler = WebhookHandler("")  # Empty secret disables validation
else:
    logger.info("Signature validation is ENABLED. Initializing WebhookHandler with actual secret.")
    if CHANNEL_SECRET:
        handler = WebhookHandler(CHANNEL_SECRET)
    else:
        logger.error("CHANNEL_SECRET is missing but validation is enabled!")
        handler = WebhookHandler("")

def lambda_handler(event, context):
    """
    AWS Lambda handler function for LINE Bot webhook
    """
    try:
        # Check if this is a health check request
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        if http_method == 'GET' and path == '/health':
            return health_check()
        
        # Get request body and signature
        body = event.get('body', '')
        headers = event.get('headers', {})
        
        # LINE sends signature in X-Line-Signature header, but API Gateway might lowercase it
        signature = headers.get('X-Line-Signature') or headers.get('x-line-signature', '')
        
        logger.info(f"Received webhook body: {body}")
        logger.info(f"All headers: {headers}")
        logger.info(f"Signature header: {signature}")
        
        # Validate signature (can be disabled for testing)
        if ENABLE_SIGNATURE_VALIDATION and not validate_signature(body, signature):
            logger.error("Invalid signature")
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Invalid signature'})
            }
        elif not ENABLE_SIGNATURE_VALIDATION:
            logger.warning("Signature validation is DISABLED - this should only be used for testing!")
        
        # Handle webhook events
        handler.handle(body, signature)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'OK'})
        }
        
    except InvalidSignatureError:
        logger.error("Invalid signature error")
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'Invalid signature'})
        }
    except LineBotApiError as e:
        logger.error(f"LINE Bot API error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'LINE Bot API error'})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }


def validate_signature(body, signature):
    """
    Validate LINE webhook signature
    """
    if not CHANNEL_SECRET or not signature:
        logger.error(f"Missing CHANNEL_SECRET or signature. CHANNEL_SECRET exists: {bool(CHANNEL_SECRET)}, signature: {signature}")
        return False
    
    try:
        # Ensure body is bytes for HMAC calculation
        if isinstance(body, str):
            body_bytes = body.encode('utf-8')
        else:
            body_bytes = body
            
        hash_digest = hmac.new(
            CHANNEL_SECRET.encode('utf-8'),
            body_bytes,
            hashlib.sha256
        ).digest()
        
        expected_signature = base64.b64encode(hash_digest).decode('utf-8')
        
        logger.info(f"Expected signature: {expected_signature}")
        logger.info(f"Received signature: {signature}")
        
        is_valid = hmac.compare_digest(signature, expected_signature)
        logger.info(f"Signature validation result: {is_valid}")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error during signature validation: {e}")
        return False


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """
    Handle text messages from users
    """
    try:
        user_message = event.message.text
        user_id = event.source.user_id
        
        logger.info(f"Received message: {user_message} from user: {user_id}")
        
        # Check if LINE Bot API is available
        if not line_bot_api:
            logger.error("LINE Bot API is not initialized - missing CHANNEL_ACCESS_TOKEN")
            return
        
        # Generate response
        response_message = generate_response(user_message)
        
        # Send reply message
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_message)
        )
        
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        # Only try to send error message if line_bot_api is available
        if line_bot_api:
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="Sorry, I encountered an error. Please try again.")
                )
            except Exception as reply_error:
                logger.error(f"Failed to send error message: {reply_error}")


def generate_response(user_message):
    """
    Generate intelligent response using AI analysis and web search
    
    Steps:
    1. Analyze user's question using AI to determine if web search is needed
    2. If search is needed, perform DuckDuckGo search
    3. Generate final response using AI with or without search context
    """
    user_message_lower = user_message.lower()
    
    # Handle basic commands first
    if 'hello' in user_message_lower or 'hi' in user_message_lower:
        return "Hello! How can I help you today? I can search the web for current information or answer general questions!"
    elif 'help' in user_message_lower:
        return "I'm a LINE bot with AI and web search capabilities!\n\n• Ask me anything and I'll decide if I need to search for current information\n• Say 'search [query]' for direct web search\n• I can help with current events, weather, news, tech updates, and more!"
    elif 'time' in user_message_lower:
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Current time: {current_time}"
    
    # Check for explicit search command first
    if user_message_lower.startswith('search '):
        query = user_message[7:].strip()
        search_results = perform_search(query)
        if search_results and not search_results.startswith("I couldn't find"):
            return generate_contextual_response(user_message, search_results)
        else:
            return search_results or "Sorry, I couldn't find any relevant information."
    
    # Step 1: Analyze user's question with AI to determine if search is needed
    if OPENROUTER_API_KEY:
        try:
            search_decision = analyze_search_need(user_message)
            logger.info(f"Search decision result: {search_decision}")
            
            # Step 2: Check if AI determined search is needed
            if should_search(search_decision):
                logger.info("AI determined search is needed, performing web search...")
                search_query = extract_search_query(search_decision, user_message)
                search_results = perform_search(search_query)
                
                # Step 3: Generate final response with search context
                if search_results and not search_results.startswith("I couldn't find"):
                    return generate_contextual_response(user_message, search_results)
                else:
                    # If search failed, fall back to direct AI response
                    return generate_ai_response_http(user_message)
            else:
                # No search needed, use direct AI response
                logger.info("AI determined no search needed, generating direct response...")
                return generate_ai_response_http(user_message)
                
        except Exception as e:
            logger.warning(f"AI processing error, falling back to direct AI response: {e}")
            # Fall back to direct AI response if analysis fails
            if OPENROUTER_API_KEY:
                return generate_ai_response_http(user_message)
    
    # Final fallback to simple response
    return f"I received your message: {user_message}\nI'm experiencing some technical issues. Please try again later."


def analyze_search_need(user_message):
    """
    Step 1: Analyze user's question to determine if web search is needed
    """
    system_prompt = """You are an AI assistant that analyzes user questions to determine if they need web search for current information.

Analyze the user's question and determine if it requires recent/current information that would benefit from web search.

Questions that NEED web search:
- Current events, news, weather
- Recent developments, latest updates
- Current prices, stock market, live data
- Recent sports scores, match results
- Today's/recent information about anything
- Breaking news or trending topics

Questions that DON'T NEED web search:
- General knowledge questions
- Definitions, explanations of concepts
- Historical facts (unless asking for recent updates)
- Math calculations
- Personal advice or opinions
- Simple greetings, casual conversation

Respond with one of these tags:
- <search>YES</search> if web search is needed
- <search>NO</search> if web search is not needed

After the tag, briefly explain your reasoning and if search is needed, suggest a good search query.

Examples:
- "What's the weather today?" → <search>YES</search> Need current weather data. Search: "weather today"
- "What is Python programming?" → <search>NO</search> General knowledge question about programming.
- "Latest AI news" → <search>YES</search> Need current AI developments. Search: "latest AI news 2025"
- "How are you?" → <search>NO</search> Casual greeting, no search needed."""
    
    return call_openrouter_api(system_prompt, user_message, max_tokens=100)


def should_search(analysis_response):
    """
    Check if AI determined that search is needed
    """
    if not analysis_response:
        return False
    
    # Look for <search>YES</search> pattern
    import re
    match = re.search(r'<search>YES</search>', analysis_response, re.IGNORECASE)
    return match is not None


def extract_search_query(analysis_response, user_message):
    """
    Extract search query from AI analysis or use user message as fallback
    """
    if not analysis_response:
        return user_message
    
    # Look for suggested search query in the analysis
    import re
    
    # Try to find "Search: " followed by query
    search_match = re.search(r'Search:\s*["\']?([^"\'.\n]+)["\']?', analysis_response, re.IGNORECASE)
    if search_match:
        suggested_query = search_match.group(1).strip()
        if suggested_query:
            logger.info(f"Using AI suggested search query: {suggested_query}")
            return suggested_query
    
    # Fallback to original user message
    logger.info(f"Using original user message as search query: {user_message}")
    return user_message


def generate_contextual_response(user_message, search_results):
    """
    Step 3: Generate final response using search context
    """
    system_prompt = """You are a helpful LINE bot assistant. The user asked a question and I've gathered some recent web search results for you.

Use the search results to provide a helpful, accurate, and concise answer to the user's question. 
Keep your response under 300 characters when possible.
If the search results don't fully answer the question, acknowledge what you found and suggest they search for more specific terms."""

    context_message = f"User question: {user_message}\n\nSearch results:\n{search_results}\n\nPlease provide a helpful response based on this information."
    
    response = call_openrouter_api(system_prompt, context_message, max_tokens=200)
    return response if response else search_results  # Fallback to raw search results


def call_openrouter_api(system_prompt, user_message, max_tokens=150):
    """
    Helper function to call OpenRouter API
    """
    if not OPENROUTER_API_KEY:
        return None
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://your-line-bot.com",
        "X-Title": "LINE Bot"
    }
    
    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=15)
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def generate_ai_response_http(user_message):
    """
    Generate AI response using direct HTTP request to OpenRouter
    """
    if not OPENROUTER_API_KEY:
        return None
        
    system_prompt = """You are a helpful and friendly LINE bot assistant. 
    Keep your responses concise (under 200 characters when possible) and engaging.
    Be helpful, informative, and maintain a conversational tone.
    If you don't know something, admit it honestly."""
    
    ai_message = call_openrouter_api(system_prompt, user_message, max_tokens=150)
    if ai_message:
        logger.info(f"OpenRouter response generated successfully via HTTP request")
    return ai_message


def perform_search(query, topic=None):
    """
    Perform DuckDuckGo search and return summarized results
    """
    try:
        logger.info(f"Performing search for: {query}")
        
        # Get search settings
        settings = SEARCH_CONFIG.get('search_settings', {})
        max_results = settings.get('max_results', 3)
        summary_length = settings.get('summary_length', 300)
        
        # Perform search using DuckDuckGo
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))
        
        if not results:
            return f"I couldn't find any results for '{query}'. Try a different search term!"
        
        # Format results
        response_parts = [f"🔍 Search results for '{query}':\n"]
        
        for i, result in enumerate(results[:max_results], 1):
            title = result.get('title', 'No title')[:80]
            snippet = result.get('body', 'No description')[:summary_length]
            url = result.get('href', '')
            
            # Clean up snippet
            snippet = clean_text(snippet)
            
            response_parts.append(f"{i}. {title}\n{snippet}...\n")
        
        response = '\n'.join(response_parts)
        
        # Limit total response length for LINE (max ~2000 chars)
        if len(response) > 1800:
            response = response[:1800] + "...\n\n💡 Try more specific search terms for better results!"
        
        return response
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Sorry, I encountered an error while searching for '{query}'. Please try again later."


def clean_text(text):
    """
    Clean and format text for better readability
    """
    if not text:
        return ""
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove HTML entities and tags if any
    text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    
    return text


# Health check endpoint
def health_check():
    """
    Simple health check function
    """
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'healthy', 'service': 'LINE Bot'})
    }
