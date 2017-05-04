# noinspection PyCompatibility
import http.server

# noinspection PyCompatibility
from socketserver import ThreadingMixIn

try:
    # noinspection PyCompatibility
    import urlparse
except ImportError:
    #py3
    # noinspection PyCompatibility
    import urllib.parse as urlparse
    
import logging
logger = logging.getLogger(__name__)

def register_endpoint(path):
    def _reg_ep(func):
        #_endpoints[path] = func
        func._expose_path = path
        return func

    return _reg_ep

class JSONAPIRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    logrequests = False

    def _process_request(self):
        import zlib
        up = urlparse.urlparse(self.path)

        kwargs = urlparse.parse_qs(up.query)

        kwargs = {k : v[0] for k, v in kwargs.items()}

        cl = int(self.headers.get('Content-Length', 0))
        if cl > 0:
            body = self.rfile.read(cl)
            if self.headers.get('Content-Encoding') == 'gzip':
                body = zlib.decompress(body)
            kwargs['body'] = body

        #logger.debug('Request path: ' + up.path)
        #logger.debug('Requests args: ' + repr(kwargs))

        handler = self.server._endpoints[up.path]
        resp = handler(**kwargs)

        self.send_response(200)
        self.send_header("Content-Type", 'application/json')
        if 'gzip' in self.headers.get('Accept-Encoding', ''):
            self.send_header('Content-Encoding', 'gzip')
            resp = zlib.compress(resp)
        self.send_header("Content-Length", "%d" % len(resp))
        self.end_headers()

        self.wfile.write(resp)
        return


    def do_GET(self):
        return self._process_request()

    def do_POST(self):
        return self._process_request()

    def log_request(self, code='-', size='-'):
        """Log an accepted request.

        This is called by send_response().

        """
        if self.logrequests:
            self.log_message('"%s" %s %s', self.requestline, str(code), str(size))


class APIHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    def __init__(self, server_address):
        http.server.HTTPServer.__init__(self, server_address, JSONAPIRequestHandler)

        #make a mapping of endpoints to functions
        self._endpoints = {}
        for a in dir(self):
            func = getattr(self, a)
            endpoint_path = getattr(func, '_expose_path', None)
            if not endpoint_path is None:
                self._endpoints[endpoint_path] = func