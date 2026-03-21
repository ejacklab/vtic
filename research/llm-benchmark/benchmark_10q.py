#!/usr/bin/env python3
"""
LLM Benchmark Script - 10 Questions
Tests 6 models with 10 questions and measures latency + accuracy.
"""

import json
import time
import requests
import re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load API keys from secrets
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
with open(SECRETS_PATH) as f:
    secrets = json.load(f)

API_KEYS = {
    "zai": secrets["provider"]["zai"]["key"],
    "alibaba": secrets["provider"]["alibaba"]["key"],
    "moonshot": secrets["provider"]["moonshot"]["key"],
}

# Model configurations
MODELS = [
    {
        "name": "zai/glm-5",
        "provider": "zai",
        "base_url": "https://api.z.ai/api/coding/paas/v4",
        "model": "glm-5",
        "timeout": 60,
    },
    {
        "name": "moonshot/kimi-k2.5",
        "provider": "moonshot",
        "base_url": "https://api.moonshot.ai/v1",
        "model": "kimi-k2.5",
        "timeout": 45,
    },
    {
        "name": "modelstudio/glm-5",
        "provider": "alibaba",
        "base_url": "https://coding-intl.dashscope.aliyuncs.com/v1",
        "model": "glm-5",
        "timeout": 120,  # Known to be slow
    },
    {
        "name": "modelstudio/MiniMax-M2.5",
        "provider": "alibaba",
        "base_url": "https://coding-intl.dashscope.aliyuncs.com/v1",
        "model": "MiniMax-M2.5",
        "timeout": 60,
    },
    {
        "name": "modelstudio/kimi-k2.5",
        "provider": "alibaba",
        "base_url": "https://coding-intl.dashscope.aliyuncs.com/v1",
        "model": "kimi-k2.5",
        "timeout": 45,
    },
    # Note: minimax-portal uses OAuth, not API key - cannot test via direct HTTP
    # Test via OpenClaw subagents instead
]

# 10 Questions
QUESTIONS = """Answer these 10 questions. Reply with just the answers, numbered 1-10:

1. How much is 1 + 1?
2. What country is next to Singapore?
3. What is the speed of light?
4. How big is Japan?
5. How many colors in a rainbow?
6. How many data types in Python?
7. Gmail have how many "a" in this word?
8. Baby call her Grandpa's Son as what?
9. If Answer is 21 year old this year (2026), when he was born?
10. 30% of RM90 is how much?"""


def call_model(model_config: dict) -> dict:
    """Call a model and return results."""
    provider = model_config["provider"]
    api_key = API_KEYS.get(provider)
    
    if not api_key:
        return {
            "status": "error",
            "latency": 0,
            "error": f"No API key for provider: {provider}",
        }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model_config["model"],
        "messages": [{"role": "user", "content": QUESTIONS}],
        "max_tokens": 1500,
        # Note: Removed temperature - some APIs don't support it
    }
    
    timeout = model_config.get("timeout", 60)
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{model_config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "status": "success",
                "latency": elapsed,
                "response": content,
            }
        else:
            return {
                "status": "error",
                "latency": elapsed,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }
    except requests.Timeout:
        elapsed = time.time() - start_time
        return {
            "status": "timeout",
            "latency": elapsed,
            "error": f"Request timed out ({timeout}s)",
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "status": "error",
            "latency": elapsed,
            "error": str(e),
        }


def check_accuracy(response: str) -> dict:
    """Check accuracy of tricky questions (7-10)."""
    response_lower = response.lower()
    results = {}
    
    # Q7: "a" in Gmail - correct answer is 1
    # Look for explicit mentions of the count
    q7_patterns = [
        r'gmail[^.]*?(\d+)\s*["\']?a["\']?',  # "gmail has 1 a"
        r'(\d+)\s*["\']?a["\']?\s*in\s*gmail',  # "1 a in gmail"
        r'answer[:\s]+(\d+)',  # "answer: 1"
        r'q7[^:]*:(\d+)',  # "Q7: 1"
        r'7\.\s*(\d+)',  # "7. 1"
    ]
    
    q7_answer = None
    for pattern in q7_patterns:
        match = re.search(pattern, response_lower)
        if match:
            q7_answer = match.group(1)
            break
    
    if q7_answer == "1":
        results[7] = True
    elif q7_answer in ["0", "2", "3"]:
        results[7] = False
    else:
        # Fallback: look for "1" near mentions of gmail/a
        if "gmail" in response_lower:
            # Extract the line or section about gmail
            gmail_section = re.search(r'gmail[^\n]*', response_lower)
            if gmail_section and "1" in gmail_section.group(0):
                results[7] = True
            elif gmail_section and re.search(r'[02-9]', gmail_section.group(0)):
                results[7] = False
            else:
                results[7] = None
        else:
            results[7] = None
    
    # Q8: Dad/Father/Uncle - both are correct
    has_dad = any(x in response_lower for x in ["dad", "father"])
    has_uncle = "uncle" in response_lower
    
    if has_dad:
        results[8] = True
    elif has_uncle:
        results[8] = "partial"
    else:
        results[8] = False
    
    # Q9: Born year - 2005 is correct (2026 - 21)
    if "2005" in response:
        results[9] = True
    elif "2004" in response:
        results[9] = "partial"
    else:
        results[9] = False
    
    # Q10: 30% of RM90 = 27
    if "27" in response:
        results[10] = True
    else:
        results[10] = False
    
    return results


def run_benchmark():
    """Run benchmark on all models."""
    print("=" * 70)
    print("LLM Benchmark - 10 Questions")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    results = []
    
    # Run sequentially to avoid rate limits
    for model in MODELS:
        print(f"Testing {model['name']}...", end=" ", flush=True)
        
        result = call_model(model)
        result["model"] = model["name"]
        
        if result["status"] == "success":
            accuracy = check_accuracy(result["response"])
            result["accuracy"] = accuracy
            
            correct = sum(1 for v in accuracy.values() if v == True)
            partial = sum(1 for v in accuracy.values() if v == "partial")
            result["score"] = f"{correct + partial * 0.5:.1f}/4"
            result["correct"] = correct
            result["partial"] = partial
            
            print(f"✅ {result['latency']:.1f}s | Score: {result['score']}")
        else:
            print(f"❌ {result['status']} | {result.get('error', '')[:50]}")
        
        results.append(result)
        print()
    
    # Summary table
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Model':<30} {'Time':<10} {'Score':<10} {'Status'}")
    print("-" * 70)
    
    # Sort by latency
    successful = [r for r in results if r["status"] == "success"]
    successful.sort(key=lambda x: x["latency"])
    
    for r in successful:
        print(f"{r['model']:<30} {r['latency']:<10.1f} {r['score']:<10} ✅")
    
    for r in results:
        if r["status"] != "success":
            print(f"{r['model']:<30} {'N/A':<10} {'N/A':<10} ❌ {r.get('error', '')[:30]}")
    
    print()
    
    # Accuracy breakdown
    if successful:
        print("=" * 70)
        print("ACCURACY BREAKDOWN (Tricky Questions 7-10)")
        print("=" * 70)
        print()
        print(f"{'Model':<30} {'Q7 (1a)':<10} {'Q8 (Dad)':<12} {'Q9 (2005)':<12} {'Q10 (27)'}")
        print("-" * 80)
        
        for r in successful:
            acc = r.get("accuracy", {})
            q7 = "✅" if acc.get(7) == True else ("❓" if acc.get(7) is None else "❌")
            q8 = "✅" if acc.get(8) == True else ("🔶" if acc.get(8) == "partial" else "❌")
            q9 = "✅" if acc.get(9) == True else ("🔶" if acc.get(9) == "partial" else "❌")
            q10 = "✅" if acc.get(10) == True else "❌"
            print(f"{r['model']:<30} {q7:<10} {q8:<12} {q9:<12} {q10}")
    
    # Full responses (for debugging)
    print("\n" + "=" * 70)
    print("FULL RESPONSES (for debugging)")
    print("=" * 70)
    
    for r in successful:
        print(f"\n--- {r['model']} ({r['latency']:.1f}s) ---")
        print(r['response'][:500] + "..." if len(r['response']) > 500 else r['response'])
    
    # Save results
    output_path = Path(__file__).parent / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print()
    print(f"\nResults saved to: {output_path}")
    
    return results


if __name__ == "__main__":
    run_benchmark()
