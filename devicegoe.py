#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging
import json

from charger import Charger


# see https://github.com/goecharger/go-eCharger-API-v1/blob/master/go-eCharger%20API%20v1%20DE.md
# amp uint8_t Ampere Wert für die PWM Signalisierung in ganzen Ampere von6-32A

# nrg[4]​: Ampere auf L1 in 0.1A ​(123 entspricht 12,3A)
# nrg[5]​: Ampere auf L2 in 0.1A
# nrg[6]​: Ampere auf L3 in 0.1A
# nrg[11]​: Leistung gesamt  in 0.01kW ​(360 entspricht 3,6kW)

# ama uint8_t Absolute max. Ampere: Maximalwert für Ampere Einstellung
# Beispiel: 20 (Einstellung auf mehr als 20A in der App nicht möglich)


class DeviceGoe(Charger):
    def handle_get_data(self, url_path):
        if url_path != "/status":
            return super().handle_get_data(url_path)

        # determine charging state
        minute_in_session = (datetime.now().minute - self._session_start) % 60
        car = 1  # default
        if self._CHARGING_START <= minute_in_session < self._CHARGING_STOP:
            car = 2
        elif self._CHARGING_STOP <= minute_in_session < self._CHARGING_CABLE_CAR_OFF:
            car = 4
        result = {
            "version": "B",
            "rbc": "251",
            "rbt": "2208867",
            "car": str(car),
            "amp": "10",
            "err": "0",
            "ast": "0",
            "alw": "1",
            "stp": "0",
            "cbl": "0",
            "pha": "8",
            "tmp": "30",
            "dws": str(self.e_session * 360000),
            "dwo": "0",
            "adi": "1",
            "uby": "0",
            "eto": str(self.e_total * 10),
            "wst": "3",
            "nrg": [
                self.cur_u[0], self.cur_u[1], self.cur_u[2], 0,
                self.cur_i[0] * 10, self.cur_i[1] * 10, self.cur_i[2] * 10,
                self.cur_u[0] * self.cur_i[0] / 100, self.cur_u[1] *
                self.cur_i[1] / 100, self.cur_u[2] * self.cur_i[2] / 100, 0,
                self.cur_power / 10,
                0, 0, 0, 0,
            ],
            "fwv": "020-rc1",
            "sse": "000000",
            "wss": "goe",
            "wke": "",
            "wen": "1",
            "tof": "101",
            "tds": "1",
            "lbr": "255",
            "aho": "2",
            "afi": "8",
            "ama": str(self._DEV_MAX_I),
            "amp": str(self.req_max_i),
            "al1": "11",
            "al2": "12",
            "al3": "15",
            "al4": "24",
            "al5": "31",
            "cid": "255",
            "cch": "65535",
            "cfi": "65280",
            "lse": "0",
            "ust": "0",
            "wak": "",
            "r1x": "2",
            "dto": "0",
            "nmo": "0",
            "eca": "0",
            "ecr": "0",
            "ecd": "0",
            "ec4": "0",
            "ec5": "0",
            "ec6": "0",
            "ec7": "0",
            "ec8": "0",
            "ec9": "0",
            "ec1": "0",
            "rca": "",
            "rcr": "",
            "rcd": "",
            "rc4": "",
            "rc5": "",
            "rc6": "",
            "rc7": "",
            "rc8": "",
            "rc9": "",
            "rc1": "",
            "rna": "",
            "rnm": "",
            "rne": "",
            "rn4": "",
            "rn5": "",
            "rn6": "",
            "rn7": "",
            "rn8": "",
            "rn9": "",
            "rn1": ""
        }
        return json.dumps(result)

    def handle_post_data(self, url_path, post_data):
        if not url_path.startswith("/mqtt?payload="):
            return super().handle_post_data(url_path, post_data)
        command = url_path[len("/mqtt?payload="):]
        if command.startswith("amp="):
            # set new charger current
            self.req_max_i = int(command[len("amp="):])
            logging.info("new charger current: %s", self.req_max_i)
        else:
            logging.warning("unhandled command: %s", command)
        return ""
