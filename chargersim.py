#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import time
import logging
import traceback
import http.server
import socketserver
import select

from charger import Charger


START_PORT = 8000
CHARGER_AREA = 10  # number of ports between chargers
NR_CHARGERS = 10  # number of instantiated chargers, must be less than CHARGER_AREA


class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    chargers = None  # handle to the correspondig chargers

    def do_GET(self):
        # determine targetted charger
        port = self.request.getsockname()[1]
        charger_type = port % START_PORT // CHARGER_AREA
        charger_index = port % START_PORT % CHARGER_AREA
        logging.info("GET for charger %s index %s", charger_type, charger_index)
        charger = self.chargers[charger_type][charger_index]

        # Sending an '200 OK' response
        self.send_response(200)
        # Setting the header
        self.send_header("Content-type", "application/json")
        # Whenever using 'send_header', you also have to call 'end_headers'
        self.end_headers()

        # derive answer
        json = charger.handle_get_data()

        # Writing the HTML contents with UTF-8
        self.wfile.write(bytes(json, "utf8"))


class ChargerSim:
    MAIN_RECURRENCE = 1    # second

    chargers = []  # array of type, index
    servers = []

    def __init__(self):
        # disable logging of urllib and requests
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        # setup chargers and http sockets
        for charger_type in range(2):
            chargers = []
            for charger_index in range(5):
                port = START_PORT + charger_type * CHARGER_AREA + charger_index
                chargers.append(Charger())
                self.servers.append(socketserver.TCPServer(
                    ("", port),
                    HttpRequestHandler
                ))
            self.chargers.append(chargers)

        HttpRequestHandler.chargers = self.chargers

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
            for charger_type in self.chargers:
                for cur_charger in charger_type:
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
