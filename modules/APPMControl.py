import mcp511A
from mcp511A import McpCommands, McpRegisters
import serial
import time

def csum(frame):
# checksum of frame, = to byte addition -- modulus 256

    total = 0
    for byte in frame:
        total += byte
    result = [total % 256]

    return result

def get_cmd(commands):
# Takes in the commands to be sent to the meter in a form of string, it is then parsed and converted
# into a data frame filled byte data, the format is simply 'command *register *data command *register *data etc.'
# where the star represents optional parameter and depends on the command. register names are stored as keys
# in McpRegisters, Commands are stored in McpCommands, their descriptions are in the mcp datasheet.


    cmds = commands.split()
    cmd_frame = [0xa5, 0x0,]                             
    readitems = []
    

    specials = ('volts', 'amps', 'power', 'rctpower')        
    if any(x in cmds for x in specials):                    # This appends the Read SysStatus command if any of the specials are being read from
        cmds.extend(['read', 'sysstatus'])                  # This is becuase the sign the of the reg's in specials are stored seperatly in SysStatus and must be recieved from there

    i = 0
    while i + 1 <= len(cmds):
        if cmds[i] in McpCommands.keys():
            result, replydata = get_args(cmds, cmds[i], i)
            cmd_frame.extend(result)
            readitems.extend([replydata])
            jump = McpCommands[cmds[i]][1] + 1
            i += jump

        else:
            raise ValueError('Either you entered too many parameters or and invalid command')

    Nbytes = len(cmd_frame) + 1
    cmd_frame[1] = Nbytes
    
    if len(cmd_frame) < 3:
        raise ValueError('No valid commands were detected')
    
    cmd_frame.extend(csum(cmd_frame))

    if len(cmd_frame) > 35:
        raise ValueError('the commands you have entered have exceeded the maximum frame size, please reduce the number of commands')
    return cmd_frame, readitems

def build_reponse(response, readitems, p):
    try:
        if response[0] == 0x06:

            if readitems and (len(response) > 1):
                readregs, Nbytes = readitems

                if csum(response[:-1])[0] == response[-1]:
                    # FormatedResponse = ''
                    index = 0
                    data = response[2:-1]
                    FormatedDict = {}

                    for i, reg in enumerate(readregs):
                        bytedata = data[index: index + Nbytes[i]]

                        try:                                                    # This determines if its page read data(aka reg = 'integer') or if its a typical reg.
                            int(reg)
                            value = tuple(bytedata[::-1])
                            # FormatedResponse += f'page {reg}: {value}'
                            FormatedDict[reg] = value
                        except ValueError:

                            value = int.from_bytes (bytedata, byteorder = 'little', signed = McpRegisters[reg][1])

                            if reg == 'amps' and bin(data[-1])[2:].zfill(8)[0]:
                                sign = bin(data[-1])[2:].zfill(8)[1]
                                if sign == '0':
                                    value = -value

                            elif reg == 'volts' and bin(data[-1])[2:].zfill(8)[0]:
                                sign = bin(data[-1])[2:].zfill(8)[2]
                                if sign == '0':
                                    value = -value

                            elif reg == 'power':
                                sign = bin(data[-2])[2:].zfill(8)[3]
                                if sign == '0':
                                    value = -value

                            elif reg == 'rctpower':
                                sign = bin(data[-2])[2:].zfill(8)[2]
                                if sign == '0':
                                    value = -value

                            result = McpRegisters[reg][3](value)                # dispatches int value to its corrisponding interpretering function, as each register value must be interpreted diffrently
                            # FormatedResponse += f'{reg}: {result} '
                            FormatedDict[reg] = result

                        index += Nbytes[i]

                    # return FormatedResponse
                    return FormatedDict

                else:
                    return 'Csum did not match, data invalid'

            elif readitems and (len(response) <= 1):
                return 'Command executed, but no reply data'

            else:
                return 'Acknowledged'

        elif response[0] == 0x15:
            return 'An NAK error was detected, and the command was not executed'

        elif response[0] == 0x51:
            return 'The checksum did not match and the command was not executed'
        else:
            raise ValueError

    except IndexError:
        return 'No Valid Response Byte was detected, its possible a timeout happended or there is not a valid conneciton'


def send_cmd(cmds, ports, attempts=1):                                          # pass list of cmds(each command is output of build_cmd), and list of ports respectivly for those commands
    responses = []                                                  # responses are returned in a list in the order the ports were provided

    for i, p in enumerate(ports):
        p.write(cmds[i][0])
    
    for i, p in enumerate(ports):                                   # reads input data, if the response byte is not valid, it flushes buffers and tries the command again. 
        n = 0                                                       # if it fails again, a None type will take the place of the dictionary.
        while n <= attempts:
            try:
                response = p.read(cmds[i][2])
                #print([b for b in response])
                r = build_reponse(response, cmds[i][1], p)
                #print(r)
                responses.append(r)
                break

            except ValueError:
                p.reset_input_buffer()
                p.reset_output_buffer()
                if n != attempts:
                    p.write(cmds[i][0])
                else:
                    responses.append(None)                          # adds a None type place holder if no data could be collected
                n += 1
            
    return responses

def build_cmd(commands):
    cmd_frame, readitems = get_cmd(commands.lower())
    data = bytearray(cmd_frame)
    transposed = [x for x in zip(*filter(None, readitems))]

    if transposed:
        NReadBytes = sum(transposed[1]) + 3                         # number of bytes to read: ack + NOB + data + csum. Data bytes = sum of register sizes in read commands. 
    else: 
        NReadBytes = 1

    return data, transposed, NReadBytes

def get_args(cmds, cmd, index): 
# the actual functions that produce hex data equivalent to sending a command vary enough that they each are there own
# function. They are stored in mcp39F_addresses and called by being dispatched from a command dictionary
# This function matches the command in the entered string to a real function, finds the arguments it is supposed to accept
# and then passes those pass arguments into the function and calls it.

    Ninputs = McpCommands[cmd][1]       
    args = []                      
    x = 1

    for n in range(Ninputs):
        args.append(cmds[index + x])    # gets the args from command string and stores them as list
        x += 1
    
    if args:
        result = McpCommands[cmd][2](args)
    else:
        result = McpCommands[cmd][2]()
    
    
    if cmd == 'read':                   # if the cmd is read, save the command register being read and the size of register in bytes(for reponse processing)
        replydata = [cmds[index + 1], McpRegisters[cmds[index + 1]][2]]
    elif cmd == 'pageread':             # if cmd is pageread, save page number and size of page(always 16 bytes)
        replydata = [cmds[index + 1], 16]
    else:
        replydata = []

    return result, replydata


def main():

    port1 = serial.Serial(baudrate=115200, port='COM22', timeout=0.5)
    while True:
        txt = input('commands: ')
        if txt == 'exit':
            break
        if txt == 'correction':
            test_correction([port1])
        else:
            try:
                print(send_cmd([build_cmd(txt)], [port1]))
            except ValueError as err:
                print(f'{err}')

def test_correction(ports):
    check_cmd = [build_cmd('read temp')]
    initials = send_cmd(check_cmd, ports)[0]
    recent_temp = initials['temp']
    correction_coefficient = .45 * 33.3   # (0.47 lsb / degree C) * (33.3 offcal bits / lsb)
    calibraton_temp = 25
    calibration_offcal = 30600

    while True:
        b = input('press enter to correct value, stop to return to regular commands')
        if b == 'stop':
            return
        a = send_cmd(check_cmd, ports)[0]
        current_temp = a['temp']
        print(current_temp)
        if (recent_temp - 1) < current_temp < (recent_temp + 1):
            recent_temp = current_temp
            new_offcal = round(calibration_offcal - (current_temp - calibraton_temp)*correction_coefficient)
            send_cmd([build_cmd(f'write offcal0 {new_offcal}')], ports)

if __name__ == '__main__' :
    main()
