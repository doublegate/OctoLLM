#!/bin/bash
# Test Ollama local LLM inference

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [ -f .env.unraid ]; then
    set -a
    source .env.unraid
    set +a
fi

HOST_IP=${HOST_IP:-192.168.4.6}
OLLAMA_URL="http://$HOST_IP:3014"

echo "Testing Ollama service..."

# Test connection
if ! curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo -e "${RED}[FAIL]${NC} Cannot connect to Ollama at $OLLAMA_URL"
    exit 1
fi

echo -e "${GREEN}[PASS]${NC} Ollama is running"

# List available models
echo ""
echo "Available models:"
curl -s "$OLLAMA_URL/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "  (unable to parse model list)"

# Test simple inference
echo ""
echo "Testing inference with llama3.1:8b..."

RESPONSE=$(curl -s "$OLLAMA_URL/api/generate" -d '{
  "model": "llama3.1:8b",
  "prompt": "Say hello in one word.",
  "stream": false
}')

if echo "$RESPONSE" | jq -e '.response' > /dev/null 2>&1; then
    echo -e "${GREEN}[PASS]${NC} Inference successful"
    echo "Response: $(echo "$RESPONSE" | jq -r '.response')"
else
    echo -e "${RED}[FAIL]${NC} Inference failed"
    echo "$RESPONSE"
    exit 1
fi

echo ""
echo -e "${GREEN}All Ollama tests passed!${NC}"
