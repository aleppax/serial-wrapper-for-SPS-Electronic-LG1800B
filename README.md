# serial-wrapper-for-SPS-Electronic-LG1800B
Wrapper for communicating with a programmable SPS Electronic LG1800B as a serial interface.

Wrapper for communicating with a programmable SPS Electronic LG1800B as a serial interface.
The library creates a layer of abstraction
It talks via serial port or ethernet port and depends on pySerial.
The code could have been generalized to every SPS model but there are safety implications:
The LG1800 is considered "safe" since it can't output more than 12 mA DC.
Anyway the functional test shall be carried out last, and the externally feeded line must be safegurded externally by appropriate means.
