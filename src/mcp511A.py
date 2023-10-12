# ------------------------------------------------------------    Interpreting Functions     -----------------------------------------------------------

# These functions take the raw integer output from the device reponses and interpret it into actual values. 
# ex: the PowerFactor(PF) is a value that can be between -1 and 1, however the raw integer recieved is divided over the 16 bit register range
# thus 1 corrlates to 32768, -1 corelates to -32768, 0 to 0 and .5 would be 16389. governing equation PF = Raw Int / 32768
# there are diffrent equations for almost every register. 

def pfinterpreter(value):               # powerfactor formating func
    result = round(value / 32768, 2)
    return result

def linefreqinterpreter(value):
    #return f'{value}Hz'
    return value/1000

def ampsrmsinterpreter(value):          # calibrate reg for miliamps
    result = value / 1000
    #return f'{result}A'
    return result

def voltsrmsinterpreter(value):         # calibrate register for 1v = 100
    result = value / 100
    #return f'{result}V'
    return result

def powerinterpreter(value):            # calibrate register for 1 lsb = .01A
    result = value / 10
    # return f'{result}W'
    return result
def accactenergyinterpreter(value):     # calibrate register for miliwat
    result = ( value / 100 ) * 0.996    # .996 accounts for a consistant +.4% error that is always observed for accumulation measurments.
    #return f'{result}Wh'
    return round(result,1)

def noloadthreshinterpreter(value):     
    result = value / 10
    #return f'{result}W'
    return result

def fourbytereginterpreter(value):
    string = bin(value)[2:].zfill(32)
    result = string[:8] + '_' + string[8:16] + '_' + string[16:24] + '_' + string[24:]
    return result

def twobytereginterpreter(value):
    string = bin(value)[2:].zfill(16)
    result = string[:8] + '_' + string[8:]
    return result

def thermistorvinterpreter(value):
    temp = round((value - 154) / 3.09, 1)
    # return f'Raw: {value}, Temp: {temp} C'
    return temp

def rawinterpreter(value):
    return value
    
# -----------------------------------------------------------     REGISTER LIST --------------------------------------------------------
McpRegisters = {
# This dic contains the names, hex address and size of registers on the mcp39f511, most are included.
# The format is {'name' : (Address, Signed or not, size in bytes )}

# OUTPUT REGISTERS 
    'sysstatus'     : ('0x0002', False, 2, twobytereginterpreter),
    'sysversion'    : ('0x0004', False, 2, rawinterpreter),
    'volts'         : ('0x0006', False, 2, voltsrmsinterpreter),
    'linefreq'      : ('0x0008', False, 2, linefreqinterpreter),
    'temp'          : ('0x000a', False, 2, thermistorvinterpreter),
    'pf'            : ('0x000c', True, 2, pfinterpreter),
    'amps'          : ('0x000e', False, 4, ampsrmsinterpreter),
    'power'         : ('0x0012', False, 4, powerinterpreter),
    'rctpower'      : ('0x0016', False, 4, powerinterpreter),
    'apppower'      : ('0x001a', False, 4, powerinterpreter),
    'ienergy'       : ('0x001e', False, 8, accactenergyinterpreter),
    'eenergy'       : ('0x0026', False, 8, accactenergyinterpreter),
    'irctenergy'    : ('0x002e', False, 8, accactenergyinterpreter),
    'erctenergy'    : ('0x0036', False, 8, accactenergyinterpreter),
    'min1'          : ('0x003e', False, 4, rawinterpreter),
    'min2'          : ('0x0042', False, 4, rawinterpreter),
    'max1'          : ('0x0046', False, 4, rawinterpreter),
    'max2'          : ('0x004A', False, 4, rawinterpreter),

# CALIBRATION REGISTERS(AC)
    'resetcal'      : ('0x004e', False, 2, rawinterpreter), #write 0xa5a5 42405
    'ampgain'       : ('0x0050', False, 2, rawinterpreter),
    'voltgain'      : ('0x0052', False, 2, rawinterpreter),
    'pwrgain'       : ('0x0054', False, 2, rawinterpreter),
    'rctpwrgain'    : ('0x0056', False, 2, rawinterpreter),
    'ampoffset'     : ('0x005a', True, 2, rawinterpreter),
    'pwroffset'     : ('0x005c', True, 2, rawinterpreter),
    'rctpwroffset'  : ('0x005e', True, 2, rawinterpreter),
    'linefreqgain'  : ('0x0060', False, 2, rawinterpreter),
    'phasecomp'     : ('0x0062', True, 2, rawinterpreter),

# EMI REGISTERS
    'voltdropcomp'  : ('0x0064', False, 2, rawinterpreter),
    'incapcrntcomp' : ('0x0066', False, 2, rawinterpreter),
    'comprange'     : ('0x0068', False, 2, rawinterpreter),

# CALIBRATION REGISTERS(DC)
    'dcampgain'     : ('0x006c', False, 2, rawinterpreter),
    'dcvoltgain'    : ('0x006e', False, 2, rawinterpreter),
    'dcpwrgain'     : ('0x0070', False, 2, rawinterpreter),
    'dcampoffset'   : ('0x0072', True, 2, rawinterpreter),
    'dcpwroffset'   : ('0x0074', True, 2, rawinterpreter),

# ADC REGISTERS
    'offcalmsb'     : ('0x007a', False, 2, rawinterpreter),
    'offcal0'       : ('0x007c', False, 2, rawinterpreter),
    'offcal1'       : ('0x007e', False, 2, rawinterpreter),

# TEMP REGISTERS
    'ptempfreq'     : ('0x0080', False, 2, rawinterpreter),
    'ntempfreq'     : ('0x0082', False, 2, rawinterpreter),
    'ptempcrntcomp' : ('0x0084', False, 2, rawinterpreter),
    'ntempcrntcomp' : ('0x0086', False, 2, rawinterpreter),
    'ptemppwrcomp'  : ('0x0088', False, 2, rawinterpreter),
    'ntemppwrcomp'  : ('0x008a', False, 2, rawinterpreter),

# CONFIG REGISTERS
    'sysconfig'     : ('0x0094', False, 4, fourbytereginterpreter),
    'eventconfig'   : ('0x0098', False, 4, fourbytereginterpreter),
    'range'         : ('0x009c', False, 4, fourbytereginterpreter),
    'calamps'       : ('0x00a0', False, 4, rawinterpreter),
    'calvolts'      : ('0x00a4', False, 2, rawinterpreter),
    'calpwr'        : ('0x00a6', False, 4, rawinterpreter),
    'calrctpwr'     : ('0x00aa', False, 4, rawinterpreter),
    'pwrdivdigits'  : ('0x00be', False, 2, rawinterpreter),
    'accinterval'   : ('0x00c0', False, 2, rawinterpreter),
    'pwmperiod'     : ('0x00c2', False, 2, rawinterpreter),
    'pwmdutycycle'  : ('0x00c4', False, 2, rawinterpreter),
    'minmaxpnt1'    : ('0x00c6', False, 2, rawinterpreter),
    'minmaxpnt2'    : ('0x00c8', False, 2, rawinterpreter),
    'linefreqref'   : ('0x00ca', False, 2, rawinterpreter),
    'thermvoltcal'  : ('0x00cc', False, 2, rawinterpreter),
    'voltsaglim'    : ('0x00ce', False, 2, rawinterpreter),
    'voltsurgelim'  : ('0x00d0', False, 2, rawinterpreter),
    'overcurrent'   : ('0x00d2', False, 4, rawinterpreter),
    'overpower'     : ('0x00d6', False, 4, rawinterpreter),
    'overtemp'      : ('0x00da', False, 2, rawinterpreter),
    'lowvthresh'    : ('0x00dc', False, 2, rawinterpreter),
    'highvthresh'   : ('0x00de', False, 2, rawinterpreter),
    'noloadthresh'  : ('0x00e0', False, 2, noloadthreshinterpreter)

}

# ------------------------------------------------- Command Functions and Registers ----------------------------------------------------

# This is a block of code specifies the functions for McpCommands below and then are dispatched.
# The agruments for each function will be sent as a list so they should be refrenced by list index not name

def setpointer(regname):
# this function outputs the setpointer command and the address in big endian. Finds the address from the register list

    a = McpRegisters[regname][0]
    
    Cmdaddress = [0x0041]
    Hbyte = [int(a[-4:-2], 16)]
    Lbyte = [int(a[-2:], 16)]

    result = Cmdaddress + Hbyte + Lbyte

    return result       #returns list

def read(args): 
# args = [Register]
# Ex. Command: 'Read PF' where PF or PowerFactor is found from the register list, its address is set by set pointer

    if args[0] in McpRegisters.keys():

        Nbytes = [McpRegisters[args[0]][2]]

        Regaddress = setpointer(args[0])
        Cmdaddress = [0x4e]
        result = Regaddress + Cmdaddress + Nbytes

    else:
        raise ValueError('{} is not a valid register'.format(args[0]))
    
    return result

def write(args):
# args = [Register, value]
# Ex. Command: 'Write Range 256' Writes the Range Reg to 256. You can also input binary data directly if you so choose for thing like sys config registers
# Ex. Command: 'Write SysConfig b00001000_01000010_00010001_00001000' This writes this 32 bit number to the SysConfig register. 
# You start the string with 'b' and can add _ seperators to your discression
# Note: input values should be whole integers base 10. This will we the raw value the register will recieve, 

    if args[0] in McpRegisters.keys():

        Nbytes = [McpRegisters[args[0]][2]]
        Regaddress = setpointer(args[0])
        Cmdaddress = [0x4d]
        wrtdata = args[1]
        
        if wrtdata[0:1] == 'b':                     # handles bit string inputs
            Formated = wrtdata.replace("_", "")[1:]

            if (len(Formated) / 8) == Nbytes[0]:
                value = int(Formated, 2)      
                data = list(value.to_bytes(Nbytes[0], byteorder = 'little'))
                
            else:
                raise ValueError('length of binary string: {}, size of register: {}'.format(len(Formated), (Nbytes[0] * 8)))

        else:                                       # handles integer inputs
            value = int(wrtdata)                                                 
            data = list(value.to_bytes(Nbytes[0], byteorder = 'little', signed = McpRegisters[args[0]][1]))

    else:
         raise ValueError('{} is not a valid register'.format(args[0]))

    result = Regaddress + Cmdaddress + Nbytes + data
    return result

def saveflash():
    return [0x53]

def pageread(args): 
# args = [pagenumber]

    Cmdaddress = [0x42]
    Pagenumber = [int(args[0])]
    result = Cmdaddress + Pagenumber

    return result

def pagewrite(args): 
# args = [pagenumber, data]  ** Data should be listed as a single block with bytes sperated by a comma as in hex format
# ex Command: 'PageWrite 2 10,14,1e,......' -- This writes 10,20,30,...etc to page 2. Note: all 16 bytes for the page must be provided.

    Cmdaddress = [0x50]
    Pagenumber = [int(args[0])]
    lst = args[1].split(',')
    data = [int(x) for x in lst]
    data.reverse()

    result = Cmdaddress + Pagenumber + data
    return result

def bulkerase():
    return [0x4f]

def autogain():
    return [0x5a]

def autorctgain():
    return [0x7a]

def autofrqgain():
    return [0x76]

def saveenergy():
    return [0x45]


McpCommands = {
# This dict holds | key : (comand register, the number of additioinal parameters to be accepted for each command, dispatch function) |
# Ex. Read command only accepts one addition paramter -- where to read
# Write accepts 2, where to write and data. saveflash accepts no additional parameters

# COMMAND REGISTERS -- Ref datasheet for descriptions of commands
    'read'          : ('0x4e', 1, read),
    'write'         : ('0x4d', 2, write),
    'saveflash'     : ('0x53', 0, saveflash),
    'setpointer'    : ('0x41', 1, setpointer),
    'pageread'      : ('0x42', 1, pageread),
    'pagewrite'     : ('0x50', 2, pagewrite),
    'bulkerase'     : ('0x4f', 0, bulkerase),
    'autogain'      : ('0x5a', 0, autogain),
    'autorctgain'   : ('0x7a', 0, autorctgain),
    'autofrqgain'   : ('0x76', 0, autofrqgain),
    'saveenergy'    : ('0x45', 0, saveenergy)

}
