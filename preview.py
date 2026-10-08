"""Launch the included offline practice website without a deployment account."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from pathlib import Path
import webbrowser

if __name__ == '__main__':
    site=Path(__file__).resolve().parents[1]/'site'
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(site)))
    url=f'http://127.0.0.1:{server.server_port}/'
    print('AI Daily Intelligence — local preview')
    print('Open:',url)
    print('This is the fictional sample, NOT live news. Press Ctrl+C to stop.')
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
