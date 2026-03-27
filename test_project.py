import os
import sys
import importlib
import traceback
from pathlib import Path

def test_imports():
    print("\n--- 1. Checking Files ---")
    expected_files = [
        "config/settings.py",
        "hunter/gazette_hunter.py",
        "hunter/downloader.py",
        "hunter/keyword_filter.py",
        "parser/pdf_parser.py",
        "parser/metadata_extractor.py",
        "parser/normalizer.py",
        "brain/prompts.py",
        "brain/map_analyzer.py",
        "brain/reduce_synthesizer.py",
        "brain/intelligence_engine.py",
        "memory/schema.py",
        "memory/embedder.py",
        "memory/vector_store.py",
        "memory/portfolio_manager.py",
        "radar/email_formatter.py",
        "radar/whatsapp_notifier.py",
        "radar/alert_engine.py",
        "radar/orchestrator.py",
        "radar/scheduler.py",
        "radar/dashboard.py",
        "main.py",
        "requirements.txt",
        "data/chroma_db/.gitkeep",
        "data/intelligence_reports/.gitkeep",
        "data/portfolio_seed.json",
        "templates/alert_email.html"
    ]
    
    all_files_exist = True
    for f in expected_files:
        if not os.path.exists(f):
            print(f"❌ Missing file: {f}")
            all_files_exist = False
        else:
            code = "✅" if ".py" in f else "📄"
            print(f"{code} Exists: {f}")
    
    if all_files_exist:
        print("✅ All expected files and directories exist.")

    print("\n--- 2. Validating config/settings.py ---")
    try:
        from config.settings import get_settings
        # Remove env variables if they exist in the process implicitly
        if "GOOGLE_API_KEY" in os.environ: del os.environ["GOOGLE_API_KEY"]
        if "OPENAI_API_KEY" in os.environ: del os.environ["OPENAI_API_KEY"]
        if "LLAMA_CLOUD_API_KEY" in os.environ: del os.environ["LLAMA_CLOUD_API_KEY"]
        if "TWILIO_ACCOUNT_SID" in os.environ: del os.environ["TWILIO_ACCOUNT_SID"]
        if "TWILIO_AUTH_TOKEN" in os.environ: del os.environ["TWILIO_AUTH_TOKEN"]
        
        settings = get_settings()
        print("✅ config/settings.py loaded successfully without API keys.")
    except Exception as e:
        print(f"❌ config/settings.py failed to load: {e}")
        traceback.print_exc()

    print("\n--- 3. Testing Module Imports ---")
    # All python modules in the project
    modules_to_test = [
        "config.settings",
        "hunter.gazette_hunter",
        "hunter.downloader",
        "hunter.keyword_filter",
        "parser.pdf_parser",
        "parser.metadata_extractor",
        "parser.normalizer",
        "brain.prompts",
        "brain.map_analyzer",
        "brain.reduce_synthesizer",
        "brain.intelligence_engine",
        "memory.schema",
        "memory.embedder",
        "memory.vector_store",
        "memory.portfolio_manager",
        "radar.email_formatter",
        "radar.whatsapp_notifier",
        "radar.alert_engine",
        "radar.orchestrator",
        "radar.scheduler",
        "radar.dashboard",
        "main"
    ]

    for mod in modules_to_test:
        try:
            importlib.import_module(mod)
            print(f"✅ Successfully imported {mod}")
        except Exception as e:
            print(f"❌ Failed to import {mod}: {type(e).__name__} - {e}")
            # print localized traceback
            traceback.print_exc(limit=1, file=sys.stdout)

    print("\n--- done ---")

if __name__ == "__main__":
    # Ensure local dir is in path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    test_imports()
