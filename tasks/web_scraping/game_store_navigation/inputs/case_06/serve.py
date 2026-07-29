#!/usr/bin/env python3
"""Serve this directory over plain HTTP so the site's fetch()-based pages
(bundle tiers, catalog) work correctly -- file:// URLs hit CORS restrictions
on fetch() in most browsers, http:// does not.

Usage: python3 serve.py [port]   (default port 8000)
Then open http://localhost:<port>/index.html
"""
import http.server
import os
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
os.chdir(os.path.dirname(os.path.abspath(__file__)))

with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    print(f"Serving NebulaKey Store at http://localhost:{PORT}/index.html")
    httpd.serve_forever()
