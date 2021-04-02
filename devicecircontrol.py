#!/usr/bin/env python3
# Copyright (c) 2021 embyt GmbH. All rights reserved.
# Author: Roman Morawek <rmorawek@embyt.com>

import logging
from datetime import datetime
import xml.etree.ElementTree as ET

from charger import Charger

# Current values in A.
# Power values in W.
# Energy values in Wh

# Ladestrom auf 16A stellen
# Request to modify the plug current limit.
# POST / services/cpi/plugCurrent.xml
# <device >
#     <id > deviceName.plugName.socketName</id>
#     <current > int</current>
# </device >
# <id > deviceName.plugName.socketName</id> can be found in socketInfo.xml request

# Alternative:
# Request to modify the “limit current” during * ongoing * transactions.
# POST / services/cpi/reduceCurrent.xml
# <device >
#     <id > EVCommDevice</id>
#     <current > int</current>
# </device >
# <id > EVCommDevice</id> can be found in socketInfo.xml request


class DeviceCircontrol(Charger):
    def handle_get_data(self, url_path):
        # determine charging data
        minute_in_session = (datetime.now().minute - self._session_start) % 60
        state = 8  # todo
        data = {
            'requestDate': datetime.now().timestamp(),
            'beginDate': datetime.now().timestamp() - (minute_in_session - self._CHARGING_START) * 60
            if minute_in_session >= self._CHARGING_START else 0,
            'plugCurrent': self._DEV_MAX_I,
            'supportedCurrent': self._DEV_MAX_I,
            'chargeTime': (minute_in_session - self._CHARGING_START) * 60 if self.is_charging() else 0,
            'stopped': 1 if self._CHARGING_STOP <= minute_in_session < self._CHARGING_CABLE_CAR_OFF else 0,
            'activeEnergy': self.e_total,
            'partialActiveEnergy': self.e_session,
            'state': state,
            'chargingPhases': self.nr_phases,
            'currentL1': self.cur_i[0],
            'currentL2': self.cur_i[1],
            'currentL3': self.cur_i[2],
            'voltageL1': self.cur_u[0],
            'voltageL2': self.cur_u[1],
            'voltageL3': self.cur_u[2],
            'activePower': self.cur_power,
            'reduceCurrent': self.req_max_i,
            'limitCurrent': self.req_max_i,
        }

        if url_path == "/services/cpi/socketInfo.xml":
            return self._get_socket_info(data)
        if url_path == "/services/cpi/chargeInfo.xml":
            return self._get_charge_info(data)
        if url_path == "/services/cpi/chargeState.xml":
            return self._get_charge_state(data)

        return super().handle_get_data(url_path)

    def _get_socket_info(self, data):
        return """
          <socketsInfo>
            <socketInfo>
              <id>672C24E1-780D-457B-BDD1-C1D3BB5A7D2B.476A1CEA-951D-436A-A6CC-F71B94E48725.4A2963B9-2831-4656-A9E7-328BA8490F52</id>
              <name>EVSE.PLUG.SOCKET MODE 3</name>
              <number>1</number>
              <chargeMode>3</chargeMode>
              <connectorType>62196 TYPE 2</connectorType>
              <supportedCurrent>{supportedCurrent}</supportedCurrent>
              <EVCommDevice>PLUG - Mode 3</EVCommDevice>
              <plugCurrent>{plugCurrent}</plugCurrent>
              <hasCover>F</hasCover>
              <hasLock>T</hasLock>
              <hasSafeStorageLock>F</hasSafeStorageLock>
              <meter>PLUG - Meter</meter>
            </socketInfo>
          </socketsInfo>
        """.format(**data)

    def _get_charge_info(self, data):
        if self.is_charging():
            socket = """
                <socket >
                  <id > 4A2963B9-2831-4656-A9E7-328BA8490F52 < /id >
                  <name > SOCKET MODE 3 < /name >
                  <number > 1 < /number >
                  <state > {state} < /state >
                  <chargeId > 4A8EFBD2-8996-11EB-8996-11EBAEA263C0 < /chargeId >
                  <user > DAFC6C72 < /user >
                  <requestDate > {requestDate} < /requestDate >
                  <beginDate > {beginDate} < /beginDate >
                  <endDate > -1.000000 < /endDate >
                  <chargeTime > {chargeTime} < /chargeTime >
                  <stopped > {stopped} < /stopped >
                  <activeEnergy > {activeEnergy} < /activeEnergy >
                  <partialActiveEnergy > {partialActiveEnergy} < /partialActiveEnergy >
                </socket >
          """.format(**data)
        else:
            socket = ""

        return """
          <chargesInfo >
            <chargeInfo >
              <id > 672C24E1-780D-457B-BDD1-C1D3BB5A7D2B.476A1CEA-951D-436A-A6CC-F71B94E48725 < /id >
              <name > EVSE.PLUG < /name >
              <number > 1 < /number >
              <state > {state} < /state >
              <chargeId > 4A8EFBD2-8996-11EB-8996-11EBAEA263C0 < /chargeId >
              <user > DAFC6C72 < /user >
              <userType > RFID < /userType >
              <requestDate > {requestDate} < /requestDate >
              <beginDate > {beginDate} < /beginDate >
              <endDate > -1.000000 < /endDate >
              <chargeTime > {chargeTime} < /chargeTime >
              <stopped > {stopped} < /stopped >
              <stoppedByError > F < /stoppedByError >
              <activeEnergy > {activeEnergy} < /activeEnergy >
              <partialActiveEnergy > {partialActiveEnergy} < /partialActiveEnergy >
              {socket}
            </chargeInfo >
          </chargesInfo >
        """.format(socket=socket, **data)

    def _get_charge_state(self, data):
        if self.is_charging():
            socket = """
              <socket >
                <id > 4A2963B9-2831-4656-A9E7-328BA8490F52 < /id >
                <name > SOCKET MODE 3 < /name >
                <number > 1 < /number >
                <reduceCurrent > {reduceCurrent} < /reduceCurrent >
                <chargingPhases > {chargingPhases} < /chargingPhases >
                <state > {state} < /state >
                <chargeId > 4A8EFBD2-8996-11EB-8996-11EBAEA263C0 < /chargeId >
                <user > DAFC6C72 < /user >
                <chargeTime > {chargeTime} < /chargeTime >
                <activeEnergy > {activeEnergy} < /activeEnergy >
                <partialActiveEnergy > {partialActiveEnergy} < /partialActiveEnergy >
                <currentL1 > {currentL1} < /currentL1 >
                <currentL2 > {currentL2} < /currentL2 >
                <currentL3 > {currentL3} < /currentL3 >
                <currentIII > 0 < /currentIII >
                <voltageL1 > {voltageL1} < /voltageL1 >
                <voltageL2 > {voltageL2} < /voltageL2 >
                <voltageL3 > {voltageL3} < /voltageL3 >
                <voltageIII > 0 < /voltageIII >
                <activePower > {activePower} < /activePower >
                <limitCurrent > {limitCurrent} < /limitCurrent >
              </socket >
          """.format(**data)
        else:
            socket = ""

        return """
          <chargesState >
            <chargeState >
              <id > 672C24E1-780D-457B-BDD1-C1D3BB5A7D2B.476A1CEA-951D-436A-A6CC-F71B94E48725 < /id >
              <name > EVSE.PLUG < /name >
              <number > 1 < /number >
              <state > {state} < /state >
              <chargingPhases > {chargingPhases} < /chargingPhases >
              <chargeId > 4A8EFBD2-8996-11EB-8996-11EBAEA263C0 < /chargeId >
              <user > DAFC6C72 < /user >
              <chargeTime > {chargeTime} < /chargeTime >
              <reduceCurrent > {reduceCurrent} < /reduceCurrent >
              <activeEnergy > {activeEnergy} < /activeEnergy >
              <partialActiveEnergy > {partialActiveEnergy} < /partialActiveEnergy >
              <currentL1 > {currentL1} < /currentL1 >
              <currentL2 > {currentL2} < /currentL2 >
              <currentL3 > {currentL3} < /currentL3 >
              <currentIII > 0 < /currentIII >
              <voltageL1 > {voltageL1} < /voltageL1 >
              <voltageL2 > {voltageL2} < /voltageL2 >
              <voltageL3 > {voltageL3} < /voltageL3 >
              <voltageIII > 0 < /voltageIII >
              <activePower > {activePower} < /activePower >
              {socket}
            </chargeState >
          </chargesState >
        """.format(socket=socket, **data)

    def handle_post_data(self, url_path, post_data):
        if url_path == "/services/cpi/reduceCurrent.xml":
            xml = ET.fromstring(post_data)
            for tag in xml.findall('current'):
                self.req_max_i = int(tag.text)
                logging.info("new charger current: %s", self.req_max_i)
            return ""

        if url_path == "/services/cpi/plugCurrent.xml":
            # reduce current is only effective during charging
            if self.is_charging():
                xml = ET.fromstring(post_data)
                for tag in xml.findall('current'):
                    self.req_max_i = int(tag.text)
                    logging.info("new charger current: %s", self.req_max_i)
            return ""

        return super().handle_post_data(url_path, post_data)
