#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging
from datetime import datetime


class Charger:
    # constant settings
    _CHARGING_START = 2   # minutes
    _CHARGING_STOP = 15   # minutes
    _CHARGING_CABLE_CAR_OFF = 20  # minutes
    _CHARGING_ALL_OFF = 25  # minutes

    _CAR_MAX_POWER = 22  # kW
    _DEV_MAX_I = 32  # kW

    # config settings
    _session_start = 0

    # internal data
    req_max_i = None
    e_total = 0       # total energy
    e_session = 0     # session energy
    charger_current = 0  # like cur_i
    cur_power = 0     # current charging power
    cur_i = None      # current charging current
    cur_u = None      # current phase voltage
    nr_phases = 3    # current number of used phases

    _last_update = None

    def __init__(self, session_start, phases=3):
        # init vars
        self._session_start = session_start
        self.nr_phases = phases
        self.cur_i = [0, 0, 0]
        self.cur_u = [230, 230, 230]

    def handle_get_data(self):
        attr_list = [(attr, getattr(self, attr)) for attr in dir(self)
                     if not attr.startswith('_') and not callable(getattr(Charger, attr))]
        attr_strings = [str(item) for item in attr_list]
        return "\n".join(attr_strings) + "\n"

    def update_state(self):
        if not self._last_update:
            self._last_update = datetime.now()

        sec_since_last_update = (datetime.now() - self._last_update).total_seconds()
        self.charger_current = self._get_charger_current()
        for phase in range(3):
            self.cur_i[phase] = self.charger_current if phase < self.nr_phases else 0
        self.cur_power = sum([self.cur_i[ph] * self.cur_u[ph] for ph in range(3)])
        energy = self.cur_power * sec_since_last_update / 3600000
        self.e_session += energy
        self.e_total += energy

    def _get_charger_current(self):
        minute_in_session = datetime.now().minute - self._session_start
        if not self._CHARGING_START <= minute_in_session < self._CHARGING_STOP:
            return 0

        currents = [self._DEV_MAX_I, self._CAR_MAX_POWER, self.req_max_i]
        return min(x for x in currents if x is not None)

    def _simulate_charging(self, target_power):
        # charging
        self.cur_power = target_power
