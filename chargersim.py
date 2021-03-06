#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging
import traceback
import http.server
import socketserver
import select

from devicegoe import DeviceGoe
from devicecircontrol import DeviceCircontrol


START_PORT = 8100
CHARGER_AREA = 10  # number of ports between chargers
NR_CHARGERS = 10  # number of instantiated chargers, must be less than CHARGER_AREA


class HttpRequestHandler(http.server.BaseHTTPRequestHandler):
    chargers = None  # handle to the correspondig chargers

    def _get_charger(self):
        # determine targetted charger
        port = self.request.getsockname()[1]
        return self.chargers[port]

    def _set_response(self, content, content_type):
        # Sending an '200 OK' response
        self.send_response(200)
        # Setting the header
        self.send_header("Content-type", content_type)
        # Whenever using 'send_header', you also have to call 'end_headers'
        self.end_headers()

        # Writing the HTML contents with UTF-8
        self.wfile.write(bytes(content, "utf8"))

    def do_GET(self):
        # derive answer
        charger = self._get_charger()
        response, content_type = charger.handle_get_data(self.path)
        self._set_response(response, content_type)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        # derive answer
        charger = self._get_charger()
        response, content_type = charger.handle_post_data(self.path, post_data)
        self._set_response(response, content_type)

    def do_PUT(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        # derive answer
        charger = self._get_charger()
        response, content_type = charger.handle_post_data(self.path, post_data)
        self._set_response(response, content_type)


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
        start_times = [0, 10, 20, 30, 40]
        nr_phases = [3, 1, 3, 2, 3]

        port = START_PORT
        # go-e chargers
        for i in range(5):
            self.chargers[port] = DeviceGoe(start_times[i], nr_phases[i], port)
            self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
            port += 1
        for i in range(5):
            self.chargers[port] = DeviceGoe(-0.3 * (i + 1), nr_phases[i], port)
            self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
            port += 1
        # Circontrol chargers
        for i in range(5):
            self.chargers[port] = DeviceCircontrol(start_times[i], nr_phases[i], port)
            self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
            port += 1
        for i in range(5):
            self.chargers[port] = DeviceCircontrol(-0.3 * (i + 1), nr_phases[i], port)
            self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
            port += 1
        # 100 more Circontrol chargers
        for i in range(100):
            self.chargers[port] = DeviceCircontrol(-1, nr_phases[i % len(nr_phases)], port)
            self.servers.append(socketserver.TCPServer(("", port), HttpRequestHandler))
            port += 1

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
