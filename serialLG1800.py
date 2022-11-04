#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Alessandro Proglio"
__version__ = "1.0"
__license__ = "MIT"

#  serialLG1800.py
#  
#    Copyright 2017 Alessandro Proglio <ale.proglio@gmail.com>
#
#    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
#    documentation files (the "Software"), to deal in the Software without restriction, including without limitation 
#    the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, 
#    and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be included in all copies or substantial 
#    portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED 
#    TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#     OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
#     DEALINGS IN THE SOFTWARE.

import logging
import serial
import time
import sys
from . import vibes
# import pyaudio

class LG1800(object):
    """ Wrapper for communicating with a programmable SPS Electronic LG1800B as a serial interface.
    The library creates a layer of abstraction
    It talks via serial port or ethernet port and depends on pySerial.
    The code could have been generalized to every SPS model but there are safety implications:
    The LG1800 is considered "safe" since it can't output more than 12 mA DC.
    Anyway the functional test shall be carried out last, and the externally feeded line
    must be safegurded externally by appropriate means.
    """

    def send(self, text):
        # controlla solo la lunghezza del comando, l'assenza di ";", la formattazione delle cifre e dei valori binari
        if self.valid(text,"NOREPLY"):
            try:
                self.s.write(bytes(text + '\n', 'UTF-8'))
                self.fetchERRqueue()
            except:
                logging.warning("Errore nell'invio della richiesta: " + text, exc_info=True)
                self.connected = False
        else:
            logging.warning("Errore di validazione nel tentativo di inviare " + text)

    def send_receive(self, text):
        if self.valid(text,"REPLY"):
            try:
                self.s.write(bytes(text + '\n', 'UTF-8'))
                try:
                    response = self.s.readline()
                    # unicode: 60(<) 61(=) 62(>)
                    if response[0] in (60,61,62):
                        return response[1:]
                    if response == None:
                        logging.warning("ricevuta risposta anomala")
                        response = b'0'
                    return response
                except:
                    e = sys.exc_info()
                    logging.error("Errore nella lettura della porta seriale", exc_info=True)
                    logging.error(e)
                    self.fetchERRqueue()
                    self.connected = False
                    response = b'0'
                    return response
            except:
                e = sys.exc_info()
                logging.error("Errore nell'invio della richiesta: " + text, exc_info=True)
                logging.error(e)
                self.connected = False
                response = b'0'
                return response
        else:
            logging.warning("Errore di validazione nel tentativo di inviare " + text)
            response = b'0'
            return response
 
    def decodeIDN(self, rawIDN):
        # CSV
        logging.debug("interpreto la stringa: %s", rawIDN)
        parts = rawIDN.split(b',')
        idn = {
        'device' : parts[0],
        'firmware' : parts[1].split(b'Ver. ')[1],
        'sn' : parts[2][4:-2]
        }
        return(idn)
        
    def decodeMOD(self, rawMOD):
        ''' unsigned short int 0-255
        ‘Communication’ and ‘Remote mode’ parameter have meaning only if ‘Control type’ is ‘Automatic’.
        bit   Item          Description
        0     remote mode   0 = Testing
        1     remote mode   0
        2     remote mode   0
        3   communication   0
        4   communication   1 = Ethernet, 0 = RS-232
        5    control type   0 Manual, 1 Automatic, 0 Digital
        6    control type   0 Manual, 0 Automatic, 1 Digital
        7    control type   0 Manual, 0 Automatic, 0 Digital
        '''
        communication = (rawMOD >> 4) & 1
        controlType = (rawMOD >> 5) & 3
        return(communication,controlType)
        
    def decodeERR(self, rawERR):
        ''' unsigned short int 0-255
        Decodes the error queue.
        (mostly comunication errors).
        Number  Description
        200     Queue overflow
        0       No error
        2       Missing end character
        3       Wrong command
        4       Wrong MEAS parameter
        5       Wrong CONF parameter
        6       Wrong SYST parameter
        7       Wrong READ parameter
        8       Wrong DISP parameter
        9       Unable to start measurement
        '''
        lserr = rawERR.split(b',')
        nerrore = lserr[0]
        msgerrore = lserr[1]
        return(nerrore, msgerrore)
        
    def fetchERRqueue(self):
        oldestError = self.decodeERR(self.send_receive("*ERR?"))
        if int(oldestError[0]) != 0:
            logging.debug("trovato un errore %s - %s",oldestError[0] , oldestError[1])
            #self.fetchERRqueue()
    
    def connect(self, port):
        # there are two types of connection: serial over RS232 or over TCP/IP. 
        # PySerial can handle both types
        self.s = None
        if ('COM' in port) or ('tty' in port):
            # TODO: testare la connesione RS232 con un apperecchio
            self.s = serial.Serial()
            self.s.port = port
            self.s.timeout = 1
            try:
                self.s.open()
                if self.s.is_open:
                    logging.info("connected to serial port %s", port)
                    self.connected = True
                    return 1
            except serial.SerialException:
                logging.error("Errore nel tentativo di stabilire una connessione seriale. Nuovo tentativo tra 30 secondi.", exc_info=True)
                logging.info('In atesa di connessione al LG1800. Nuovo tentativo tra 30 secondi.')
                time.sleep(28)
                try:
                    self.s.open()
                    if self.s.is_open:
                        logging.info("connected to serial port %s", port)
                        self.connected = True
                        return 1
                except serial.SerialException:
                    logging.error("Errore nel tentativo di stabilire una connessione seriale. Nuovo tentativo tra 30 secondi.", exc_info=True)
                    return 0
        else:
            try:
                self.s = serial.serial_for_url(port, timeout=1)
                logging.info("connected to serial port %s", port)
                self.connected = True
                return 1
            except serial.SerialException:
                logging.error("Errore nel tentativo di stabilire una connessione seriale-ethernet.", exc_info=True)
                return 0
    
    def valid(self, text, reply):
        parts = text.split(" ")
        # commands with parameters are checked in setConfiguration()
        # remove from this list the commands that are not allowed.
        # some of this commands cause the device to send a reply.
        # Make sure that the reply is fetched or there will be a
        # misalignment between requests and replies
        noparsNoreplyCommands = ('*CEQ','*CLS','*RST','*LLO','MEAS:CT','MEAS:PW',
        'MEAS:I5','CONF:PW:DEF','CONF:I5:DEF','CONF:H5:DEF','MEAS:H5','CONF:F1:DEF',
        'CONF:L1:DEF','MEAS:F1','MEAS:L1','DISP:CLS','SYST:HALT','SYST:STFK'
        )
        parsNoreplyCommands = ('CONF:H5:ITYP:TOTAL','CONF:H5:ITYP:REAL')
        noparsCommands = ('*IDN?','*VER?','*EXT?','*MOD?','*STA?','*ERR?',
        '*LLO?','*INPW?','MEAS?','READ:CT:CURR?','CONF:PW:TIME?','CONF:PW:IMIN?',
        'CONF:PW:UNOM?','CONF:PW:MODE?','READ:PW:CURR?','READ:PW:VOLT?',
        'READ:PW:RES?','READ:I5:VOLTMIN?','CONF:I5:TIME?','CONF:I5:RAMP?',
        'CONF:I5:RDWN?','CONF:I5:USTART?','CONF:I5:UNOM?','CONF:I5:RMIN?','CONF:I5:IRMIN?',
        'CONF:I5:IRMAX?','CONF:I5:RERR?','CONF:I5:SKTYP?','CONF:I5:CON?','CONF:I5:SKINP?',
        'READ:I5:VOLT?','READ:I5:VOLTMAX?','READ:I5:CURR?','READ:I5:CURRMAX?',
        'READ:I5:CURRMIN?','READ:I5:RES?','READ:I5:RESMAX?','READ:I5:RESMIN?','CONF:H5:TIME?',
        'CONF:H5:RAMP?','CONF:H5:RDWN?','CONF:H5:UTYP?','CONF:H5:USTART?','CONF:H5:UNOM?',
        'CONF:H5:IMAX?','CONF:H5:IMIN?','CONF:H5:ITYP?','CONF:H5:IRMIN?','CONF:H5:IRMAX?',
        'CONF:H5:RERR?','CONF:H5:ARC?','CONF:H5:CON?','CONF:H5:SKTYP?',
        'READ:H5:VOLT?','READ:H5:VOLTMAX?','READ:H5:VOLTMIN?','READ:H5:CURR?',
        'READ:H5:CURRMAX?','READ:H5:CURRMIN?','READ:H5:ARC?','READ:H5:ARCMIN?','READ:H5:ARCMAX?',
        'CONF:F1:TIME?','CONF:F1:SKTYP?','CONF:F1:SKINP?','CONF:F1:PWR?',
        'READ:F1:CURR?','READ:F1:CURRMAX?','READ:F1:CURRMIN?','CONF:L1:TIME?','CONF:L1:SKTYP?',
        'CONF:L1:SKINP?','CONF:L1:UNOM?','CONF:L1:CURRMAX?','CONF:L1:CURRMIN?',
        'READ:L1:VOLT?','READ:L1:VOLTMAX?','READ:L1:VOLTMIN?','READ:L1:CURR?',
        'READ:L1:CURRMAX?','READ:L1:CURRMIN?','SYST:LICENSE?','SYST:HVG18:T?'
        )
        if len(parts) == 1:
            if reply == "NOREPLY":
                if text in noparsNoreplyCommands:
                    return True
                elif text in parsNoreplyCommands:
                    return True
                else:
                    return False
            elif reply == "REPLY":
                if text in noparsCommands:
                    return True
                else:
                    return False
        # parametro intervallo
        # 
        # TODO (if necessary)
        return True
    
    def fixedFloatSerial(self,value):
        # returns a string for serial communication
        # format an input value as a numerical float NNN.N
        # the non‐important leading zeroes can be deleted
        # value should be float between 0.1 and 999.0 (NNN.N)
        value = "{0:.1f}".format(float(value))
        # overwrite to the limit value
        if value >= '999.0':
            value = '999.0'
        elif value <= '0.1':
            value = '0.1'
        return value
        
    def fpFloatSerial(self,value):
        # returns a string for serial communication
        # format an input value as a floating point numerical N.NNNE+/‐NN
        value = "{0:.3e}".format(float(value))
        # overwrite to the limit value
        exponent = value[-2:]
        if exponent >= '99':
            exponent = '99'
            value = value[:-1] + exponent
        return value
        
    def bit16hexSerial(self,value):
        return value
        
    def bit32hexSerial(self,value):
        return value
    
    def integer2digit(self,value):
        value = "{0:2}".format(int(value))
        # overwrite to the limit value
        if value[0] == " ":
            value = "0" + value[1]
        return value
    
    def displayRow(self,text,row):
        request = 'DISP:ROW' + str(row) + ' "' + str(text) + '"'
        self.send(request)
        
    def displayRows(self,text):
        self.displayRow(text[:20],1)
        time.sleep(self.snooze)
        self.displayRow(text[20:40],2)
        time.sleep(self.snooze)
        self.displayRow(text[40:60],3)
        time.sleep(self.snooze)
        self.displayRow(text[60:80],4)

    
    def setConfiguration(self, par, value):
        '''
        NOTE: DON'T rely on the default values stated in the
        official SPS protocoll communication documents.
        
        currently validated pars:
        parameter     | value  range        |  default
        
        CONF:PW:TIME  | time, 0.1-999.0     | 1.0
        CONF:PW:IMIN  | A, 10-30            | 10.0 (1.000E+01)
        CONF:PW:UNOM  | V, 6/12             | 12
        CONF:PW:MODE  | OFF/MAN/AUTO        | OFF
        CONF:I5:TIME  | time, 0.1-999.0     | 1.0
        CONF:I5:RAMP  | time, 0.1-999.0     | 1.0
        CONF:I5:RDWN  | OFF/ON              | OFF
        CONF:I5:USTART| V,   0-6000 (4000*) | 100   *power socket
        CONF:I5:UNOM  | V, 100-6000         | 1000
        CONF:I5:RMIN  | ohm, N.NNNE+NN      | 5.000E+06
        CONF:I5:IRMIN | A, N.NNNE+NN        | 0.0 (0.000E+00)
        CONF:I5:IRMAX | A, N.NNNE+NN        | 0.01 (1.000E-02)
        CONF:I5:RERR  | EXTRA|EOR|NORM      | NORM
        CONF:I5:SKTYP | OFF|SK|SW|IMP|HOLD  | OFF
        CONF:I5:CON   | SOCK|PROB|SK2|SW    | SOCK
        CONF:I5:SKINP | 1-16                | 0
        CONF:H5:TIME  | time, 0.1-999.0     | 1.0
        CONF:H5:RAMP  | time, 0.1-999.0     | 0.0
        CONF:H5:RDWN  | OFF/ON              | OFF
        CONF:H5:UTYP  | SYNC|AC50|AC60|DC   | AC50
        CONF:H5:USTART| V, 0-6000DC 0-5500AC| 0.0 (0.000E+00)
        CONF:H5:UNOM  |100-6000DC 100-5500AC| 1000 (1.000E+03)
        CONF:H5:IMIN  |0-10mA DC 0-3,3mA AC | 0.0 (0.000E-00)
        CONF:H5:IMAX  |0-10mA DC 0-3,3mA AC | 0.001(1.000E-03)
        CONF:H5:ITYP  | REAL|TOTAL          | TOTAL
        CONF:H5:IRMIN | A, N.NNNE+NN        | 0.0 (0.000E+00)
        CONF:H5:IRMAX | A, N.NNNE+NN        | 0.01 (1.000E-02)
        CONF:H5:RERR  | EXTRA|EOR|NORMAL    | NORMAL
        CONF:H5:ARC   | 0-100               | 50
        CONF:H5:CON   | SOCK|PROB|SK2|SW    | SOCK
        CONF:H5:SKTYP | OFF|SK|SW|IMP|HOLD  | OFF
        CONF:H5:SKINP | 1-16                | 0
        CONF:F1:TIME  | time, 0.1-999.0     | 2.0
        CONF:F1:SKTYP | OFF|IMP|HOLD        | OFF
        CONF:F1:SKINP | 1-16                | 0
        CONF:F1:PWR   | OFF/ON              | OFF
        CONF:L1:TIME  | time, 0.1-999.0     | 1.0
        CONF:L1:SKTYP | OFF|IMP|HOLD        | OFF
        CONF:L1:SKINP | 1-16                | 0
        CONF:L1:UNOM  | V 100-270           | 253
        CONF:L1:CURRMAX| A, 0-10 mA         | 0.0 (0.000E+00)
        
        '''
        timeParameters = ("PW:TIME","I5:TIME","I5:RAMP","H5:TIME","H5:RAMP","F1:TIME","L1:TIME")
        inputParameters = ("I5:SKINP","H5:SKINP","F1:SKINP","L1:SKINP")
        floatParameters = ("PW:IMIN","I5:IRMIN","I5:IRMAX","I5:USTART","I5:UNOM","I5:RMIN","I5:IRMIN",
        "H5:USTART","H5:UNOM","H5:IMIN","H5:IMAX","H5:IRMIN","H5:IRMAX",
        "L1:UNOM","L1:CURRMAX")
        onoffParameters = ("I5:RDWN","H5:RDWN","F1:PWR")
        nosend = ("H5:ITYP","L1:CURRMAX")
        # parameters with standard value ranges
        if par in timeParameters:
            value = self.fixedFloatSerial(value)
        elif par in floatParameters:
            value = self.fpFloatSerial(value)
        elif par in onoffParameters:
            value = value.upper()
            if value not in ('OFF','ON'):
                value = 'OFF'
        elif par in inputParameters:
            value = self.integer2digit(value)
            if value < '01':
                value = '01'
            elif value > '16':
                value = '16'
        # parameters with specific values
        elif par == "PW:UNOM":
            value = "{0:d}".format(value)
            if value < '9':
                value = '6'
            else:
                value = '12'
        elif par == "PW:MODE":
            value = value.upper()
            if value not in ('OFF','MAN','AUTO'):
                value = 'OFF'
        elif par == "I5:RERR":
            value = value.upper()
            if value not in ('EXTRA','EOR','NORM'):
                value = 'NORM'
        elif (par == "I5:SKTYP") or (par == "H5:SKTYP"):
            value = value.upper()
            if value not in ('OFF','SK','SW','IMP','HOLD'):
                value = 'OFF'
        elif (par == "F1:SKTYP") or (par == "L1:SKTYP"):
            value = value.upper()
            if value not in ('OFF','IMP','HOLD'):
                value = 'OFF'
        elif (par == "I5:CON") or (par == "H5:CON"):
            value = value.upper()
            if value not in ('SOCK','PROB','SK2','SW'):
                value = 'SOCK'
        elif par == "H5:ITYP":
            value = value.upper()
            if value not in ('REAL','TOTAL'):
                value = 'TOTAL'
        elif par == "H5:RERR":
            value = value.upper()
            if value not in ('EXTRA','EOR','NORMAL'):
                value = 'NORMAL'
        elif par == "H5:ARC":
            value = "{0:d}".format(value)
            if value < '0':
                value = '0'
            elif value > '100':
                value = '100'
        else:
            logging.info("Missing validating function for input setting %s", par)
        # validate input  
        if par in nosend:
            pass
        else:    
            request = "CONF:" + par + " " + value
            self.send(request)
        
    
    def updateState(self):
        time.sleep(self.snooze)
        rawSTA = int(self.send_receive("*STA?"))
        ''' unsigned short int 0-255
        Decodes the status register describing the current activity when the device performs a test.
        ‘Test end’ bits have meaning only if ‘Activity’ bits are set to ‘Test finished’ (1000).
        high nibble: Activity
        low nibble: Test end result
        '''
        descriptionTest = {
        '0' : 'normal', '1' : 'stop button', '10' : 'HW test - high current', '11' : 'PW test - disconnected',
        '100' : 'PW disconnected/U low', '101' : 'SK control released', '110' : 'LC test - high current',
        '111' : 'extension failed', '1000' : 'HV test - low current', '1001' : 'PW test - U > U max',
        '1010' : 'Over Arc max', '1011' : 'Temp err', '1100' : 'Hardware err', '1111' : 'after syst:HALT'
        }
        descriptionActivity = {
        '0' : 'idle', '1' : 'test starting', '10' : 'test preparing', '11' : 'ramp up',
        '110' : 'measuring', '101' : 'ramp down', '100' : 'test end', '1000' : 'test finished'
        }
        self.activity = str(bin((rawSTA >> 4) & 15))[2:]
        self.testEnd = str(bin(rawSTA & 15))[2:]
        self.desActivity = descriptionActivity[self.activity]
        self.desTestEnd = descriptionTest[self.testEnd]
        logging.info(self.desActivity)

    def waitTestEnd(self, funky = lambda dura: None, duration = 1):
        # during the execution of a particulr test (updateState polls the status register)
        self.updateState()
        # we also update the status of all of the inputs
        self.inputLevels()
        # run some optional function (or run None)
        # this is where we run vibration tests (or other tests) during functional tests.
        funky(duration)
        # the duration of the funky function should be less than the 
        # duration of the test.
        while self.activity != '1000':
            self.updateState()
        # waiting for a little bit because sometimes the response from the device doesn't arrive, 
        # we suppose that waiting could help in avoiding missing responses.

    def inputLevel(self, digitalInput):
        '''
        Retrieves a single input and updates the inputs list
        The external digital inputs have number 1‐8, 
        the internal are in range 9‐16.
        For consistency with the self.inputs list indexes, the value 
        of digitalInput is increased by 1, therefore the 
        function accepts values between 0 and 15
        '''
        if (digitalInput > 15) or (digitalInput < 0):
            logging.warning("richiesta di stato di un input inesistente.")
            return(0)
        digitalInput = digitalInput + 1
        if digitalInput < 10:
            inpstr = "*INP 0"
        else:
            inpstr = "*INP "
        inputValue = int(self.send_receive(inpstr + str(digitalInput) + "?"))
        self.inputs[digitalInput] = inputValue
        return(inputValue)

    def inputLevels(self):
        '''
        01-08 external input
        09-16 internal input
        01 = free        (PIN 11) Avvio
        02 = free        (PIN 12) 1-Pronto
        03 = free        (PIN 13)
        04 = free        (PIN 14)
        05 = free        (PIN 15)
        06 = free        (PIN 16)
        07 = free        (PIN 17) 2-Pronto
        08 = EXT_START   (PIN 18) Fine
        ----------
        09 = button START on the front panel
        10 = start button on PE probe (PW test),HV pistols in HV test (IL3800X, HA38XX devices)
        11 = button DEVICE ON on KT1800 devices
        12 = button DEVICE OFF / NOT HALT on KT1800 devices
        13 = HV SK active in 1800 devices (I5 and H5 tests)
        14 = HV pistols in 1800 devices (I5 and H5 tests)
        15 = Fuse state, 1 = OK 0 = broken
        '''
        rawInputs = self.send_receive("*INPW?")
        inputs = [int(i) for i in bin(int(rawInputs))[2:]]
        missingZeros = 16 - len(inputs)
        while missingZeros > 0:
            missingZeros -= 1
            inputs.insert(0,0)
        inputs.reverse()
        self.inputs = inputs

    def oF(self, keyw):
        self.outputFunctional(keyw)
    
    def outputFunctional(self, keyw):
        # sets the fuses of the output. "REVERSE" "FORWARD" "OFF"
        # fuses are hardcoded, for the time being
        #  BIT  purpose forward reverse 230 115 0uf 10uf 20uf 30uf 40uf 50uf 60uf ext1 ext2 OFF  FT
        #   0   230/115V    x      x    1    0   x    x    x    x    x    x    x    x    x    x   x
        #   1   L1          1      0    x    x   x    x    x    x    x    x    x    x    x    1   0
        #   2   L2          0      1    x    x   x    x    x    x    x    x    x    x    x    1   0
        #   3   ext 1/2     x      x    x    x   x    x    x    x    x    x    x    1    0    x   x
        #   4   10uF        x      x    x    x   0    1    0    0    1    0    1    x    x    x   x
        #   5   20uF        x      x    x    x   0    0    1    0    0    1    1    x    x    x   x
        #   6   30uF        x      x    x    x   0    0    0    1    1    1    1    x    x    x   x
        #   7   free        x      x    x    x   x    x    x    x    x    x    x    x    x    x   x
        
        fuses = {
        "230V" : "000;001",
        "115V" : "001;000",
        "FORWARD" : "004;002",
        "REVERSE" : "002;004",
        "OFF"  : "000;006", # default condition to be set before an after any kind of test: both L1 and L2 active
        "FT"   : "006;000",
        "0uf"  : "112;000",
        "10uf" : "096;016",
        "20uf" : "080;032",
        "30uf" : "048;064",
        "40uf" : "032;080",
        "50uf" : "016;096",
        "60uf" : "000;112",
        "ext1" : "000;008",
        "ext2" : "008;000"
        }
        keyword = keyw
        # toggle between ext1 and ext2
        if keyword == "toggleEXT":
            if self.exta == "ext1":
                keyword = "ext2"
            else:
                keyword = "ext1"
            self.exta = keyword
        self.send("*SET " + fuses[keyword])
        time.sleep(self.snooze)
        
        
    def initQuadro(self, exta, mains, capacitor):
        # inizializzazione differita dei valori predefiniti in base alla sequenza di prova
        self.exta = exta
        self.mains = mains
        self.capacitor = capacitor
        self.outputFunctional(self.exta)
        self.outputFunctional(self.mains)
        
# ################ #
# Continuity Test  #
# ################ #

    def runCT(self, absolute=False, checkimax=False, imin=0, imax=0.6, nom=0.3, suptolerance=20, inftolerance=20, autotest=False):
        # si presume (con un discreto margine di errore) che le due fasi abbiano la stessa resistenza.
        # i limiti sono calcolati in base alle due fasi collegate in parallelo. Se ne deduce il valore di una
        # fase sola raddoppiando la resistenza.
        # absolute: (criterio di verifica dei risultati) TRUE = absolute ossia passa se compreso tra ttCTImin e ttCTImax,
        # FALSE = relative ossia passa se, ripetto ad un valore nomiale di ttCTInom, 
        # lo scarto rientra in una + ttCTItolpos percentuale o - ttCTItolneg percentuale
        #
        # runs the continuity test: 22-24 V DC between N and L1+L2 together, 
        # measuring the current, there's no PASS or Fail, just a measurement,
        # therefore we have to compare the result with the limits
        # R = V / I
        # V = 22-24 V
        # la resistenza del quadro e del cavo di alimentazione 
        # è circa 0,2  + 0,3 ohm = 0,5 ohm
        # first short circuit line1 and line2
        if not autotest:
            self.outputFunctional("OFF")
        self.send("MEAS:CT")
        self.waitTestEnd()
        current = float(self.send_receive("READ:CT:CURR?"))
        if not autotest:
            self.outputFunctional("OFF")
        result = True
        reason = ""
        # se il test viene eseguito con valutazione dello scarto percentuale rispetto ad un valore di riferimento
        if not absolute:
            imin = nom*(100-inftolerance)/100
            imax = nom*(100+suptolerance)/100
        # se il test viene eseguito con criteri di accettazione, considerali
        if current < imin:
            result = False
            reason = "Open circuit"
        elif current > imax:
            if checkimax:
                result = False
                reason = "Short circuit"
        # chiarire la relazione tra corrente e resistenza, ossia stabilire
        # il valore di tensione da usare per il calcolo, non è 22 V...
        # anche se con il multimetro ho visto un picco intorno ai 22V.
        # verifica resistenza...
        return({'current': current,'reason': reason,'result': result})

# ########################### #
#  Protective Wire Test (PW)  #
# ########################### #

    def runPW(self,rmin=0,rmax=1):
        # runs the Protective Wire Test: 6-12 V DC between PE and housing of DUT, 
        # measuring the resistance value: it should be between Rmin and Rmax
        # this test cycle can be used to perform: the Ground Bond Test or the Ground Continuity test
        # according to the EN 60335-1 the Earth continuity test requires at least 10A of current,
        # the presence of a supply cord determines the resistance limit of the appliance:
        #  with supply cord 0,2 ohm or 0,1 ohm + the resistance of the supply cord.
        #  without supply cord: 0,1 ohm
        # the test voltage can be set to 6 or 12 V 
        # returns a dict with the measured results.
        self.send("MEAS:PW")
        self.waitTestEnd()
        result =True
        reason = ""
        current = float(self.send_receive("READ:PW:CURR?"))
        voltageDrop = float(self.send_receive("READ:PW:VOLT?"))
        resistance = float(self.send_receive("READ:PW:RES?"))
        if resistance < rmin:
            result = False
            reason = "Resistance lower than Rmin"
        elif resistance > rmax:
            result = False
            reason = "Resistance greater than Rmax"
        return({'current': current,'voltageDrop': voltageDrop,'resistance': resistance,'reason': reason,'result': result})
        
# ###################### #
#  Insulation Test (IS)  #
# ###################### #

    def runIS(self,rmin=0):
        # runs the Insulation Resistance Test: with the insulation test, 
        # the insulation resistance between the contacted potentials is evaluated.
        # In case of insufficient or damaged electric strength of the DUT, an arc-over will occur.
        # The connection for class I devices is between L+N together and PE
        # for class II appliances the connection is between L+N and the chassis.
        self.send("MEAS:I5")
        self.waitTestEnd()
        result = True
        reason = ""
        voltage = float(self.send_receive("READ:I5:VOLT?"))
        voltMax = float(self.send_receive("READ:I5:VOLTMAX?"))
        voltMin = float(self.send_receive("READ:I5:VOLTMIN?"))
        current = float(self.send_receive("READ:I5:CURR?"))
        currentMax = float(self.send_receive("READ:I5:CURRMAX?"))
        currentMin = float(self.send_receive("READ:I5:CURRMIN?"))
        resistance = float(self.send_receive("READ:I5:RES?"))
        resistanceMax = float(self.send_receive("READ:I5:RESMAX?"))
        resistanceMin = float(self.send_receive("READ:I5:RESMIN?"))
        if resistance < rmin:
            result = False
            reason = "Resistance lower than Rmin"
        
        return({'voltage': voltage,
        'voltMax': voltMax,
        'voltMin': voltMin,
        'current': current,
        'currentMax': currentMax,
        'currentMin': currentMin,
        'resistance': resistance,
        'resistanceMax': resistanceMax,
        'resistanceMin': resistanceMin,
        'reason': reason,
        'result': result
        }
        )
        
# ############################### #
#   High Voltage Test H5 (AC/DC)  #
# ############################### #

    def runHV(self,imin=0,imax=0.003):
        # With the high voltage test, the electrical strength between the
        # contacted potentials is evaluated.
        # In case of insufficient or damaged electric strength of the
        # DUT, an arc-over will occur.
        self.send("MEAS:H5")
        self.waitTestEnd()
        result = True
        reason = ""
        voltage = float(self.send_receive("READ:H5:VOLT?"))
        voltMax = float(self.send_receive("READ:H5:VOLTMAX?"))
        voltMin = float(self.send_receive("READ:H5:VOLTMIN?"))
        current = float(self.send_receive("READ:H5:CURR?"))
        currentMax = float(self.send_receive("READ:H5:CURRMAX?"))
        currentMin = float(self.send_receive("READ:H5:CURRMIN?"))
        arc = float(self.send_receive("READ:H5:ARC?"))
        arcMax = float(self.send_receive("READ:H5:ARCMAX?"))
        arcMin = float(self.send_receive("READ:H5:ARCMIN?"))
        if current < imin:
            result = False
            reason = "Current lower than Imin"
        elif current > imax:
            result = False
            reason = "Current greater than Imax"
        
        return({'voltage': voltage,
        'voltMax': voltMax,
        'voltMin': voltMin,
        'current': current,
        'currentMax': currentMax,
        'currentMin': currentMin,
        'arc': arc,
        'arcMax': arcMax,
        'arcMin': arcMin,
        'reason': reason,
        'result': result
        }
        )

# ##################### #
#   Function Test (F1)  #
# ##################### #

    def runFT(self, imin=0, imax=10, pausa=0.1, duration=1, autotest=False):
        result = True
        reason = ""
        logging.info('autotest ' + str(autotest))
        if autotest:
            currentFwd = 0.0
            currentMaxFwd = 0.0
            currentMinFwd = 0.0
        else:
            self.outputFunctional("FT")
            self.outputFunctional(self.mains)
            self.outputFunctional(self.capacitor)
            self.outputFunctional("FORWARD")
            self.send("MEAS:F1")
            self.waitTestEnd(self.vibes,duration)
            currentFwd = float(self.send_receive("READ:F1:CURR?"))
            currentMaxFwd = float(self.send_receive("READ:F1:CURRMAX?"))
            currentMinFwd = float(self.send_receive("READ:F1:CURRMIN?"))
            time.sleep(pausa)
        self.outputFunctional("REVERSE")        
        self.send("MEAS:F1")
        self.waitTestEnd(self.vibes,duration)
        self.outputFunctional("OFF")
        self.outputFunctional("0uf")
        currentRev = float(self.send_receive("READ:F1:CURR?"))
        currentMaxRev = float(self.send_receive("READ:F1:CURRMAX?"))
        currentMinRev = float(self.send_receive("READ:F1:CURRMIN?"))
        # TODO: non c'è molta documentazione, quindi in base alle prime misurazioni
        # considerare se utilizare current o currentMax/currentMin
        if not autotest:
            minCurrentMeasured = min(currentFwd,currentRev)
            maxCurrentMeasured = max(currentFwd,currentRev)
        else:
            minCurrentMeasured = currentRev
            maxCurrentMeasured = currentRev
        if minCurrentMeasured < imin:
            result = False
            reason = "current lower than Imin"
        elif maxCurrentMeasured > imax:
            result = False
            reason = "current greater than Imax"
        else:
            result = True
        
        vtr = self.vibesTestResult
        self.vibesTestResult = self.defaultvibesTestResult
        if vtr["result"] == False:
            result = False
            reason = vtr["reason"]
        return({'currentFwd': currentFwd,
        'currentMaxFwd': currentMaxFwd,
        'currentMinFwd': currentMinFwd,
        'currentRev': currentRev,
        'currentMaxRev': currentMaxRev,
        'currentMinRev': currentMinRev,
        'reason': reason,
        'result': result,
        'vtr':vtr
        }
        )

# ########################### #
#  Leakage Current Test (L1)  #
# ########################### #

    def runLC(self):
        self.send("MEAS:L1")
        self.waitTestEnd()
        result = True
        reason = ""
        voltage = float(self.send_receive("READ:L1:VOLT?"))
        voltMax = float(self.send_receive("READ:L1:VOLTMAX?"))
        voltMin = float(self.send_receive("READ:L1:VOLTMIN?"))
        current = float(self.send_receive("READ:L1:CURR?"))
        currentMax = float(self.send_receive("READ:L1:CURRMAX?"))
        currentMin = float(self.send_receive("READ:L1:CURRMIN?"))
        return({'voltage': voltage,
        'voltMax': voltMax,
        'voltMin': voltMin,
        'current': current,
        'currentMax': currentMax,
        'currentMin': currentMin,
        'reason': reason,
        'result': result
        }
        )

# ############################### #
#  Vibration (noise) Test (Vibes) #
# ############################### #

    def vibes(self,duration):
        # select channel according to the status of ext1/ext2
        if self.exta == "ext1":
            channel = 0
        else:
            channel = 1
        pass



# ########################## #
#        System Init         #
# ########################## #

    def initConn(self, port):
        while True:
            self.connect(port)
            if not self.connected:
                logging.info("Riprovo tra 5 secondi.")
                time.sleep(5)
            else:
                logging.info("LG1800 connesso")
                break

    def testConnection(self):
        # the connection may be lost, here we check if this is the case.
        self.send_receive("*IDN?")
        if not self.connected:
            self.initConn(self.s.port)

    def initData(self):
        
        self.idn = self.decodeIDN(self.send_receive("*IDN?"))
        self.lgsn = self.idn['sn'].decode('latin_1')
        self.temperature = int(self.send_receive("SYST:HVG18:T?"))
        logging.info("temperature: " + str(self.temperature) + "°C")
        self.activity = None
        self.testEnd = None
        self.desActivity = None
        self.desTestEnd = None
        self.defaultvibesTestResult = {'reason': "",
        'result': True
        }
        self.vibesTestResult = self.defaultvibesTestResult
        self.lastSeqID = None
        self.lastSeqRev = None
        self.capacitor = "10uf"
        self.outputFunctional(self.exta)
        self.outputFunctional(self.mains)
        self.inputLevels()
        # audio
        self.vib = vibes.VibesAnalyzer()

    def __init__(self, port, debug=False):
        self.connected = False
        self.snooze = 0.1
        self.mains = "230V"
        self.exta = "ext1"
        self.initConn(port)
        self.initData()