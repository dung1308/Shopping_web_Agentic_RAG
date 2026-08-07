"""
scripts/check_all_connections.py — Terminal CLI diagnostic tool.
Verifies connections to Neon PostgreSQL, Redis, OpenAI, Gemini, Anthropic, Ollama, ChromaDB, and Embedding Server.
"""

import sys
import asyncio
import time
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

async def run_diagnostics():
    print(f"\n{BOLD}{CYAN}========================================================================{RESET}")
    print(f"{BOLD}{CYAN} 🛠️  MALL AGENTIC RAG — SERVICE CONNECTION SETUP DIAGNOSTICS {RESET}")
    print(f"{BOLD}{CYAN}========================================================================{RESET}\n")

    try:
        from backend.api.routers.diagnostics import check_all_connections
    except Exception as exc:
        print(f"{RED}❌ Failed to import diagnostic module: {exc}{RESET}")
        return

    print("🔎 Probing service endpoints in parallel...\n")
    start_total = time.perf_counter()
    report = await check_all_connections()
    total_elapsed = round((time.perf_counter() - start_total) * 1000, 2)

    services = report.get("services", {})
    
    # Table Header
    print(f"{'SERVICE':<28} | {'STATUS':<16} | {'LATENCY':<10} | {'DETAILS'}")
    print("-" * 80)

    for key, info in services.items():
        provider = info.get("provider", key)
        status = info.get("status", "unknown")
        latency = f"{info.get('latency_ms', 0)} ms"
        details = info.get("details", {})
        
        if status == "connected":
            status_str = f"{GREEN}✅ CONNECTED{RESET}"
        elif status == "warning":
            status_str = f"{YELLOW}⚠️  WARNING{RESET}"
        elif status == "not_configured":
            status_str = f"{YELLOW}⚪ NOT CONFIGURED{RESET}"
        else:
            status_str = f"{RED}❌ FAILED{RESET}"

        # Format details string
        if "is_neon" in details and details["is_neon"]:
            detail_str = f"Neon DB ({details.get('database')})"
        elif "base_url" in details:
            detail_str = f"{details['base_url']} ({details.get('configured_model', details.get('model', ''))})"
        elif "available_models" in details:
            detail_str = f"Models: {', '.join(details['available_models'][:3])}"
        elif "collections" in details:
            cols = [c['name'] for c in details['collections']]
            detail_str = f"Collections: {', '.join(cols) if cols else 'none'}"
        elif "redis_version" in details:
            detail_str = f"Redis v{details['redis_version']}"
        elif "message" in details:
            detail_str = details["message"]
        elif "error" in details:
            detail_str = f"Error: {details['error'][:35]}..."
        else:
            detail_str = str(details)

        print(f"{provider:<28} | {status_str:<25} | {latency:<10} | {detail_str}")

    print("-" * 80)
    print(f"\n{BOLD}Overall System Status:{RESET} ", end="")
    overall = report.get("overall_status")
    if overall == "healthy":
        print(f"{GREEN}{BOLD}HEALTHY (All configured services online){RESET}")
    elif overall == "degraded":
        print(f"{YELLOW}{BOLD}DEGRADED (Some optional cloud services or servers offline){RESET}")
    else:
        print(f"{RED}{BOLD}UNHEALTHY (Core database or cache offline){RESET}")

    print(f"⏱️ Total diagnostic runtime: {total_elapsed} ms\n")

    # Display Troubleshooting / Actionable Fixes if any service failed or warnings
    fix_needed = [s for s in services.values() if s.get("fix_hint")]
    if fix_needed:
        print(f"{BOLD}{YELLOW}💡 ACTIONABLE FIX RECOMMENDATIONS:{RESET}")
        for s in fix_needed:
            print(f"  • {BOLD}{s['provider']}{RESET}: {s['fix_hint']}")
        print()

    print(f"{CYAN}💡 Tip: Launch backend (`uvicorn backend.main:app --port 8000`) and open {RESET}")
    print(f"{CYAN}   http://localhost:8000/connection_status.html for the interactive GUI demo!{RESET}\n")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
