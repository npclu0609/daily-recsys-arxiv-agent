from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    print("Paper archive: http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), SimpleHTTPRequestHandler).serve_forever()
