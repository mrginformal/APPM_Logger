# Test-Automation-Integrated_Test_Software
 Contains integrated test setup software/scripts and documents

## How to install:
1. Download this GitHub repo as a zip and all of its contents to your local computer(only works on Linux and windows based systems for now)
2. Ensure the latest version of python3 is installed on your machine.       https://www.python.org/downloads/
Note: don't forget to add python to PATH during the installation process (there will be a little check box at the bottom of the install window at one point).
3. Navigate to the Silabs website and ensure that latest Silabs CP210x USB to UART driver is installed.     https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads 
I have had better luck not using the universal and instead using the VCP driver.
4. Install pip.   https://www.geeksforgeeks.org/how-to-install-pip-on-windows/
5. Use pip to run the following command:

```
 pip install -r /path/to/requirments.txt
```

**Note: The actual path to requirments.txt on your machine must be used.**

**You are now ready to run the program without yeti's connected.** If you wish to be able to communicate with yeti's you must also install the MOS cli tool 
from mongoose OS (currently only verified to work with Linux). There is a tutorial on how to do this on the official mongoose GitHub page for windows, Linux 
and mac. To install on an ARM based Linux platform like a raspberry pi you need to follow the 'INSTALLING MOS ON PI GUIDE' word doc provided in this repo.

With MOS installed you should be able to fully take advantage of the program

### Setup
First connect all the necessary cabling for your test. Ensure each APPM (if any) has the necessary connections for the test. L(for load) and S(for supply)
on the top of the bolts define the direction of positive dc volts and current. Ensure each APPM is connected via USB and the red power LED is illuminated.

If connecting yeti's, one must remove the lid or access by other means the 6 pin UART pins connected to the Wi-Fi module (esp32 chip). While the location of
these pins may vary, they are usually near the silver esp32 chip (for most x line products they stick off the back of the faceplate PCB just above the lcd).
Connect a premade and verified USB to UART adapter(see matt if you need one) to the 6 pin header with the black wire connected to the GND pin. These adapters
are special in that the DTR pin is not connected and that they are serialized such that they are automatically recognized by the program as yeti communication
channels.

## Running the Program
With the install complete and the cabling connected you are now ready to launch the program. You can launch it however you wish either via python3 in the
terminal, and IDE or some other means. The program operates through a command line interface(CLI).

A very easy way to run this program is to navigate to the folder that contains MainControl.py, click on the address bar so that the path is highlighted and 
type 'cmd' and hit enter. then type 'python MainControl.py' into the terminal window and the program should launch. 

Once you run the Program, you will setup the test by going through the following steps:

1. Enter filename: Enter the name you wish to save the file as. There is no need to include the file extension.

2. If the file already exists you will be asked if you want to overwrite it.

3. It will then attempt to establish connections to all connected devices. Once its complete, it will list all the detected meters and detected yetis by
serial # and mac address, respectively. 

4. Associate meters to yetis: This information is used to later correlate yeti and meter data in post processing (helps you remember which
meters were reading data from each yeti, so you do not have to record it manually for later). Simply type the meter's serial number and press enter to link them,
multiple meters can be entered, serial numbers, leading 0's are also not necessary. It is also not necessary to assign every yeti a meter or every meter a yeti.
Any unassigned meters will be added to a group named independents

5. Once all associations are made, they will be printed and you will be asked if they are correct, if you select no, you will be asked if you wish to exit or try again.

6. For each meter you will be asked to enter the commands they should read. Below is a list of the options available as well as some examples of the format of each command

- volts         *(ac/dc)
- amps          *(ac/dc)
- power         *(ac/dc)
- rctpower      *(ac)reactive power
- linefreq      *(ac/dc)frequency of voltage line
- thermistor    *(ac/dc)temperature reported by thermistor in Celsius
- pf            *(ac/dc)power factor
- ienergy       *(ac/dc) cumulative imported active energy | energy moved from S(supply) to L(load)
- eenergy       *(ac/dc) cumulative exported active energy | energy moved from L(load) to S(supply)
- irctenergy    *(ac)cumulative imported reactive energy
- erctenergy    *(ac)cumulative exported reactive energy

**Examples**
Ex. 
To read from volts simply type "read volts". or to read cumulative imported energy type "read ienergy".

If you wish to log multiple parameters at the same time, simply chain the commands together. Note: nothing is cap sensitive
Ex.
To read volts, amps, power, temperature and ienergy type: "read volts read amps read power read thermistor read ienergy". Notice read must be typed before each parameter.

This must be completed for all connected meters. 

7. Enter the test duration (in seconds) as whole number. Note: you can always end the test prematurely by entering 'stop' into the terminal.

8. Enter the frequency of data polling. Note: all meters will poll at the same rate, this also only affects meters, yeti data is automatically polled every 2 seconds. 
Value must be below between 1 and 60.

9. Press enter to begin the test. Note: at any time, you can enter stop and the test will end, saving the data you have acquired.

Data is saved in the Output Files folder. the data will be saved as the name you entered in step 1, with a prefix Mdata_ for the recorded meter data and Ydata_ for the recorded yeti data.
