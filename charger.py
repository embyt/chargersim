#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging
from datetime import datetime


class Charger:
    # constant settings
    _CHARGING_START = 5   # minutes
    _CHARGING_STOP = 20  # minutes

    _CAR_MAX_POWER = 22  # kW

    # config settings
    _session_start = 0

    # internal data
    e_total = 0       # total energy
    e_session = 0     # session energy
    cur_power = 0     # current charging power
    cur_i = [0, 0, 0]  # current charging current
    cur_u = [230, 230, 230]  # current phase voltage
    nr_phases = 3    # current number of used phases

    _last_update = None

    def __init__(self, session_start):
        # init vars
        self._session_start = session_start
        self.cur_power = self._get_power()

    def handle_get_data(self):
        attr_list = [(attr, getattr(self, attr)) for attr in dir(self)
                     if not attr.startswith('_') and not callable(getattr(Charger, attr))]
        return str(attr_list)

    def update_state(self):
        if not self._last_update:
            self._last_update = datetime.now()

        sec_since_last_update = (datetime.now() - self._last_update).total_seconds()
        self.cur_power = self._get_power()
        energy = self.cur_power * sec_since_last_update / 3600000
        self.e_session += energy
        self.e_total += energy

        for phase in range(3):
            self.cur_i[phase] = self.cur_power * 1000 / (self.nr_phases * self.cur_u[phase]) \
                if phase < self.nr_phases else 0

    def _get_power(self):
        minute_in_session = datetime.now().minute - self._session_start
        if not self._CHARGING_START <= minute_in_session < self._CHARGING_STOP:
            return 0

        return self._CAR_MAX_POWER

    def _simulate_charging(self, target_power):
        # charging
        self.cur_power = target_power
