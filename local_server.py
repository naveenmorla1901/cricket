#!/usr/bin/env python3
"""
Simple HTTP server for local cricket stats development
Run this in your project directory to serve the website locally
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

PORT = 8000

class LocalHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow local file access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def log_message(self, format, *args):
        # Custom logging to show file requests
        if self.path.endswith('.json'):
            print(f"📊 Loading data file: {self.path}")
        elif self.path.endswith(('.html', '/')):
            print(f"🌐 Loading page: {self.path}")
        else:
            super().log_message(format, *args)

def main():
    # Check if we're in the right directory
    if not os.path.exists('index.html'):
        print("❌ Error: index.html not found!")
        print("💡 Please run this script from your cricket stats project directory")
        sys.exit(1)
    
    # Check for data directory
    if not os.path.exists('data'):
        print("⚠️  Warning: 'data' directory not found!")
        print("💡 Create a 'data' directory and add your JSON files there")
        os.makedirs('data', exist_ok=True)
    
    # List available data files
    data_files = list(Path('data').glob('*.json'))
    print(f"\n📊 Cricket Stats Local Server")
    print(f"{'='*40}")
    print(f"🌐 Server URL: http://localhost:{PORT}")
    print(f"📁 Data files found: {len(data_files)}")
    
    if data_files:
        for file in sorted(data_files):
            print(f"   - {file.name}")
    else:
        print("   ⚠️  No JSON data files found in data/ directory")
        print("   💡 Run your Python extractor script first:")
        print("   💡 python cricket_stats_extractor.py 2025 data")
    
    print(f"\n🚀 Starting server...")
    print(f"🌐 Open http://localhost:{PORT} in your browser")
    print(f"⏹️  Press Ctrl+C to stop the server")
    
    try:
        with socketserver.TCPServer(("", PORT), LocalHTTPRequestHandler) as httpd:
            # Try to open browser automatically
            try:
                webbrowser.open(f'http://localhost:{PORT}')
            except:
                pass
            
            print(f"✅ Server started successfully on port {PORT}")
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Server stopped by user")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use!")
            print(f"💡 Try a different port: python local_server.py 8001")
        else:
            print(f"❌ Server error: {e}")

if __name__ == "__main__":
    # Allow custom port as argument
    if len(sys.argv) > 1:
        try:
            PORT = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid port number")
            sys.exit(1)
    
    main()