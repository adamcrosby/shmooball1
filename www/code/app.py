#!/usr/bin/python
from flup.server.fcgi import WSGIServer
from werkzeug.contrib.fixers import LighttpdCGIRootFix
from shmooball import app

OUR_APP_ROOT = ""

class LameRootFix(object):
    """ Quick hack to fix root path """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        environ['PATH_INFO'] = OUR_APP_ROOT + environ.get('PATH_INFO', '')
        environ['SCRIPT_NAME'] = ''
        return self.app(environ, start_response)

if __name__ == '__main__':
    app.secret_key = # This should error on launch, please fix and don't check in to git
#    WSGIServer(app).run()
#    WSGIServer(LighttpdCGIRootFix(app)).run()
    WSGIServer(LameRootFix(app)).run()
