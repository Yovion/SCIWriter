#!/usr/bin/env python3
"""
SCIWriter LLM Client

Unified LLM API interface for all SCIWriter scripts.
Currently supports: Anthropic Claude
Future support: OpenAI, Local LLM

Usage:
    from llm_client import call, call_json, is_available

    if is_available():
        response = call("Your prompt here")
        data = call_json("Your prompt requesting JSON")
"""

import os
import sys
import json
import time
import yaml
from pathlib import Path


# ============================================================================
# Configuration Loading
# ============================================================================

def load_config():
    """
    Load LLM configuration from config/llm_config.yaml.

    Returns:
        dict: Configuration dictionary

    Raises:
        FileNotFoundError: If config file not found
    """
    # Find config file
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config" / "llm_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"LLM config file not found: {config_path}\n"
            f"Please create config/llm_config.yaml"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


# Global config (loaded once)
try:
    _CONFIG = load_config()
    _LLM_CONFIG = _CONFIG.get("llm", {})
except Exception as e:
    print(f"⚠️  Warning: Failed to load LLM config: {e}", file=sys.stderr)
    _CONFIG = {}
    _LLM_CONFIG = {}


# ============================================================================
# API Key Management
# ============================================================================

def get_api_key():
    """
    Get API key from environment variable.

    Returns:
        str: API key or None if not set

    Raises:
        ValueError: If api_key_env not configured
    """
    api_key_env = _LLM_CONFIG.get("api_key_env")

    if not api_key_env:
        raise ValueError(
            "api_key_env not configured in llm_config.yaml"
        )

    api_key = os.environ.get(api_key_env)

    return api_key


def is_available():
    """
    Check if LLM is available (API key configured).

    Returns:
        bool: True if LLM can be used
    """
    try:
        api_key = get_api_key()
        return api_key is not None and len(api_key) > 0
    except Exception:
        return False


def get_provider():
    """
    Get current LLM provider name.

    Returns:
        str: "anthropic", "openai", "local", or "none"
    """
    if not is_available():
        return "none"

    return _LLM_CONFIG.get("provider", "none")


# ============================================================================
# Anthropic Claude API
# ============================================================================

def call_anthropic(prompt, max_tokens=None, temperature=None):
    """
    Call Anthropic Claude API.

    Args:
        prompt: Input prompt
        max_tokens: Override default max_tokens
        temperature: Override default temperature

    Returns:
        str: Generated text

    Raises:
        ImportError: If anthropic package not installed
        Exception: If API call fails
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic package not installed.\n"
            "Install with: pip install anthropic"
        )

    # Get API key
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            f"API key not found in environment variable: {_LLM_CONFIG.get('api_key_env')}\n"
            f"Set it with: export {_LLM_CONFIG.get('api_key_env')}='your-api-key'"
        )

    # Get parameters
    model = _LLM_CONFIG.get("model", "claude-sonnet-4-20250514")
    max_tokens = max_tokens or _LLM_CONFIG.get("max_tokens", 4000)
    temperature = temperature or _LLM_CONFIG.get("temperature", 0.7)
    timeout = _LLM_CONFIG.get("timeout", 60)
    base_url = _LLM_CONFIG.get("base_url", "").strip()

    # Create client with optional base_url
    if base_url:
        # Use custom base URL (e.g., proxy or custom endpoint)
        client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
    else:
        # Use official Anthropic API
        client = anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout
        )

    # Call API
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Extract text
    return message.content[0].text


# ============================================================================
# Unified Interface
# ============================================================================

class LLMNotAvailableError(Exception):
    """Raised when LLM is not available (API key not configured)."""
    pass


class LLMAPIError(Exception):
    """Raised when LLM API call fails."""
    pass


def call(prompt, max_tokens=None, temperature=None):
    """
    Call LLM and return text response.

    Args:
        prompt: Input prompt
        max_tokens: Override default max_tokens
        temperature: Override default temperature

    Returns:
        str: Generated text

    Raises:
        LLMNotAvailableError: If API key not configured
        LLMAPIError: If API call fails
    """
    if not is_available():
        raise LLMNotAvailableError(
            f"LLM not available. Please set environment variable: {_LLM_CONFIG.get('api_key_env', 'ANTHROPIC_API_KEY')}"
        )

    provider = get_provider()
    max_retries = _LLM_CONFIG.get("max_retries", 3)
    retry_delay = _LLM_CONFIG.get("retry_delay", 2)

    for attempt in range(max_retries):
        try:
            if provider == "anthropic":
                return call_anthropic(prompt, max_tokens, temperature)
            else:
                raise LLMAPIError(f"Unsupported provider: {provider}")

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  LLM API error (attempt {attempt+1}/{max_retries}): {e}", file=sys.stderr)
                time.sleep(retry_delay)
            else:
                raise LLMAPIError(f"LLM API call failed after {max_retries} attempts: {e}")


def _extract_json_from_text(text):
    """
    Try to extract the first complete JSON object or array from text.
    Handles: trailing content after JSON, markdown code fences, mixed text blocks.

    Returns:
        str: Extracted JSON string, or None if not found
    """
    import re

    # Strip markdown code fences first
    text = text.strip()
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try to find the first { or [ and extract the matching block
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
    return None


def call_json(prompt, max_retries=3):
    """
    Call LLM and return parsed JSON.

    Args:
        prompt: Input prompt (should request JSON output)
        max_retries: Number of retry attempts for JSON parsing

    Returns:
        dict or list: Parsed JSON data

    Raises:
        LLMNotAvailableError: If API key not configured
        LLMAPIError: If API call fails
        json.JSONDecodeError: If response is not valid JSON after all retries
    """
    if not is_available():
        raise LLMNotAvailableError(
            f"LLM not available. Please set environment variable: {_LLM_CONFIG.get('api_key_env', 'ANTHROPIC_API_KEY')}"
        )

    for attempt in range(max_retries):
        try:
            # Call LLM
            response = call(prompt)
            raw_response = response

            # Clean markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Try direct parse first
            try:
                data = json.loads(response)
                return data
            except json.JSONDecodeError as e:
                # If "Extra data" or similar, try extracting first JSON block
                extracted = _extract_json_from_text(raw_response)
                if extracted and extracted != response:
                    try:
                        data = json.loads(extracted)
                        print(f"ℹ️  JSON extracted from response with trailing content", file=sys.stderr)
                        return data
                    except json.JSONDecodeError:
                        pass
                raise

        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"⚠️  JSON parse error (attempt {attempt+1}/{max_retries}): {e}", file=sys.stderr)
                print(f"   Response preview: {response[:200]}...", file=sys.stderr)
            else:
                raise json.JSONDecodeError(
                    f"Failed to parse JSON after {max_retries} attempts: {e.msg}",
                    e.doc,
                    e.pos
                )


# ============================================================================
# Utility Functions
# ============================================================================

def get_config():
    """
    Get current LLM configuration.

    Returns:
        dict: Configuration dictionary
    """
    return _LLM_CONFIG.copy()


def print_status():
    """Print LLM client status (for debugging)."""
    print("=" * 60)
    print("SCIWriter LLM Client Status")
    print("=" * 60)

    if is_available():
        print(f"✓ LLM Available")
        print(f"  Provider: {get_provider()}")
        print(f"  Model: {_LLM_CONFIG.get('model', 'N/A')}")

        # Show base_url if configured
        base_url = _LLM_CONFIG.get('base_url', '').strip()
        if base_url:
            print(f"  Base URL: {base_url}")
        else:
            print(f"  Base URL: (official Anthropic API)")

        # Show API key status (not the actual key)
        api_key_env = _LLM_CONFIG.get('api_key_env', 'N/A')
        api_key = os.environ.get(api_key_env, '')
        if api_key:
            print(f"  API Key: {api_key_env} (set, {len(api_key)} chars)")
        else:
            print(f"  API Key: {api_key_env} (NOT SET)")
    else:
        print(f"✗ LLM Not Available")
        print(f"  Reason: API key not set")
        print(f"  Required: export {_LLM_CONFIG.get('api_key_env', 'ANTHROPIC_API_KEY')}='your-api-key'")

    print("=" * 60)


# ============================================================================
# Main (for testing)
# ============================================================================

def main():
    """Test LLM client."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test SCIWriter LLM Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check status
  python3 llm_client.py --status

  # Test simple call
  python3 llm_client.py --test-call

  # Test JSON call
  python3 llm_client.py --test-json
        """
    )
    parser.add_argument("--status", action="store_true", help="Print LLM status")
    parser.add_argument("--test-call", action="store_true", help="Test simple LLM call")
    parser.add_argument("--test-json", action="store_true", help="Test JSON LLM call")

    args = parser.parse_args()

    if args.status or (not args.test_call and not args.test_json):
        print_status()
        return

    if args.test_call:
        print("\nTesting simple LLM call...")
        try:
            response = call("Say 'Hello from SCIWriter LLM Client!' in one sentence.")
            print(f"✓ Success!")
            print(f"Response: {response}")
        except Exception as e:
            print(f"✗ Failed: {e}")

    if args.test_json:
        print("\nTesting JSON LLM call...")
        try:
            prompt = """Output a JSON object with two fields:
{
  "message": "Hello from JSON test",
  "status": "success"
}

Output ONLY the JSON, no explanation."""

            data = call_json(prompt)
            print(f"✓ Success!")
            print(f"Response: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"✗ Failed: {e}")


if __name__ == "__main__":
    main()
