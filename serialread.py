import serial

ser_instec = serial.Serial(
    port='COM5',
    baudrate=1200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

def openSerial(ser):
    # Open serial port, get and read identifier
    if ser.isOpen():
        print(f"Connected to {ser.portstr}")
    else:
        ser.open()

openSerial(ser_instec)

while True:
    try:
        data = ser_instec.readline()
        print(data)
        while ser_instec.in_waiting:
            line = ser_instec.readline()
    except KeyboardInterrupt:
        ser_instec.close()
