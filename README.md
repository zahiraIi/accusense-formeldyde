## Atmosense AccuSense CH2O Data Logging (with SMU and MFC Control)

Production-ready instructions and documentation for operating two lab scripts used to collect formaldehyde (CH2O) sensor data with a Source Measure Unit (SMU), optionally read AccuSense CH2O concentration via Modbus/TCP, and control up to three Mass Flow Controllers (MFCs).

### Contents

- Overview
- Features
- Hardware requirements
- Software requirements
- Installation
- Configuration
- Quick start
- Input sequence CSV format
- Output data schema
- Operational guidance and safety
- Troubleshooting
- Repository layout
- References and citation
- License

---

### Overview

This repository contains two primary data acquisition scripts:

- `SMU-Test_CH2O.py`: Reads sensor resistance via a SCPI-compatible SMU over serial, controls up to three MFC channels (A/B/C) over serial, and logs to CSV.
- `SMU-Test_CH2O_ETH.py`: All of the above, plus reads an AccuSense CH2O concentration over Ethernet (Modbus/TCP) and includes it in the log.

Both scripts support an optional sequence file to schedule MFC setpoint changes over time.

### Features

- **SMU integration**: Configures and reads current/voltage to compute resistance.
- **MFC control (A/B/C)**: Closed-loop write/readback of setpoints until target within tolerance.
- **AccuSense integration (optional)**: Modbus/TCP read of CH2O concentration.
- **CSV logging**: Time-stamped files with stable programmatic column ordering.
- **Graceful shutdown**: On Ctrl-C, SMU output disabled and MFCs commanded to 0.

---

### Hardware requirements

- SCPI-compatible SMU with serial connectivity (e.g., Keysight/Keithley class). Serial: 19200 baud, 8N1.
- Up to three Mass Flow Controllers (MFCs) connected to a serial interface. Default port `COM3` in scripts.
- Optional: AccuSense CH2O analyzer connected via Ethernet (Modbus/TCP, default port 502).
- Optional: Arduino for RH/T (currently disabled in code).

Note: The scripts default to Windows-style COM ports. On macOS/Linux, update serial device paths (e.g., `/dev/tty.usbserial-XXXX`).

---

### Software requirements

- Python 3.9+ (3.11 recommended)
- Packages:
  - `pyserial`

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install pyserial
```

---

### Installation

Clone or download this repository to your lab workstation. No build step is required.

```bash
git clone <your_repo_url>
cd atmosense-accusense-data-logging-formeldyhde
```

If you use a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install pyserial
```

---

### Configuration

Update these parameters in the scripts to match your lab setup.

- Serial ports (Windows examples below):
  - MFC: `COM3`
  - SMU: `COM8`
  - Serial format: 19200 baud, 8 data bits, no parity, 1 stop bit, 1 s timeout
- MFC full-scale flow: hardcoded as `511.99` (SLPM). Adjust if your MFCs differ.
- AccuSense (in `SMU-Test_CH2O_ETH.py`):
  - `IP_ADDR = '192.168.1.70'`
  - `PORT = 502`
  - `UNIT_ID = 1`
  - `REG_ADDR = 30001` (logical; normalized internally to zero-based)
  - `USE_INPUT_REGS = True` (function 0x04) or set `False` to use holding registers (0x03)
  - `DATA_TYPE = 'float32'`
  - `BYTE_ORDER = 'big'` and `WORD_ORDER = 'little'` (adjust to your device)
  - `SCALE = 1.0`

macOS/Linux serial ports: Replace `COMx` with the correct device (e.g., `/dev/tty.usbserial-1410`). Ensure your user has permission to access serial devices.

### Output data schema

Files are comma-separated, with one data record per line. Columns differ slightly between scripts.

1) `SMU-Test_CH2O_ETH.py` (Ethernet + serial):

Header written by script:

```csv
Time (s), Resistance (Ohms), CH2O (ppm), Temperature (C), Humidity (%), MFC_A_PSI, MFC_A_Temp, MFC_A_SLPM, MFC_A_Setpoint, MFC_B_PSI, MFC_B_Temp, MFC_B_SLPM, MFC_B_Setpoint, MFC_C_PSI, MFC_C_Temp, MFC_C_SLPM, MFC_C_Setpoint
```

Notes:

- `Resistance (Ohms)` is computed as V/I from the SMU reading.
- `CH2O (ppm)` is read via Modbus/TCP and decoded according to byte/word order settings.
- `Temperature (C)` and `Humidity (%)` placeholders are currently `-1` unless Arduino integration is enabled in code.
- `MFC_*` fields are parsed from the MFC readback string; indexing assumes a space-delimited response with fields in positions consistent with `readMFC`.

2) `SMU-Test_CH2O.py` (serial only):

Header written by script (currently minimal):

```csv
Time (s), Resistance (Ohms)
```

Actual values appended per record (in order):

```csv
Time (s), Resistance (Ohms), Temperature (C), Humidity (%), [MFC_A_PSI, MFC_A_Temp, MFC_A_SLPM, MFC_A_Setpoint, MFC_B_..., MFC_C_...]
```

Important: Downstream processors should not rely solely on the header row in this script; prefer position-based parsing or update the header to match your configuration before production runs.

### Troubleshooting

- Serial port not found:
  - Windows: Check Device Manager for `COMx` assignment.
  - macOS/Linux: Use `ls /dev/tty.*` or `dmesg | grep tty` to find the device; update the script.
  - Permissions (macOS/Linux): Ensure your user has rights to serial devices (e.g., dialout/uucp groups) or run via `sudo` if policy permits.
- No AccuSense data / NaN values:
  - Confirm `IP_ADDR`, `PORT`, and network connectivity.
  - Verify `UNIT_ID`, `REG_ADDR`, and whether your device publishes on input vs holding registers.
  - Adjust `BYTE_ORDER` and `WORD_ORDER` to match the instrument’s float32 representation.
- MFC setpoint not converging:
  - Confirm the readback string format and indices used in `readMFC`.
  - Validate `full_scale` and tolerance used in the write loop.
- Resistance values look wrong:
  - Check SMU source/measure configuration and wiring; the script assumes V-source and I-sense.

---

### Repository layout

- `SMU-Test_CH2O.py` — SMU + MFC logging (serial)
- `SMU-Test_CH2O_ETH.py` — SMU + MFC + AccuSense logging (Ethernet + serial)
- `MFC-Test.py` — MFC-specific testing (if present)
- `serialread.py` — Serial helper example (if present)
- `socketread.py` — Socket/Modbus example (if present)