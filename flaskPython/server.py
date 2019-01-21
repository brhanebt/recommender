from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Hello, world!')

httpd = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
httpd.serve_forever()

# PORT=8018
# Handler=http.server.SimpleHTTPRequestHandler
# httpd=socketserver.TCPServer(("",PORT),Handler)
# print("Server at PORT ", PORT)
# httpd.serve_forever()