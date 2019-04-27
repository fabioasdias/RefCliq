#!/usr/bin/env python
# encoding: utf-8

import cherrypy
import sys
import json
import os
import webbrowser

def cors():
    if cherrypy.request.method == 'OPTIONS':
        # preflign request
        # see http://www.w3.org/TR/cors/#cross-origin-request-with-preflight-0
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'POST'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'content-type'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        # tell CherryPy no avoid normal handler
        return True
    else:
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'


cherrypy.tools.cors = cherrypy._cptools.HandlerTool(cors)


@cherrypy.expose
class server(object):
    @cherrypy.expose
    @cherrypy.config(**{'tools.cors.on': True})
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    @cherrypy.tools.gzip()
    def getAspects(self):
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        input_json = cherrypy.request.json
        print(input_json)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def availableCountries(self):
        pass

    @cherrypy.expose
    def index(self):
        return("It works!")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print('\nUsage:\n {0} result.json\n Where "result.json" is the result to be visualized.'.format(
            sys.argv[0]))
        exit(-1)

    with open(sys.argv[1]) as fin:
        data = json.load(fin)

    webapp = server()
    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd()),
            'tools.gzip.on': True,
            'tools.gzip.mime_types': ['text/*', 'application/*']
        },
        '/public': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './public'
        }
    }
    cherrypy.server.max_request_body_size = 0  # for upload
    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.server.socket_port = 8080
    webbrowser.open_new_tab("http://localhost:8080/")
    cherrypy.quickstart(webapp, '/', conf)
