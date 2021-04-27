# PSL controller
# This file is part of project PslWake https://github.com/wackyfrog/psl-wake-py
# (C) 2021 Oleksandr Degtiar <adegtiar@gmail.com>

import glob
import sys
import time
import struct
from pprint import pprint
from .wake import Wake


class Control:
    is_on: bool
    is_cv: bool
    is_cc: bool
    is_ovp: bool
    is_ocp: bool
    is_opp: bool
    is_otp: bool
    info: str
    voltage: int  # mV
    current: int  # mA
    version: str
    BAUDRATE = 19200

    CMD_ECHO = 2
    CMD_INFO = 3
    CMD_GET_VI = 7
    CMD_STAT = 8
    CMD_GET_PARAM = 16

    PAR_INF = 20

    def __init__(self, port):
        self.wake = Wake()
        self.port = port
        self.voltage = 0
        self.current = 0
        self.is_on = False
        self.is_cv = False
        self.is_cc = False
        self.is_ovp = False
        self.is_ocp = False
        self.is_opp = False
        self.is_otp = False
        self.info = ""
        self.version = ""
        self.address = 0

    def open(self):
        if not self.wake.is_opened():
            self.wake.open(self.port, self.BAUDRATE)
            time.sleep(.1)

    def close(self):
        if self.wake.is_opened():
            self.wake.close()

    def command(self, command: int, data=[]):
        self.open()
        response = self.wake.command(command, self.address, data)
        if command == Control.CMD_INFO or command == Control.CMD_ECHO:
            return response
        else:
            assert response[0] == Wake.ERR_NO
            return response[1:]

    def update_info(self):
        response = self.command(Control.CMD_INFO)
        self.info = ''.join(map(chr, response))

    def echo(self, data):
        response = self.command(Control.CMD_ECHO, data.encode())
        return ''.join(map(chr, response))

    def get_param(self, param: int):
        response = self.command(Control.CMD_GET_PARAM, [param])
        return struct.unpack("<H", bytes(response))[0]

    def upvate_version(self):
        ver = str(self.get_param(21))
        self.version = ver[0] + '.' + ver[1:]

    def update_voltage_current(self):
        response = self.command(Control.CMD_GET_VI)
        voltage, current = struct.unpack("<HH", bytes(response))
        self.voltage = voltage
        self.current = current

    def update_state(self):
        response = self.command(Control.CMD_STAT)
        state, = struct.unpack("<B", bytes(response))
        self.is_on = bool(state & (1 << 0))
        self.is_cv = bool(state & (1 << 1))
        self.is_cc = bool(state & (1 << 2))
        self.is_ovp = bool(state & (1 << 3))
        self.is_ocp = bool(state & (1 << 4))
        self.is_opp = bool(state & (1 << 5))
        self.is_otp = bool(state & (1 << 6))

    def update(self):
        self.update_info()
        self.upvate_version()
        self.update_state()
        self.update_voltage_current()
        # self.get_param(17)
        pass
