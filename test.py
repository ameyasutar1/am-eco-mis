import time
import logging
import struct
import socket
import snap7
from snap7.util import get_bool

# ---------------- CONFIG ----------------

IP = "192.168.2.50"
READ_DB = 14
WRITE_DB = 5
RACK = 0
SLOT = 1
PORT = 102
CONNECT_TIMEOUT = 3.0

CYCLE_TIMEOUT = 300
POLL_DELAY = 0.5
PULSE_DELAY = 0.1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================================================
# PLC MAP
# =========================================================

class ReadBits:
    LOAD_DONE = 0.0
    UNLOAD_DONE = 0.1
    EMG_HEALTHY = 0.2
    MANUAL_MODE = 0.3
    AUTO_MODE = 0.4
    LOCATION_SET_COMPLETED = 0.5
    HEARTBEAT = 0.6
    LOAD_IN_PROGRESS = 0.7
    UNLOAD_IN_PROGRESS = 1.0


class WriteBits:
    LOAD_START = 0.0
    UNLOAD_START = 0.1
    SET_LOC_FOR_LOAD = 0.2
    SET_LOC_FOR_UNLOAD = 0.3
    HEARTBEAT = 0.4
    LOAD_RECORDED = 0.5
    UNLOAD_RECORDED = 0.6


class WriteDints:
    LOAD_PICKUP = 4.0
    LOAD_DROP = 8.0
    UNLOAD_PICKUP = 12.0
    UNLOAD_DROP = 16.0


# =========================================================
# PLC CONNECTION
# =========================================================

class PLCConnection:

    def __init__(self, ip, rack, slot, read_db, write_db, port=102):
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.read_db = read_db
        self.write_db = write_db
        self.port = port
        self.client = snap7.client.Client()

    @staticmethod
    def split_offset(offset):
        byte_str, bit_str = str(offset).split(".")
        return int(byte_str), int(bit_str)

    def connect(self):
        logging.info(f"Connecting to {self.ip}:{self.port}")
        self.client.connect(self.ip, self.rack, self.slot, self.port)
        if not self.client.get_connected():
            raise Exception("PLC connection failed")
        logging.info("PLC Connected")

    def disconnect(self):
        if self.client.get_connected():
            self.client.disconnect()
            logging.info("PLC Disconnected")

    def read_bool(self, offset):
        byte, bit = self.split_offset(offset)
        raw = self.client.db_read(self.read_db, byte, 1)
        return get_bool(raw, 0, bit)

    def write_bool(self, offset, value):
        byte, bit = self.split_offset(offset)
        current = bytearray(self.client.db_read(self.write_db, byte, 1))

        if value:
            current[0] |= (1 << bit)
        else:
            current[0] &= ~(1 << bit)

        self.client.db_write(self.write_db, byte, current)
        logging.info(f"WRITE BOOL @ {offset} = {value}")

    def write_dint(self, offset, value):
        byte, _ = self.split_offset(offset)
        buffer = struct.pack(">i", int(value))
        self.client.db_write(self.write_db, byte, buffer)
        logging.info(f"WRITE DINT @ {offset} = {value}")


# =========================================================
# HELPERS
# =========================================================

def connect_plc():
    # Fail fast if PLC TCP endpoint is not reachable.
    try:
        with socket.create_connection((IP, PORT), timeout=CONNECT_TIMEOUT):
            pass
    except OSError as e:
        raise ConnectionError(
            f"PLC {IP}:{PORT} unreachable (timeout {CONNECT_TIMEOUT}s): {e}"
        )

    plc = PLCConnection(IP, RACK, SLOT, READ_DB, WRITE_DB, PORT)
    plc.connect()
    return plc


def probe_plc_connection(timeout=1.5):
    try:
        with socket.create_connection((IP, PORT), timeout=timeout):
            pass
        return True, f"PLC reachable at {IP}:{PORT}"
    except OSError as e:
        return False, f"PLC unreachable at {IP}:{PORT}: {e}"


def pulse(plc, offset):
    plc.write_bool(offset, False)
    time.sleep(PULSE_DELAY)
    plc.write_bool(offset, True)
    time.sleep(PULSE_DELAY)
    plc.write_bool(offset, False)


def wait_for_bit(plc, offset, name, timeout=CYCLE_TIMEOUT):

    start = time.time()

    while True:

        value = plc.read_bool(offset)

        if value:
            print(f"✅ {name} = TRUE")
            return

        if time.time() - start > timeout:
            raise TimeoutError(f"Timeout waiting for {name}")

        print(f"⏳ Waiting for {name} ... {value}")
        time.sleep(POLL_DELAY)


def wait_until_free(plc):

    while True:

        load = plc.read_bool(ReadBits.LOAD_IN_PROGRESS)
        unload = plc.read_bool(ReadBits.UNLOAD_IN_PROGRESS)

        if not load and not unload:
            print("✅ Stacker free")
            return

        print("⚠ PLC Busy...")
        time.sleep(POLL_DELAY)


def check_stacker_health(plc):

    emg = plc.read_bool(ReadBits.EMG_HEALTHY)
    auto = plc.read_bool(ReadBits.AUTO_MODE)

    logging.info(f"EMG_HEALTHY={emg}")
    logging.info(f"AUTO_MODE={auto}")


# =========================================================
# INWARD CYCLE
# =========================================================

def inward_cycle(station_id, bin_id):

    print("\n🚀 INWARD CYCLE")

    plc = connect_plc()

    try:

        check_stacker_health(plc)

        # handshake start
        plc.write_bool(WriteBits.LOAD_RECORDED, True)
        plc.write_bool(WriteBits.UNLOAD_RECORDED, True)

        wait_until_free(plc)

        plc.write_dint(WriteDints.LOAD_PICKUP, station_id)
        plc.write_dint(WriteDints.LOAD_DROP, bin_id)

        plc.write_bool(WriteBits.SET_LOC_FOR_LOAD, True)

        wait_for_bit(plc, ReadBits.LOCATION_SET_COMPLETED, "LOCATION_SET_COMPLETED")
        plc.write_bool(WriteBits.SET_LOC_FOR_LOAD, False)
        plc.write_bool(WriteBits.LOAD_RECORDED, False)
        plc.write_bool(WriteBits.UNLOAD_RECORDED, False)

        pulse(plc, WriteBits.LOAD_START)

        wait_for_bit(plc, ReadBits.LOAD_IN_PROGRESS, "LOAD_IN_PROGRESS")

        wait_for_bit(plc, ReadBits.LOAD_DONE, "LOAD_DONE")

        plc.write_bool(WriteBits.LOAD_RECORDED, True)

        print("🎉 INWARD COMPLETE")

    finally:
        plc.disconnect()


# =========================================================
# OUTWARD CYCLE
# =========================================================

def outward_cycle(pickup_bin, drop_station):

    print("\n🚀 OUTWARD CYCLE")

    plc = connect_plc()

    try:

        check_stacker_health(plc)

        # handshake start
        plc.write_bool(WriteBits.LOAD_RECORDED, True)
        plc.write_bool(WriteBits.UNLOAD_RECORDED, True)

        wait_until_free(plc)

        plc.write_dint(WriteDints.UNLOAD_PICKUP, pickup_bin)
        plc.write_dint(WriteDints.UNLOAD_DROP, drop_station)

        plc.write_bool(WriteBits.SET_LOC_FOR_UNLOAD, True)

        wait_for_bit(plc, ReadBits.LOCATION_SET_COMPLETED, "LOCATION_SET_COMPLETED")
        plc.write_bool(WriteBits.SET_LOC_FOR_UNLOAD, False)
        plc.write_bool(WriteBits.LOAD_RECORDED, False)
        plc.write_bool(WriteBits.UNLOAD_RECORDED, False)

        pulse(plc, WriteBits.UNLOAD_START)

        wait_for_bit(plc, ReadBits.UNLOAD_IN_PROGRESS, "UNLOAD_IN_PROGRESS")

        wait_for_bit(plc, ReadBits.UNLOAD_DONE, "UNLOAD_DONE")

        plc.write_bool(WriteBits.UNLOAD_RECORDED, True)

        print("🎉 OUTWARD COMPLETE")

    finally:
        plc.disconnect()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    print("Testing code")
    #inward_cycle(1, 20)

    # time.sleep(5)

    # outward_cycle(30, 1)
