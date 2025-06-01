#!/bin/bash

# LINE Bot Configuration Script

echo "🔧 LINE Bot Configuration"
echo ""

# Check if samconfig.toml exists
if [ ! -f "samconfig.toml" ]; then
    echo "❌ samconfig.toml not found. Please run deploy.sh first."
    exit 1
fi

echo "This script will help you configure your LINE Bot credentials and OpenRouter API."
echo ""
echo "⚠️  Note: If you don't have LINE Bot credentials yet, you can still deploy with empty values"
echo "   and the bot will work for testing purposes (signature validation disabled)."
echo ""

# Get LINE Bot credentials
read -p "Enter your LINE Channel Access Token (or press Enter to skip): " CHANNEL_ACCESS_TOKEN
read -p "Enter your LINE Channel Secret (or press Enter to skip): " CHANNEL_SECRET

# Get OpenRouter model
echo ""
echo "Available models:"
echo "1. anthropic/claude-3.5-sonnet (recommended)"
echo "2. openai/gpt-4o" 
echo "3. meta-llama/llama-3.1-8b-instruct"
echo "4. google/gemini-pro"
echo "5. Custom model"
echo ""
read -p "Select model (1-5) or press Enter for default [1]: " MODEL_CHOICE

case $MODEL_CHOICE in
    1|"") OPENROUTER_MODEL="anthropic/claude-3.5-sonnet" ;;
    2) OPENROUTER_MODEL="openai/gpt-4o" ;;
    3) OPENROUTER_MODEL="meta-llama/llama-3.1-8b-instruct" ;;
    4) OPENROUTER_MODEL="google/gemini-pro" ;;
    5) 
        read -p "Enter custom model name: " OPENROUTER_MODEL
        ;;
    *) OPENROUTER_MODEL="anthropic/claude-3.5-sonnet" ;;
esac

echo ""
echo "📝 Updating configuration..."

# Get existing parameters from samconfig.toml
EXISTING_PARAMS=$(grep 'parameter_overrides' samconfig.toml | cut -d'"' -f2)

# Extract existing values
CHANNEL_ACCESS_TOKEN=""
CHANNEL_SECRET=""
if [[ $EXISTING_PARAMS == *"ChannelAccessToken="* ]]; then
    CHANNEL_ACCESS_TOKEN=$(echo "$EXISTING_PARAMS" | grep -o 'ChannelAccessToken="[^"]*"' | cut -d'"' -f2)
fi
if [[ $EXISTING_PARAMS == *"ChannelSecret="* ]]; then
    CHANNEL_SECRET=$(echo "$EXISTING_PARAMS" | grep -o 'ChannelSecret="[^"]*"' | cut -d'"' -f2)
fi

# Update samconfig.toml with new parameters
# Escape special characters for sed
ESCAPED_CHANNEL_ACCESS_TOKEN=$(printf '%s\n' "$CHANNEL_ACCESS_TOKEN" | sed 's/[[\.*^$()+?{|]/\\&/g')
ESCAPED_CHANNEL_SECRET=$(printf '%s\n' "$CHANNEL_SECRET" | sed 's/[[\.*^$()+?{|]/\\&/g')
ESCAPED_OPENROUTER_API_KEY=$(printf '%s\n' "$OPENROUTER_API_KEY" | sed 's/[[\.*^$()+?{|]/\\&/g')
ESCAPED_OPENROUTER_MODEL=$(printf '%s\n' "$OPENROUTER_MODEL" | sed 's/[[\.*^$()+?{|]/\\&/g')

sed -i "s|parameter_overrides = .*|parameter_overrides = \"ChannelAccessToken=\\\"$ESCAPED_CHANNEL_ACCESS_TOKEN\\\" ChannelSecret=\\\"$ESCAPED_CHANNEL_SECRET\\\" OpenRouterApiKey=\\\"$ESCAPED_OPENROUTER_API_KEY\\\" OpenRouterModel=\\\"$ESCAPED_OPENROUTER_MODEL\\\"\"|g" samconfig.toml

echo "✅ Configuration updated!"
echo ""
echo "📋 Current settings:"
echo "- OpenRouter API Key: ${OPENROUTER_API_KEY:0:10}..." 
echo "- OpenRouter Model: $OPENROUTER_MODEL"
echo ""
echo "🚀 Now run './deploy.sh' to deploy with OpenRouter integration!"
