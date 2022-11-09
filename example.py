from serialLG1800 import serialLG1800 as slg

lgport = 'socket://192.168.0.8:3800'
lg = None

def initLG():
    lg = slg.LG1800(lgport)
    
def fetchInputs():
    if lg.connected == True:
        # retrieve the status of external input used by the operator
        lg.inputLevels()
        # do something
        
def riconnectLG(event=None):
    if lg.connected == False:
        if lg.connect(lgport):
            fetchInputs()

def runCT():
    s = {}
    # [...] fetch settings from database
    
    return lg.runCT(s["ttCT_absolute"], 
       s["ttCTcheckImax"], s["ttCTImin"],
       s["ttCTImax"], s["ttCTInom"], s["ttCTItolpos"], 
       s["ttCTItolneg"], s["forAutotest"])            

initLG()

# the test bench can allow the connection of two devices, but only one at a time is under test
# so the operator can connect an appliance while the other is under test.
# an output of the LG1800 is used to drive a contactor and switch from one product to the other
lg.outputFunctional("toggleEXT")

# disconnect every output
lg.oF("OFF") # translates in serial command "*SET 000;006" disable outputs to contactors controlling L1 and L2 
# disconnect any capacitor used during the functional tests
lg.oF("0uf") # translates in serial command "*SET 112;000" disable all autputs connected to phase capacitors
# run Continuity Test
resultsCT = runCT()
