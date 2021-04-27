# Power Supplies series PSL-2401/2402/3604 communication

Python implementation of control protocol for PSL-series Power Supply.

### The current version features:
- getting list of compatible ports
- working WAKE communication (send/receive/decode commands)
- reading the most main data from power supply unit
  (name, version, current, voltage, states: on/cc/cv/ocp/opp/otp/ovp)

### Known problems:
- not handling port read/write timeouts
  
### Tested on:
OS X 10.15, Python 3.8
PSL-2402 + USB-TTL
PSL-2402 + Bluetooth HC-06 module

## Documentation
PSL-2401/02 website: http://www.leoniv.diod.club/projects/power/psl-2401/psl-2401.html
