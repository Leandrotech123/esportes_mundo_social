import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("ERRO: Configure ANTHROPIC_API_KEY no arquivo .env")
    exit(1)

client = anthropic.Anthropic(api_key=api_key)
r = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=100,
    messages=[{"role": "user", "content": "Responda só: API Anthropic funcionando para esportes_mundo_social!"}]
)
print(r.content[0].text)
