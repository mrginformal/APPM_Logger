# Test-Automation-Integrated_Test_Software
 Contains integrated test setup software/scripts and documents

## How to install(if executable doesn't work):
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

### Setup
First connect all the necessary cabling for your test. Ensure each MAPPL has the necessary connections for the test. L(for load) and S(for supply)
on the top of the bolts define the direction of positive dc volts and current. Ensure each APPM is connected via USB and the red power LED is illuminated.

## Running the Program
With the install complete and the cabling connected you are now ready to launch the program. You can launch it however you wish either via python3 in the
terminal, by right clicking on it and using "Open With Python", through an IDE or some other means.

**TIPS**: 
 * Use Scan Meters to find connected meters, then use the buttons to select which parameters you wish to have each of those meters
 * Use the "Save" button to give the filename you wish to have the data logged as, it will be exported as a csv. There is no need to include the file extension in the name. The complete file name and
 location will be displayed just to the right of the Save button in a text box once a selection is made.
 * You may enter a maximum test duration on the top right corner, however if you do not wish to have a maximum duration, simply leave it blank and it will run until the stop button is pressed
 * After a test has begun, and the data is graphing, you may use the buttons underneath each mater to togle the visibility of the graph to make for less busy viewing
 * data is saved automatically every 2 minutes so if you accidentily close the program, not all is lost
 * You may pause the test using the puase and resume button, doing so will pause the graph and the data logging, in your data there will be a gap of time where no datapoints were taken, reflecting the puase
 * Pressing stop will end the test, save the data and exit the program
 * You may toggle grid lines in the graph by clicking once into the graph, then using the "G" key to toggle grid lines
 * The most recent datapoint value in the graph is added to the legend for convienience
 * Temp_Correction is use to make the meters more accurate in their current and power measurments by adjusting values based on the onboard thermometer. In order for this to be effective, you must have the onboard
 thermeter actually connected(the 3 wire comming out of the top). This means you cannot log external temps and have temp-correction at the same time. However the meter is still quite accurate without correction

 Meter accuracy and ranges specs(MAPPL 4.0 mini)(these value should be accurate for both AC and DC measurments and are relatively conservative)

 With Temp Correction

 V: (0-400V) +- 0.02V
 A: (0-60A) +- 0.1% + 0.005 A
 P: (0-24000W) +- 0.15% + .3W
Temp: N/A

Without Temp Correction
V: (0-400V) +- 0.02V
A: (0-60A) +- 0.2% + 0.01A
P: (0-24000) +- 0.3% + .5W
Temp: (-40C - 125C) +- 1.5C