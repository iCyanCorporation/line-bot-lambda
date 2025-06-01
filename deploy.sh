#!/bin/bash

# LINE Bot Lambda Deployment Script

set -e

echo "🚀 Starting LINE Bot deployment..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI is not installed. Please install it first:"
    echo "pip install aws-sam-cli"
    exit 1
fi

# Build the application
echo "📦 Building the application..."
sam build

# Check if this is the first deployment or if we need to update parameters
if [ ! -f "samconfig.toml" ]; then
    echo "🔧 First time deployment - running guided setup..."
    sam deploy --guided
elif ! grep -q "OpenRouterApiKey" samconfig.toml 2>/dev/null; then
    echo "🔧 New parameters detected - running guided setup to configure OpenRouter..."
    echo "💡 You'll be prompted for the new OpenRouter API key and model settings."
    sam deploy --guided
else
    echo "🔄 Deploying with existing configuration..."
    sam deploy
fi

# Get the webhook URL
echo "📋 Getting deployment information..."
WEBHOOK_URL=$(aws cloudformation describe-stacks \
    --stack-name sam-app \
    --query 'Stacks[0].Outputs[?OutputKey==`LineBotApi`].OutputValue' \
    --output text 2>/dev/null || echo "Could not retrieve webhook URL")

echo ""
echo "✅ Deployment completed!"
echo ""
echo "📝 Next steps:"
echo "1. Copy this webhook URL to your LINE Developer Console:"
echo "   ${WEBHOOK_URL}"
echo ""
echo "2. Test your bot by sending a message in LINE"
echo ""
echo "3. View logs with:"
echo "   sam logs -n LineBotFunction --stack-name line-bot-lambda --tail"
echo ""
echo "4. To update the bot, just run this script again!"
