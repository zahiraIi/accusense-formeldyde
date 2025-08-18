import serial
import time
import datetime
import os
import sys

ser_mfc = serial.Serial(
    port='COM3',
    baudrate=19200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

# ser_arduino = serial.Serial(
#     port='COM16',
#     baudrate=9600,
#     bytesize=serial.EIGHTBITS,
#     parity=serial.PARITY_NONE,
#     stopbits=serial.STOPBITS_ONE,
#     timeout=1
# )

ser_smu = serial.Serial(
    port='COM8',
    baudrate=19200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

def main():
    openSerial(ser_smu)
    # openSerial(ser_arduino)
    openSerial(ser_mfc)
    initSMU()

    global sequence_
    sequence_ = []
    if (len(sys.argv) > 1):
        infile = sys.argv[1]
        readCSV(infile)
    
    now = datetime.datetime.now()
    timestamp = 0.
    start_time = time.time_ns()
    timestamp = time.time_ns()

    try:
        while True:
            outvals = []
            timestamp = time.time_ns() - start_time
            resistance = readSMU()
            # rh, t = readArduinoRHT()
            rh, t = -1, -1
            seconds = timestamp / 1000000000
            outvals.extend([seconds, resistance, t, rh])
            for vals in sequence_:
                if seconds >= int(vals[0]):
                    print(vals)
                    writeMFC('A', vals[1].strip())
                    writeMFC('B', vals[2].strip())
                    writeMFC('C', vals[3].strip())
                    sequence_ = sequence_[1:]
            for i in range (0, len(vals) - 1):
                unit_id = chr(ord('A') + i)
                mfc_vals = readMFC(unit_id)
                psi = mfc_vals[1][1:]
                temp = mfc_vals[2][1:]
                slpm = mfc_vals[4][1:]
                setpoint = mfc_vals[5][1:]
                outvals.extend([psi, temp, slpm, setpoint])

            line = ','.join(str(num_val) for num_val in outvals) + '\n'
            print(line, end="")
    except KeyboardInterrupt:
        ser_smu.write((":OUTP OFF\n").encode()) #shut off SMU on KeyboardInterrupt
        writeMFC('A', 0)
        writeMFC('B', 0)
        writeMFC('C', 0)

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
    if ser.isOpen():
        print(f"Connected to {ser.portstr}")
    else:
        ser.open()

def initSMU():
    # Reset SMU
    ser_smu.write(("*WAI\n").encode())
    ser_smu.write(("*RST\n").encode())

    # Set up voltage sweep 
    ser_smu.write((":SENS:FUNC:CONC OFF\n").encode()) # concurrent functions off
    ser_smu.write((":SOUR:FUNC VOLT\n").encode()) # source voltage
    ser_smu.write((":SENS:FUNC 'CURR'\n").encode()) # current sense
    ser_smu.write((":SENS:CURR:PROT 0.01\n").encode()) # compliance current 
    ser_smu.write((":SOUR:VOLT:LEV 1\n").encode())
    ser_smu.write((":OUTP ON\n").encode())

def readSMU():
    ser_smu.write((":READ? \n").encode())
    response = ser_smu.readline().decode().strip()
    vals = response.split(',')
    resistance = float(vals[0]) / float(vals[1])
    return resistance

# def readArduinoRHT():
#     # Arduino reports every 500ms, which is faster than the poll cycle on SMU. Dump extra lines.
#     while ser_arduino.in_waiting:
#         line = ser_arduino.readline().decode().strip()
#     vals = line.split(',')
#     return float(vals[-1]), float(vals[-2])

def writeMFC(unit_id, setpoint):
    actual_setpoint = -1000
    full_scale = 511.99
    while (abs(float(setpoint) - (actual_setpoint))) > 0.005:
        if unit_id == 'A':
            full_scale = 511.99
        elif unit_id == 'B':
            full_scale = 511.99
        elif unit_id == 'C':
            full_scale = 511.99
#SLPM Units
        set_val = float(setpoint) / full_scale * 65535
        ser_mfc.write((unit_id + str(set_val)).encode())
        readback_vals = readMFC(unit_id)
        actual_setpoint = float(readback_vals[5][1:])
        

def readMFC(unit_id):
    outval = str(unit_id) + "\r"
    ser_mfc.write(outval.encode())
    response = ser_mfc.readline().decode().strip()
    mfc_readings = response.split(' ')
    return mfc_readings

if __name__ == '__main__':
    main()

