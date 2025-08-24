# Bybit Credentials Setup

This folder contains API credentials for Bybit integration. All credential files are automatically ignored by git for security.

## Required Files

### 1. Demo Trading Credentials
Create `bybit_demo.yaml` with your Bybit demo trading API credentials:

```yaml
api_key: "your_demo_api_key"
api_secret: "your_demo_api_secret"
```

## Getting Bybit Demo API Credentials

1. **Sign up for Bybit**: Visit [bybit.com](https://www.bybit.com) and create an account
2. **Access Demo Trading**: Navigate to Demo Trading section
3. **Generate API Keys**: 
   - Go to API Management in your demo account
   - Create new API key with trading permissions
   - Copy the API Key and Secret

## Security Notes

- **Never commit credentials to git** - they are automatically ignored
- **Use demo API keys only** - never use live trading keys for development
- **Store credentials securely** - consider using environment variables in production

## Configuration

The realtime trading system will automatically load credentials from this folder. Ensure the file names match exactly:
- `bybit_demo.yaml` - Demo trading API credentials

## Testing Connection

After setting up credentials, test the connection with:
```bash
python examples/test_bybit_connection.py
```