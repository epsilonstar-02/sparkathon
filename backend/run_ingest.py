#!/usr/bin/env python3
"""
Script to run data ingestion.
Usage: python run_ingest.py
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ingest import main

if __name__ == "__main__":
    asyncio.run(main())