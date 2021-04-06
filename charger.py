#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging
import random
from datetime import datetime, timedelta
from enum import Enum


class ChargerState(Enum):
    IDLE, PLUGGED_BEFORE_CHARGE, CHARGING, STOPPED_AFTER_CHARGING, \
        UNPLUGGED_CAR = range(5)


# minutes for duration of states
STATE_TIMES = [
    180,  # IDLE
    3,    # PLUGGED_BEFORE_CHARGE
    160,  # CHARGING
    10,   # STOPPED_AFTER_CHARGING
    3,    # UNPLUGGED_CAR
]


class Charger:
    # constant settings
    _CAR_MAX_POWER = 22  # kW
    _DEV_MAX_I = 32  # A

    # config settings
    # a positive session start describes the minute when above sequence starts
    # a negative session start gives the random factor to apply for charge timing
    _session_start = 0

    # internal data
    state = ChargerState.IDLE
    last_start = None
    next_state_change = None
    req_max_i = None
    e_total = 0       # kWh, total energy
    e_session = 0     # kWh, session energy
    charger_current = 0  # like cur_i
    cur_power = 0     # W, current charging power
    cur_i = None      # A, current charging current
    cur_u = None      # V, current phase voltage
    nr_phases = 3     # current number of used phases

    _last_update = None

    def __init__(self, session_start, phases=3):
        # init vars
        self._session_start = session_start
        self.state = ChargerState.IDLE
        self.nr_phases = phases
        self.cur_i = [0, 0, 0]
        self.cur_u = [230, 230, 230]
        self.e_total = random.random() * 5000   # 2.500 kWh average start
        self.next_state_change = self._get_next_statechange()
        self._last_update = datetime.now()

    def handle_get_data(self, url_path):
        attr_list = [(attr, getattr(self, attr)) for attr in dir(self)
                     if not attr.startswith('_') and not callable(getattr(Charger, attr))]
        attr_strings = [str(item) for item in attr_list]
        return "\n".join(attr_strings) + "\n", "text/plain"

    def handle_post_data(self, url_path, post_data):
        logging.warning("unhandled POST request: %s", url_path)
        return "", "text/plain"

    def _get_next_statechange(self):
        timefactor = STATE_TIMES[self.state.value]
        if self._session_start >= 0:
            # deterministic state change timing
            time_minutes = timefactor * 60 / sum(STATE_TIMES)
            if self.state != ChargerState.IDLE:
                next_start = datetime.now() + timedelta(minutes=time_minutes)
            else:
                # idle state always starts at defined minute
                last_hour = datetime.now().replace(microsecond=0, second=0, minute=0)
                next_start = last_hour + timedelta(hours=1) + timedelta(minutes=self._session_start)
        else:
            # random period
            # take session_start parameter as the weight
            mu = timefactor * -self._session_start
            # variance is 1/3
            time_minutes = random.gauss(mu, mu/3)
            # apply lower limit
            time_minutes = max(time_minutes, 1)
            next_start = datetime.now() + timedelta(minutes=time_minutes)

        return next_start

    def update_state(self):
        if datetime.now() > self.next_state_change:
            # state transition
            if self.state != ChargerState.UNPLUGGED_CAR:
                self.state = ChargerState(self.state.value + 1)
            else:
                self.state = ChargerState.IDLE
                self.last_start = datetime.now()
            self.next_state_change = self._get_next_statechange()

        # derive charging currents, power, energy
        sec_since_last_update = (datetime.now() - self._last_update).total_seconds()
        self.charger_current = self._get_charger_current()
        for phase in range(3):
            self.cur_u[phase] = int(random.gauss(230, 3))
            self.cur_i[phase] = random.gauss(self.charger_current, 0.05) \
                if self.charger_current and phase < self.nr_phases else 0
        self.cur_power = sum([self.cur_i[ph] * self.cur_u[ph] for ph in range(3)])
        energy = self.cur_power * sec_since_last_update / 3600000
        self.e_session += energy
        self.e_total += energy

        if self.state.value >= ChargerState.UNPLUGGED_CAR.value:
            self.e_session = 0

        # set last update timestamp
        self._last_update = datetime.now()

    def _get_charger_current(self):
        if self.state != ChargerState.CHARGING:
            return 0
        currents = [self._DEV_MAX_I, self._CAR_MAX_POWER, self.req_max_i]
        return min(x for x in currents if x is not None)

    def is_charging(self):
        return self.state == ChargerState.CHARGING and self.req_max_i != 0
