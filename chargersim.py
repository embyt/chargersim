#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging
import traceback
import http.server
import socketserver
import select

from charger import Charger
from devicegoe import DeviceGoe


START_PORT = 8000
CHARGER_AREA = 10  # number of ports between chargers
NR_CHARGERS = 10  # number of instantiated chargers, must be less than CHARGER_AREA


class HttpRequestHandler(http.server.BaseHTTPRequestHandler):
    chargers = None  # handle to the correspondig chargers

    def _get_charger(self):
        # determine targetted charger
        port = self.request.getsockname()[1]
        return self.chargers[port]

    def _set_response(self, content):
        # Sending an '200 OK' response
        self.send_response(200)
        # Setting the header
        self.send_header("Content-type", "application/json")
        # Whenever using 'send_header', you also have to call 'end_headers'
        self.end_headers()

        # Writing the HTML contents with UTF-8
        self.wfile.write(bytes(content, "utf8"))

    def do_GET(self):
        # derive answer
        charger = self._get_charger()
        response = charger.handle_get_data(self.path)
        self._set_response(response)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                     str(self.path), str(self.headers), post_data.decode('utf-8'))

        # derive answer
        charger = self._get_charger()
        response = charger.handle_post_data(self.path, post_data)
        self._set_response(response)


class ChargerSim:
    MAIN_RECURRENCE = 1    # second

    chargers = {}  # handle to the correspondig chargers
    servers = []

    def __init__(self):
        # disable logging of urllib and requests
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        # setup chargers and http sockets
        HttpRequestHandler.chargers = self.chargers
        port = START_PORT
        self.chargers[port] = DeviceGoe(0)
        self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
        port += 1
        self.chargers[port] = DeviceGoe(10, 1)
        self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
        port += 1
        self.chargers[port] = DeviceGoe(20)
        self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
        port += 1
        self.chargers[port] = DeviceGoe(30, 2)
        self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
        port += 1
        self.chargers[port] = DeviceGoe(40)
        self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))

    def run(self):
        # listen for server requests
        while True:
            # server http requests and timeout on charger updates
            # notice, that incoming http requests will influence the charger call repetition timing!
            # we accept this for now
            r, w, e = select.select(self.servers, [], [], self.MAIN_RECURRENCE)
            for cur_server in self.servers:
                if cur_server in r:
                    cur_server.handle_request()
            # update charger states
            for cur_charger in self.chargers.values():
                cur_charger.update_state()


def main():
    try:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

        # setup main class
        chargersim = ChargerSim()

        # run
        chargersim.run()
    except Exception as exc:
        logging.error("raised exception: {}".format(traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
