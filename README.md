# LINE Bot Lambda Deployment

This project contains a Python LINE Bot that runs on AWS Lambda using the Serverless Application Model (SAM).

## Prerequisites

1. **LINE Developer Account**: Create a LINE Bot at [LINE Developers Console](https://developers.line.biz/)
2. **AWS Account**: Set up AWS credentials
3. **AWS SAM CLI**: Install the SAM CLI for deployment
4. **Python 3.11**: Required for the Lambda runtime
5. **OpenRouter API Key** (Optional): Get your API key from [OpenRouter](https://openrouter.ai/) for AI-powered responses

## Setup Instructions

### 1. LINE Bot Configuration

1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Create a new channel (Messaging API)
3. Get your **Channel Access Token** and **Channel Secret**
4. Set the webhook URL (will be provided after deployment)

### 2. Install Dependencies

```bash
# Install AWS SAM CLI
pip install aws-sam-cli

# Install local dependencies (for testing)
pip install -r requirements.txt
```

### 3. Deploy to AWS Lambda

```bash
# Build the application
sam build

# Deploy with guided setup (first time)
sam deploy --guided

# For subsequent deployments
sam deploy
```

During the guided deployment, you'll be prompted to enter:

- **ChannelAccessToken**: Your LINE Channel Access Token
- **ChannelSecret**: Your LINE Channel Secret
- **OpenRouterApiKey**: Your OpenRouter API Key (optional - leave empty for keyword-only responses)
- **OpenRouterModel**: AI model to use (default: anthropic/claude-3.5-sonnet)

### 4. Configure LINE Webhook

After deployment, you'll get an API Gateway URL. Use this URL with `/webhook` path as your LINE Bot webhook URL:

```
https://your-api-id.execute-api.region.amazonaws.com/Prod/webhook
```

### 5. OpenRouter Setup (Optional)

For AI-powered responses:

1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Get your API key from the dashboard
3. Choose your preferred model:
   - `anthropic/claude-3.5-sonnet` (recommended)
   - `openai/gpt-4o`
   - `meta-llama/llama-3.1-8b-instruct`
   - Many others available

If you don't provide an OpenRouter API key, the bot will use keyword-based responses.

## Project Structure

```
line-bot-lambda/
├── app.py              # Main Lambda function
├── requirements.txt    # Python dependencies
├── template.yaml       # SAM template for AWS resources
├── README.md          # This file
└── deploy.sh          # Deployment script
```

## Features

- **AI-Powered Responses**: Uses OpenRouter API for intelligent conversations
- **Fallback System**: Falls back to keyword-based responses if AI is unavailable
- **Multiple AI Models**: Support for various models (Claude, GPT, Llama, etc.)
- **Error Handling**: Robust error handling and logging
- **Security**: Signature validation for LINE webhooks
- **Health Check**: `/health` endpoint for monitoring

## Customization

### Adding New Response Logic

Edit the `generate_response()` function in `app.py`:

```python
def generate_response(user_message):
    user_message_lower = user_message.lower()

    # Add your custom logic here
    if 'your_keyword' in user_message_lower:
        return "Your custom response"

    # ... existing logic
```

### Adding AI/ML Capabilities

You can integrate with services like:

- **Amazon Bedrock**: For AI-powered responses
- **Amazon Comprehend**: For sentiment analysis
- **Amazon Translate**: For multi-language support

Example integration with Bedrock:

```python
import boto3

def generate_ai_response(user_message):
    bedrock = boto3.client('bedrock-runtime')
    # Add Bedrock integration here
    pass
```

## Environment Variables

- `CHANNEL_ACCESS_TOKEN`: LINE Channel Access Token
- `CHANNEL_SECRET`: LINE Channel Secret
- `OPENROUTER_API_KEY`: OpenRouter API Key (optional)
- `OPENROUTER_MODEL`: AI model to use (default: anthropic/claude-3.5-sonnet)

## Monitoring and Logs

- **CloudWatch Logs**: View Lambda function logs
- **X-Ray Tracing**: Enable for detailed tracing (optional)
- **Health Check**: Use `/health` endpoint for uptime monitoring

## Cost Optimization

- **Memory**: Currently set to 128MB (adjust in `template.yaml`)
- **Timeout**: Set to 30 seconds (adjust based on needs)
- **Cold Starts**: Consider provisioned concurrency for high-traffic bots

## Security Best Practices

- ✅ Signature validation implemented
- ✅ Environment variables for secrets
- ✅ Error handling without exposing sensitive information
- ✅ Input validation

## Troubleshooting

### Common Issues

1. **Invalid Signature Error**

   - Check your Channel Secret is correct
   - Ensure the webhook URL is exactly as configured

2. **LINE Bot API Errors**

   - Verify Channel Access Token
   - Check token permissions and expiration

3. **Lambda Timeout**
   - Increase timeout in `template.yaml`
   - Optimize response generation logic

### Testing Locally

```bash
# Start local API
sam local start-api

# Test with curl
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"events": []}'
```

## Resources

- [LINE Messaging API Documentation](https://developers.line.biz/en/docs/messaging-api/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [LINE Bot SDK for Python](https://github.com/line/line-bot-sdk-python)
