import serial
import socket
import struct
import time
import datetime
import sys

# AccuSense Ethernet Configuration
IP_ADDR = '192.168.1.70'
PORT = 502
UNIT_ID = 1
REG_ADDR = 30001
USE_INPUT_REGS = True
DATA_TYPE = 'float32'
BYTE_ORDER = 'big'
WORD_ORDER = 'little'
SCALE = 1.0

sock = None
ser_mfc = None
ser_smu = None

def main():
    openEthernet()
    global ser_mfc, ser_smu
    try:
        ser_mfc = serial.Serial(port='COM3', baudrate=19200, bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)
        openSerial(ser_mfc)
    except Exception as e:
        print(f"Warning: Could not connect to MFC on COM3: {e}")
        ser_mfc = None
    
    try:
        ser_smu = serial.Serial(port='COM8', baudrate=19200, bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)
        openSerial(ser_smu)
        initSMU()
    except Exception as e:
        print(f"Warning: Could not connect to SMU on COM8: {e}")
        ser_smu = None

    global sequence_
    sequence_ = []
    if (len(sys.argv) > 1):
        infile = sys.argv[1]
        readCSV(infile)
    
    now = datetime.datetime.now()
    timestamp = 0.
    f = open("CH2O_" + str(now.month) + str(now.day) + str(now.year) + "_" +
             str(now.hour) + str(now.minute) + str(now.second) + ".csv", "a")

    f.write("Time (s), Resistance (Ohms), CH2O (ppm), Temperature (C), Humidity (%), MFC_A_PSI, MFC_A_Temp, MFC_A_SLPM, MFC_A_Setpoint, MFC_B_PSI, MFC_B_Temp, MFC_B_SLPM, MFC_B_Setpoint, MFC_C_PSI, MFC_C_Temp, MFC_C_SLPM, MFC_C_Setpoint\n")
    start_time = time.time_ns()
    timestamp = time.time_ns()

    try:
        while True:
            outvals = []
            timestamp = time.time_ns() - start_time
            resistance = readSMU()
            ch2o_concentration = readAccuSense()
            # rh, t = readArduinoRHT()
            rh, t = -1, -1
            seconds = timestamp / 1000000000
            outvals.extend([seconds, resistance, ch2o_concentration, t, rh])
            vals = None
            for vals in sequence_:
                if seconds >= int(vals[0]):
                    print(vals)
                    writeMFC('A', vals[1].strip())
                    writeMFC('B', vals[2].strip())
                    writeMFC('C', vals[3].strip())
                    sequence_ = sequence_[1:]
            if vals is not None:
                for i in range (0, len(vals) - 1):
                    unit_id = chr(ord('A') + i)
                    mfc_vals = readMFC(unit_id)
                    if len(mfc_vals) >= 6:
                        psi = mfc_vals[1][1:]
                        temp = mfc_vals[2][1:]
                        slpm = mfc_vals[4][1:]
                        setpoint = mfc_vals[5][1:]
                        outvals.extend([psi, temp, slpm, setpoint])
            line = ','.join(str(num_val) for num_val in outvals) + '\n'
            print(line, end="")
            f.write(line)
    except KeyboardInterrupt:
        if ser_smu is not None:
            ser_smu.write((":OUTP OFF\n").encode())
        writeMFC('A', 0)
        writeMFC('B', 0)
        writeMFC('C', 0)
        closeEthernet()

def readCSV(infile):
    for line in open(infile, "r"):
        if (line.find("Time") != -1):
            print(line)
        else:
            vals = line.split(',')
            sequence_.append(vals)
            print(vals)

def openSerial(ser):
    # Open serial port, get and read identifier
    if ser is None:
        return
    if ser.isOpen():
        print(f"Connected to {ser.portstr}")
    else:
        ser.open()

def initSMU():
    if ser_smu is None:
        return
    # Reset SMU
    ser_smu.write(("*WAI\n").encode())
    ser_smu.write(("*RST\n").encode())

    # Set up voltage sweep 
    ser_smu.write((":SENS:FUNC:CONC OFF\n").encode())
    ser_smu.write((":SOUR:FUNC VOLT\n").encode())
    ser_smu.write((":SENS:FUNC 'CURR'\n").encode())
    ser_smu.write((":SENS:CURR:PROT 0.01\n").encode())
    ser_smu.write((":SOUR:VOLT:LEV 1\n").encode())
    ser_smu.write((":OUTP ON\n").encode())

def readSMU():
    if ser_smu is None:
        return float('nan')
    try:
        ser_smu.write((":read?\n").encode())
        response = ser_smu.readline().decode().strip()
        vals = response.split(',')
        if len(vals) >= 2:
            resistance = float(vals[0]) / float(vals[1])
            return resistance
        else:
            return float('nan')
    except Exception:
        return float('nan')

def readAccuSense():
    # Read CH2O value over Modbus/TCP and return as float
    global sock
    if sock is None:
        openEthernet()
    addr0 = normalize_address(REG_ADDR, USE_INPUT_REGS)
    reg_count = 2 if DATA_TYPE == 'float32' else 1
    try:
        regs = read_registers(sock, UNIT_ID, addr0, reg_count, USE_INPUT_REGS)
        value = decode_value(regs, DATA_TYPE, BYTE_ORDER, WORD_ORDER, SCALE)
        return value
    except Exception:
        return float('nan')


def writeMFC(unit_id, setpoint):
    if ser_mfc is None:
        return
    actual_setpoint = -1000
    full_scale = 511.99
    while (abs(float(setpoint) - actual_setpoint)) > 0.005:
        set_val = float(setpoint) / full_scale * 65535
        ser_mfc.write((unit_id + str(set_val)).encode())
        readback_vals = readMFC(unit_id)
        if len(readback_vals) >= 6:
            actual_setpoint = float(readback_vals[5][1:])
        else:
            break
        

def readMFC(unit_id):
    global ser_mfc
    if ser_mfc is None:
        return [unit_id, 'P0', 'T0', 'X', 'F0', 'S0']
    outval = str(unit_id) + "\r"
    ser_mfc.write(outval.encode())
    response = ser_mfc.readline().decode().strip()
    mfc_readings = response.split(' ')
    return mfc_readings

# ---------------------
# Ethernet helpers
# ---------------------
def openEthernet():
    global sock
    if sock is not None:
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    try:
        s.connect((IP_ADDR, PORT))
        print(f"Connected to AccuSense at {IP_ADDR}:{PORT}")
    except Exception:
        print(f"Warning: Could not connect to AccuSense at {IP_ADDR}:{PORT}")
        try:
            s.close()
        except Exception:
            pass
        return
    sock = s

def closeEthernet():
    global sock
    try:
        if sock is not None:
            sock.close()
    except Exception:
        pass
    finally:
        sock = None

def normalize_address(addr, use_input):
    if use_input and addr >= 30001:
        return addr - 30001
    if (not use_input) and addr >= 40001:
        return addr - 40001
    return addr

def recv_exact(s, num_bytes):
    chunks = []
    total = 0
    while total < num_bytes:
        chunk = s.recv(num_bytes - total)
        if not chunk:
            raise ConnectionError('Socket closed unexpectedly')
        chunks.append(chunk)
        total += len(chunk)
    return b''.join(chunks)

def read_registers(s, unit_id, start_addr, count, use_input):
    # Use a monotonically increasing transaction id (wrap is fine)
    if not hasattr(read_registers, "txid"):
        read_registers.txid = 1  # type: ignore[attr-defined]
    read_registers.txid = (read_registers.txid + 1) & 0xFFFF  # type: ignore[attr-defined]
    txid = read_registers.txid  # type: ignore[attr-defined]

    function_code = 0x04 if use_input else 0x03
    pdu = struct.pack('>BHH', function_code, start_addr, count)
    mbap = struct.pack('>HHHB', txid, 0, 1 + len(pdu), unit_id)
    adu = mbap + pdu
    s.sendall(adu)

    mbap_resp = recv_exact(s, 7)
    _, _, length, unit = struct.unpack('>HHHB', mbap_resp)
    if unit != unit_id:
        raise ValueError('Unit ID mismatch in response')

    pdu_resp = recv_exact(s, length - 1)
    fc = pdu_resp[0]
    if fc & 0x80:
        exc_code = pdu_resp[1]
        raise ValueError('Modbus exception: function 0x%02X, code %d' % (fc, exc_code))

    byte_count = pdu_resp[1]
    data = pdu_resp[2:2 + byte_count]
    if len(data) != byte_count:
        raise ValueError('Incomplete register data')

    regs = []
    for i in range(0, len(data), 2):
        regs.append((data[i] << 8) | data[i + 1])
    return regs

def decode_value(registers, data_type, byte_order, word_order, scale):
    if data_type in ('uint16', 'int16'):
        raw = registers[0]
        if data_type == 'int16' and raw >= 0x8000:
            raw = raw - 0x10000
        val = float(raw)
        return val / scale if scale and scale != 0 else val

    if data_type == 'float32':
        if len(registers) < 2:
            raise ValueError('Need two registers for float32')
        r0, r1 = registers[0], registers[1]
        words = (r0, r1) if word_order == 'big' else (r1, r0)
        bytes_msb_to_lsb = []
        for w in words:
            hi = (w >> 8) & 0xFF
            lo = w & 0xFF
            if byte_order == 'big':
                bytes_msb_to_lsb.extend([hi, lo])
            else:
                bytes_msb_to_lsb.extend([lo, hi])
        b = bytes(bytes_msb_to_lsb)
        val = struct.unpack('>f', b)[0]
        return val

    raise ValueError('Unsupported DATA_TYPE')
if __name__ == '__main__':
    main()

