"""Quick check of the configured AI provider.

Usage:  venv\Scripts\python.exe scripts\test_provider.py "My maize has yellow leaves"
"""
import sys

from app.services.ai import ask_ai

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Hello"
    print(f"Provider: {__import__('app.config', fromlist=['AI_PROVIDER']).AI_PROVIDER}")
    print(f"Q: {question}")
    print(f"A: {ask_ai(question)}")