# WAKE protocol implementation
# This file is part of project PslWake https://github.com/wackyfrog/psl-wake-py
# (C) 2021 Oleksandr Degtiar <adegtiar@gmail.com>

import serial
import glob
import sys
import time
import struct
from pprint import pprint
import logging

logging.basicConfig(format='%(asctime)s [%(levelname)s]\t%(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)


class Wake:
    serial: serial.Serial

    DEBUG_RESPONSE = True

    ERR_NO = 0x00  # OK
    ERR_TX = 0x01  # Device transmit error
    ERR_BUSY = 0x02  # Device is busy
    ERR_RE = 0x03  # Device is not ready
    ERR_PA = 0x04  # Error in parameters
    ERR_NR = 0x05  # No response

    FEND = 0xC0  # Frame End
    FESC = 0xDB  # Frame Escape
    TFEND = 0xDC  # Transposed Frame End
    TFESC = 0xDD  # Transposed Frame Escape

    STATE_FEND = 'FEND'
    STATE_CMD = 'CMD'
    STATE_LEN = 'DATA_LEN'
    STATE_DATA = 'DATA'
    STATE_CRC = 'CRC'

    _crc8_table = [0, 94, 188, 226, 97, 63, 221, 131, 194, 156, 126, 32, 163, 253, 31, 65,
                   157, 195, 33, 127, 252, 162, 64, 30, 95, 1, 227, 189, 62, 96, 130, 220,
                   35, 125, 159, 193, 66, 28, 254, 160, 225, 191, 93, 3, 128, 222, 60, 98,
                   190, 224, 2, 92, 223, 129, 99, 61, 124, 34, 192, 158, 29, 67, 161, 255,
                   70, 24, 250, 164, 39, 121, 155, 197, 132, 218, 56, 102, 229, 187, 89, 7,
                   219, 133, 103, 57, 186, 228, 6, 88, 25, 71, 165, 251, 120, 38, 196, 154,
                   101, 59, 217, 135, 4, 90, 184, 230, 167, 249, 27, 69, 198, 152, 122, 36,
                   248, 166, 68, 26, 153, 199, 37, 123, 58, 100, 134, 216, 91, 5, 231, 185,
                   140, 210, 48, 110, 237, 179, 81, 15, 78, 16, 242, 172, 47, 113, 147, 205,
                   17, 79, 173, 243, 112, 46, 204, 146, 211, 141, 111, 49, 178, 236, 14, 80,
                   175, 241, 19, 77, 206, 144, 114, 44, 109, 51, 209, 143, 12, 82, 176, 238,
                   50, 108, 142, 208, 83, 13, 239, 177, 240, 174, 76, 18, 145, 207, 45, 115,
                   202, 148, 118, 40, 171, 245, 23, 73, 8, 86, 180, 234, 105, 55, 213, 139,
                   87, 9, 235, 181, 54, 104, 138, 212, 149, 203, 41, 119, 244, 170, 72, 22,
                   233, 183, 85, 11, 136, 214, 52, 106, 43, 117, 151, 201, 74, 20, 246, 168,
                   116, 42, 200, 150, 21, 75, 169, 247, 182, 232, 10, 84, 215, 137, 107, 53]

    def __init__(self):
        self.serial = serial.Serial()

    def open(self, port, baudrate, timeout=5):
        logging.debug(f"Initializing serial port '{port}'")
        try:
            s = self.serial
            s.port = port
            s.baudrate = baudrate
            s.bytesize = serial.EIGHTBITS
            s.parity = serial.PARITY_NONE
            s.stopbits = serial.STOPBITS_ONE
            s.xonxoff = False
            s.rtscts = False
            s.dsrdtr = False
            s.timeout = timeout
            s.write_timeout = timeout
            s.open()
            s.reset_input_buffer()
            s.reset_output_buffer()
            time.sleep(0.1)
            logging.debug(f"Serial port '{port}' is ready.")
        except serial.SerialException as e:
            sys.stderr.write('Could not open serial port {}: {}\n'.format(self.serial.name, e))
            sys.exit(1)

    def is_opened(self):
        return self.serial.isOpen()

    @staticmethod
    def list_ports(name="", try_open=False):
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/cu.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                if name not in port:
                    continue

                if try_open:
                    s = serial.Serial(port)
                    s.close()

                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    @staticmethod
    def get_port(name=""):
        ports = Wake.list_ports(name)
        return ports[0] if ports else None

    def close(self):
        time.sleep(0.1)
        self.serial.close()
        pass

    def calc_crc(self, packet):
        crc = 0xDE
        for byte in packet:
            byte &= 0xFF
            crc = self._crc8_table[crc ^ byte]
        return crc

    def encode_packet(self, packet):
        encoded_packet = []
        for index, byte in enumerate(packet):
            if index == 0:
                encoded_packet.append(byte)

            else:
                if byte == self.FEND:
                    encoded_packet.append(self.FESC)
                    encoded_packet.append(self.TFEND)
                elif byte == self.FESC:
                    encoded_packet.append(self.FESC)
                    encoded_packet.append(self.TFESC)
                else:
                    encoded_packet.append(byte)

        return encoded_packet

    def command(self, command: int, address: int = 0, data=[]) -> list:
        """
        Send command
        :param command:
        :param address:
        :param data:
        :return:
        """
        command &= 0x7F
        address &= 0x7F
        packet = [self.FEND]
        if address != 0:
            packet.append(address | 0x80)

        packet.append(command)
        packet.append(len(data) & 0xFF)
        packet += data
        packet.append(self.calc_crc(packet))

        packet = self.encode_packet(packet)
        logging.debug("Sending packet: {}".format(self.dump(packet)))
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        self.serial.write(packet)
        # time.sleep(.1)

        response = self.read_response()
        # pprint(response)
        assert response, f"Invalid response to command 0x{command:x}"
        return response

    def decode_packet(self, raw_packet) -> list:
        packet = []
        if self.calc_crc(raw_packet[:-1]) == raw_packet[-1]:
            body = ''.join(map(chr, raw_packet[1:-1]))
            packet = list(body)
            self.dump("Decoded packet:\t", packet)

        return packet

    def read_response(self, timeout=5):
        def next_byte(stream: list):
            """
            Decode next byte(s) (from the begining of buffer)
            :param stream:
            :return:
            """
            byte = ""

            if stream[0] == self.FESC:
                if len(stream) > 1:
                    byte = stream.pop(0)
                    if stream[0] == self.TFEND:
                        stream.pop(0)
                        byte = self.FEND

                    elif stream[0] == self.TFESC:
                        stream.pop(0)
                        byte = self.FESC
            else:
                byte = stream.pop(0)

            return byte

        ts = time.time()
        response = []
        response_raw = []
        state = self.STATE_FEND
        data_len = 0
        data = []
        cmd = 0x00
        logging.debug(f"Reading response ...")

        while True:
            response_raw += self.serial.read_all()

            if state == self.STATE_FEND:
                if response_raw:
                    try:
                        response_raw = response_raw[response_raw.index(self.FEND) + 1:]
                        state = self.STATE_CMD
                        logging.debug("... start signature found, decoding packet")
                    except ValueError:
                        response_raw = []
                        pass

            if state == self.STATE_CMD:
                if response_raw:
                    cmd = response_raw[0]
                    response_raw = response_raw[1:]
                    logging.debug(f"... command: 0x{cmd:x}")
                    state = self.STATE_LEN
                pass

            if state == self.STATE_LEN:
                if response_raw:
                    data_len = next_byte(response_raw)
                    logging.debug(f"... data length: {data_len}")
                    state = self.STATE_DATA
                pass

            if state == self.STATE_DATA:
                if len(data) == data_len:
                    logging.debug(f"... data received: " + self.dump(data))
                    state = self.STATE_CRC
                else:
                    data.append(next_byte(response_raw))
                pass

            if state == self.STATE_CRC:
                if response_raw:
                    logging.debug("Checking CRC")
                    if response_raw[0] == self.calc_crc([self.FEND, cmd, data_len] + data):
                        logging.debug("Packet decoded")
                        response = data
                        break
                    else:
                        logging.error("CRC mismatch. Resetting state.")
                        state = self.STATE_FEND
                        cmd = 0x00
                        data = []
                pass

            if time.time() - ts > timeout:
                logging.error("Read timeout")
                break

            time.sleep(0.01)
            pass
        return response

    @staticmethod
    def dump(data) -> str:
        return ''.join(map(lambda x: "{0:02X}({ch:s}) ".format(x, ch=chr(x)), data))
