import os

api_key = os.getenv('LANGCHAIN_API_KEY')

if api_key:
    print(f"API_KEY is set: {api_key}")
else:
    print("API_KEY is not set.")
