#!/usr/bin/env python
# encoding: utf-8

import http.server
import socketserver
import sys
import webbrowser
from tempfile import TemporaryDirectory
from shutil import copytree, copy
from os import chdir
from os.path import join
from imp import find_module


template = 'template'

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print('\nUsage:\n {0} result.json\n Where "result.json" is the result to be visualized.'.format(
            sys.argv[0]))
        exit(-1)

    with TemporaryDirectory() as basefolder:
        print(find_module('refcliq'))
        newRoot=join(basefolder,'refcliq')
        copytree(join(find_module('refcliq')[1], template), newRoot)
        copy(sys.argv[1], join(newRoot, 'data.json'))
        chdir(newRoot)

        PORT = 8080
        Handler = http.server.SimpleHTTPRequestHandler
        url = "http://localhost:{0}/".format(PORT)
        webbrowser.open_new_tab(url)
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print('Serving at {0}\n\nPress Ctrl+C (or Command+dot) to stop.\n\n')
            httpd.serve_forever()

        
