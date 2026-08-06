"""
scripts/reset_chroma.py — Utility to clear all vectors and collections in ChromaDB.
"""

import sys
import os
import shutil
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import get_settings

async def reset_chroma_data():
    settings = get_settings()
    print("🧹 Resetting ChromaDB vector storage...")
    
    # 1. Reset via Chroma API if chromadb module is installed
    try:
        from backend.vector.chroma_client import ChromaVectorClient
        client = ChromaVectorClient()
        collection_name = settings.chroma_collection
        try:
            await client.delete_collection(collection_name)
            print(f"✅ Deleted collection via API: '{collection_name}'")
        except Exception as e:
            print(f"ℹ️ Collection '{collection_name}' was not present or already cleared.")
    except ModuleNotFoundError:
        print("ℹ️ Note: `chromadb` python package not found in this environment. Proceeding with disk directory cleanup...")
    except Exception as err:
        print(f"⚠️ API reset note: {err}")
        
    # 2. Clean local disk database directory
    data_dir = settings.chroma_path
    if os.path.exists(data_dir):
        try:
            shutil.rmtree(data_dir, ignore_errors=True)
            print(f"✅ Removed local disk database directory: '{data_dir}'")
        except Exception as err:
            print(f"⚠️ Could not delete directory {data_dir}: {err}")
    else:
        print(f"ℹ️ ChromaDB directory '{data_dir}' is clean (0 items).")

    print("🎉 ChromaDB successfully reset! Ready for fresh data ingestion.")

if __name__ == "__main__":
    asyncio.run(reset_chroma_data())
