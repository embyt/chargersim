#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging


class Charger:
    # config settings
    START_SOC = 0.5
    CAPACITY = 1    # battery capacity [kWh]

    # internal data
    soc = START_SOC  # current state of charge
    eTotal = 0      # total energy
    eSession = 0    # session energy

    def __init__(self):
        # init vars
        self.cur_power = 0

    def handle_get_data(self):
        return '{ got: "it" }'

    def update_state(self):
        #logging.info("upate state")
        pass

    def _simulate_charging(self, target_power):
        # charging
        self.cur_power = target_power
        # determine new SOC
        self.soc += abs(self.cur_power)*self.MAIN_RECURRENCE/(self.CAPACITY*3600000)

        # limit to valid range
        if self.soc > 1:
            self.soc = 1
