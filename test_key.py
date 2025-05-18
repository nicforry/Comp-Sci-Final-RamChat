import os
from openai import OpenAI
from dotenv import load_dotenv

# Load your API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Use new OpenAI client
client = OpenAI(api_key=api_key)

# Ask ChatGPT something
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "Hello, who are you?"}
    ]
)

# Print the reply
print(response.choices[0].message.content)
