# frontend/markdown.py
"""
Markdown file caching and monitoring for HARVEST frontend.
"""
import os
import json
import logging
import threading
from dash import dcc

logger = logging.getLogger(__name__)


class MarkdownCache:
    """
    Thread-safe cache for markdown files with automatic reloading.
    Monitors the assets/ directory for .md file changes using watchdog.
    """
    def __init__(self, assets_dir, schema_json):
        self.assets_dir = assets_dir
        self.schema_json = schema_json
        self.cache = {}  # filename -> {'content': str, 'mtime': float, 'rendered': component}
        self.lock = threading.Lock()
        self.observer = None
        self._update_flag = threading.Event()
        
        # Initialize cache
        self._load_all_markdown_files()
        
        # Start watchdog observer
        self._start_watchdog()
    
    def _load_all_markdown_files(self):
        """Load all markdown files from assets directory"""
        md_files = ['annotator_guide.md', 'schema.md', 'admin_guide.md', 'db_model.md', 'participate.md', 'text2kg_pipeline.md']
        for filename in md_files:
            filepath = os.path.join(self.assets_dir, filename)
            if os.path.exists(filepath):
                self._load_file(filename, filepath)
    
    def _load_file(self, filename, filepath):
        """Load a single markdown file into cache"""
        try:
            mtime = os.path.getmtime(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Special handling for schema.md with JSON placeholder
            if filename == 'schema.md':
                schema_json_str = json.dumps(self.schema_json, indent=2)
                schema_json_block = f"```json\n{schema_json_str}\n```\n\n"
                content = content.replace("{SCHEMA_JSON}", schema_json_block)
            
            # Special handling for participate.md to allow HTML/iframe rendering
            if filename == 'participate.md':
                rendered = dcc.Markdown(content, dangerously_allow_html=True)
            else:
                rendered = dcc.Markdown(content)
            
            with self.lock:
                self.cache[filename] = {
                    'content': content,
                    'mtime': mtime,
                    'rendered': rendered
                }
            
            logger.info(f"Loaded markdown file: {filename}")
        except Exception as e:
            logger.error(f"Failed to load markdown file {filename}: {e}", exc_info=True)
            with self.lock:
                self.cache[filename] = {
                    'content': f"{filename} not found.",
                    'mtime': 0,
                    'rendered': dcc.Markdown(f"{filename} not found.")
                }
    
    def _start_watchdog(self):
        """Start watchdog observer for monitoring file changes"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class MarkdownEventHandler(FileSystemEventHandler):
                def __init__(self, cache):
                    self.cache = cache
                
                def on_modified(self, event):
                    if not event.is_directory and event.src_path.endswith('.md'):
                        filename = os.path.basename(event.src_path)
                        if filename in ['annotator_guide.md', 'schema.md', 'admin_guide.md', 'db_model.md', 'participate.md', 'text2kg_pipeline.md']:
                            logger.info(f"Detected change in {filename}, reloading...")
                            self.cache._load_file(filename, event.src_path)
                            self.cache._update_flag.set()
                
                def on_created(self, event):
                    if not event.is_directory and event.src_path.endswith('.md'):
                        filename = os.path.basename(event.src_path)
                        if filename in ['annotator_guide.md', 'schema.md', 'admin_guide.md', 'db_model.md', 'participate.md', 'text2kg_pipeline.md']:
                            logger.info(f"Detected new file {filename}, loading...")
                            self.cache._load_file(filename, event.src_path)
                            self.cache._update_flag.set()
            
            event_handler = MarkdownEventHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, self.assets_dir, recursive=False)
            self.observer.daemon = True  # Make it a daemon thread
            self.observer.start()
            logger.info(f"Started watchdog observer for markdown files in {self.assets_dir}")
        except ImportError:
            logger.warning("watchdog package not installed. Markdown auto-reload disabled.")
            logger.warning("Install with: pip install watchdog")
        except Exception as e:
            logger.error(f"Failed to start watchdog observer: {e}", exc_info=True)
    
    def get(self, filename, default_content="Content not found."):
        """Get rendered markdown component for a file"""
        with self.lock:
            if filename in self.cache:
                return self.cache[filename]['rendered']
            else:
                return dcc.Markdown(default_content)
    
    def has_updates(self):
        """Check if there are pending updates"""
        return self._update_flag.is_set()
    
    def clear_update_flag(self):
        """Clear the update flag"""
        self._update_flag.clear()
    
    def stop(self):
        """Stop the watchdog observer"""
        if self.observer:
            self.observer.stop()
            self.observer.join()


# Initialize markdown cache
# Will be created when module is imported, using SCHEMA_JSON passed from __init__
def create_markdown_cache(schema_json):
    """Create and return a MarkdownCache instance with the given schema."""
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    return MarkdownCache(assets_dir, schema_json)
