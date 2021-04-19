#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging
import random
import json
import os.path
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
    _DEV_MAX_I = 32  # A

    # config settings
    # a positive session start describes the minute when above sequence starts
    # a negative session start gives the random factor to apply for charge timing
    _session_start = 0
    _config_file_path = None

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
    auth_user = 0x4711171176abcdef

    _last_update = None

    def __init__(self, session_start, phases=3, id=None):
        # init vars
        self._session_start = session_start
        if id is not None:
            self._config_file_path = ".chargersim_cfg_" + str(id)

        if self._config_file_path is not None and os.path.isfile(self._config_file_path):
            # load data from dump file
            with open(self._config_file_path, 'r') as dumpfile:
                datadump = json.load(dumpfile)
                # restore state, timing, and energy meter
                self.state = ChargerState(datadump['state'])
                self.next_state_change = datetime.strptime(
                    datadump['next_state_change'], "%Y-%m-%dT%H:%M:%S")
                self._last_update = datetime.strptime(
                    datadump['_last_update'], "%Y-%m-%dT%H:%M:%S")
                self.cur_i = datadump['cur_i']
                self.e_total = datadump['e_total']
                self.req_max_i = datadump['req_max_i'] if 'req_max_i' in datadump else None
        else:
            # do a fresh initialization of data
            self.state = ChargerState.IDLE
            self.e_total = random.random() * 5000   # 2.500 kWh average start
            self.cur_i = [0, 0, 0]
            self.next_state_change = self._get_next_statechange()
            self._last_update = datetime.now()

        # this is always newly initialized
        self.nr_phases = phases
        self.cur_u = [230, 230, 230]

    @staticmethod
    def _serialize(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime):
            serial = obj.isoformat(timespec='seconds')
            return serial
        if isinstance(obj, ChargerState):
            serial = obj.value
            return serial
        return obj.__dict__

    def _create_dump_file(self):
        # save current data
        if self._config_file_path is not None:
            with open(self._config_file_path, 'w') as dumpfile:
                json.dump(self.__dict__, dumpfile, default=self._serialize)

    def handle_get_data(self, url_path):
        return json.dumps(self.__dict__, default=self._serialize), "application/json"

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
            # also set last update here to avoid long energy integration from other states
            # this is i.e. important if we just restored a data dump and have a long period in between
            self._last_update = datetime.now()
            # this is a good timing to backup config data
            self._create_dump_file()

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
        currents = [self._DEV_MAX_I, self.req_max_i]
        return min(x for x in currents if x is not None)

    def is_charging(self):
        return self.state == ChargerState.CHARGING and self.req_max_i != 0
