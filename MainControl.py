import serial
import serial.tools.list_ports
import sys
import threading as th
import pandas as pd
import time
from pathvalidate import sanitize_filename
from pathlib import Path
import queue
sys.path.append('modules')

from APPMControl import send_cmd, build_cmd
from YetiCom import capture

# Integration code for use with meters, and yetis, no multiplexor in this version.
# Version: 0.0.9

class Meter:
	
	def __init__(self, hexstring=None, portobj=None):
		self.name = portobj.serial_number
		self.cmd = hexstring
		self.port = portobj

# ----------------------------- Classes for threading ----------------------------------------------
class Meter_polling:

	def __init__(self, Meters=None, time=None, frequency=30, worker_in_q=None, worker_out_q=None):
		self.meters = Meters
		self.time = time
		self.freq = frequency
		self.worker_out_q = worker_out_q
		self.worker_in_q = worker_in_q
		self.on = True
		self.chunksize = 2									# chunksize is rate at which the yeti's are polling, usually ever 2 seconds
		self.start_time = time
		self.name = 'meter_polling'

	def run(self):
		start = self.start_time
		interval = 1 / self.freq
		counts_per_sample = self.chunksize * self.freq		#samples before sending datapacket
		count = 0
		meters = self.meters
		ports = [m.port for m in meters]
		reset_energy_cmd = [build_cmd('write sysconfig b00000011_00000000_00000000_00000000')]	#makes hex commands for reseting and enabling energy accumulation
		enable_energy_cmd = [build_cmd('write sysconfig b00000011_00000000_00000000_00000001')]

		send_cmd(reset_energy_cmd * len(ports), ports)					# resets and enables energy accumulation for all meters
		send_cmd(enable_energy_cmd * len(ports), ports)

		while self.on:
			data = []					# a dict that contains the data for each meter(each meters name is the key), then data is the value(another dic with values for each param)

			hex_cmds = [m.cmd for m in meters]

			while True:
				while (time.time() - start) < (interval * count):
					pass

				measurment = send_cmd(hex_cmds, ports)
				timestamp = time.time() - start
				for i, m in enumerate(measurment):
					m['timestamp'] = timestamp
					m['M_ID'] = meters[i].name

				data.append(measurment)
				count += 1
				if not count % (counts_per_sample):
					break

			formatted_data = [dict(zip(lst[0].keys(), zip(*(x.values() for x in lst))))	for lst in zip(*data)]		#single most rediculous line of code i've ever written(preps data for pandas dataframe)
			self.worker_out_q.put([self.name, formatted_data])

			try:
				if self.worker_in_q.queue[0][0] == self.name:		#makes updates if any found
					packet = self.worker_in_q.get()
					self.update(packet)

			except IndexError:
				pass

		return

	def update(self, packet):  # the goal of this function will be to update the attributes, which control the run loop
		for key in packet:
			setattr(self,key,packet[key])

	
class Yeti:
	
	def __init__(self,inputstring='', values=['v12PortStatus', 'usbPortStatus', 'acPortStatus', 'socPercent', 'wattsOut'],time=None, worker_in_q=None, worker_out_q=None, portobj=None):
		self.name = portobj.mac
		self.worker_in_q = worker_in_q
		self.worker_out_q = worker_out_q
		self.port = portobj
		self.on = True
		self.inputstring = inputstring
		self.values = values
		self.start_time = time
		
	def run(self): 
		start = self.start_time
		count = 0
		polling_interval = 2 #should always match chunk size(though this could be adjusted later by changing the organizer to not wait for a packer from every worker)
		
		while self.on:
			
			while (time.time() - start) < (count * polling_interval):	#holds until its time to get another data point
				pass
			
			data = [self.name,]
			data.append(capture(self.port.device, *self.values, inputs=self.inputstring))
			data[1]['Y_ID'] = self.name

			if self.inputstring:			# if there was an input string it should have been sent, this resets it 
				self.inputstring = ''
				
			else:							# if no inputstring, send out data(aka dont return data on input strings)
				self.worker_out_q.put(data)
			
			try:
				if self.worker_in_q.queue[0][0] == self.name:	# ***** not really implemented, each worker should have its own queue for proper polling, otherwise can only send one update each cycle reliably
					packet = self.worker_in_q.get()
					self.update(packet)
			except IndexError:
				pass
			
			count += 1
								
	def update(self, packet):  # the goal of this function will be to update the attributes, which control the run loop
		for key in packet:
			setattr(self,key,packet[key])


class Organizer:
	
	def __init__(self, filename='latest_test.csv',input_q=None, worker_out_q=None, worker_in_q=None, connections=None, duration=60):
		self.filename = filename
		self.worker_out_q = worker_out_q
		self.worker_in_q = worker_in_q
		self.input_q = input_q
		self.on = True
		self.connections = connections
		self.workers = len(self.connections) 	# number of threads(1 for each yeti + 1 for meter_polling)
		self.duration = duration
		self.Mtable = None
		self.Ytable = None

	def save(self, header=True):
		if self.Mtable is not None:
			self.Mtable.sort_values('timestamp').to_csv(Path(f'Output_Files/Mdata_{self.filename}'), mode='a', header=header)
		if self.Ytable is not None:
			self.Ytable.sort_values('cycle').to_csv(Path(f'Output_Files/Ydata_{self.filename}'), mode='a', header=header)

	def run(self):
		updates = {}
		cycle = 1
		while self.on and cycle <= self.duration / 2:
			Mdata = []
			Ydata = []

			while len(Mdata) + len(Ydata) < self.workers:
				data = self.worker_out_q.get()
				if data[0] == 'meter_polling':		#is meter data
					for meter in data[1]:
						meter['cycle'] = (cycle,)*len(list(meter.values())[0])
						Mdata.append(meter)
				else:								#is yeti data
					data[1]['cycle'] = (cycle)
					Ydata.append(data[1])

			if updates:                             #if any updates sends them out 
				for device, update in updates.items():
					self.worker_in_q.put([device, update])
			
			# ------------------------- LOGIC -------------------------------------------------
			while not self.input_q.empty():
				u = self.input_q.get()
				if u[0] == 'organizer':
					self.update(u[1])
				else:
					updates[u[0]] = u[1]

			# ------------------------- data structure and file saving ------------------------

			if Mdata:
				self.Mtable = pd.concat([pd.DataFrame.from_dict(m) for m in Mdata] + [self.Mtable], copy=False, ignore_index=True)
			if Ydata:
				self.Ytable = pd.concat([pd.DataFrame.from_dict(y) for y in Ydata] + [self.Ytable], copy=False, ignore_index=True)

			if cycle == 150:			
				self.save()
				self.Mtable = None
				self.Ytable = None

			elif not cycle % 150:
				self.save(header=False)
				self.Mtable = None
				self.Ytable = None
		

			print(f'\nTime Elapsed: {(cycle * 2) // 60}m {(cycle * 2 % 60)}s')
			cycle += 1

		if cycle < 150:
			self.save()
		else:
			self.save(header=False)

	def update(self, packet):  # the goal of this function will be to update the attributes, which control the run loop
		for key in packet:
			setattr(self,key,packet[key])

class Independent:
	def __init__(self):
		self.mac = 'independent'    

# -------------------------------- Ports and COM Setup ---------------------------------------------
def associate():
	state = True
	while state:
		
		ports = serial.tools.list_ports.comports()
		meters = []
		yetis = []
		connections = {}                # in hindsight it was probably simpler to leave them as just a list of devices, and do ascociation in post. what ever :\
		
		print('Initializing COMPORTS...')
		
		for p in ports:                             #Uses the custom set serial numbers to delinate meters from other(assumed yetis) open comports,
													#It then adds the the device to the meters list filled with port objects
			if p.serial_number and p.serial_number[:3] == '_M_':
				port = serial.Serial(baudrate=115200, port=p.device)
				setattr(port, 'serial_number', p.serial_number)
				meters.append(port)
		
			elif p.serial_number and p.serial_number[:3] == '_Y_':      #Ascociates MAC Adress to each Comport Connected Yeti by adding it to port object, then adds the port object to yetis list
				try:
					setattr(p, 'mac', capture(p.device, 'mac', cmd='Sys.GetInfo')['mac'])
					yetis.append(p)
				except Exception:
					pass

		print('DONE!')
		
		if meters:
			print('Detected Meters:') 
			for m in meters:
				print(f'{m.serial_number} :: {m.port}')
				
		else:
			print('No Meters Detected')
		
		if yetis:
			print('\nDetected Yetis:')
			for y in yetis:
				print(f'{y.mac}')
			print('\n')
		else:
			print('No Yetis Detected')

		dmeters = [int(meter.serial_number[-5:]) for meter in meters]
		
		for yeti in yetis:
			raw = input(f'Type which meters you would like ascociate with {yeti.mac} using comma seperated numbers:\n')
			if raw == '':
				connections[yeti] = []
				continue
				
			try:
				mnums = list(map(int,raw.split(',')))
				for num in mnums:
					try:
						i = dmeters.index(num)
						if yeti in connections.keys():
							connections[yeti].append(meters[i])         #when something is added to the dict, its removed from the meters and dmeters lists.
							del meters[i]
							del dmeters[i]
						else:
							connections[yeti] = [meters[i]]
							del meters[i]
							del dmeters[i]

					except ValueError:
						print(f'meter {num} not detected')
						
			except ValueError:
					print(f'{raw} is not a comma seperated list of numbers')
			
		connections[Independent()] = meters                             #every meter that was not ascociated to a yeti, gets placed in a new catagory called independent(which is a object with .mac)

		if connections: 
			print('The following assosiations were made:\n')
			
			for connection in connections:
				print(f'{connection.mac} --> {[i.serial_number for i in connections[connection]]}')
			value = input('Continue with listed connections? (y/n): ')
		else:
			value = 'n'
			
		if value == 'y':
			state = False
		
		else:
			value = input('try again? (y/n) Note: n will exit program: ')
			if value == 'n':
				exit()
			else:                                                       #closes ports if you need to try again to avoid errors
				for yeti in connections:
					for meter in connections[yeti]:
						meter.close()
			
	return connections

def workercmds(connections):
	cmds = {}
	
	for yeti in connections:                        #only making commands for meters, yetis can easily be added here though
		for meter in connections[yeti]:
			while True:
				try:
					cmdstring = input(f'Please input the command string for {meter.serial_number}: ')
					hexstring = build_cmd(cmdstring)
					break
				except ValueError as err:
					print(err, ' try again')

			cmds[meter.serial_number] = hexstring

	return cmds

def interupt(input_q):
	while True:
		if input('type stop to close: '):
			input_q.put(['organizer', {'on': False}])
			break
# -------------------------------------- Main -----------------------------------------------------------------

def main():
	
# ------------------------------------- filenaming ---------------------------------------------------------
	while True:
		name = sanitize_filename(input('enter filename for data: '))
		name += '.csv'
		Mformated = Path('Output_Files/Mdata_' + name)
		Yformated = Path('Output_Files/Ydata_' + name)

		if Mformated.exists() or Yformated.exists():               #checks if the filename will lead to overwrite(if either dataframe file already exists)
			value = input('The file already exists, would you like to overwrite it? (y/n): ')
			if value == 'y':
				filename = name
				Mformated.unlink(missing_ok=True)
				Yformated.unlink(missing_ok=True)
				break
		else:
			filename = name
			break

# ----------------------------------- Initialization of thread objects, queues and threads themselves -------------------------------------------------------------
	connections = associate()               # get user inputs
	cmds = workercmds(connections)
	while True:
		try:
			test_duration =  int(input('enter test duration in seconds as integer: '))
			if test_duration % 2 != 0:		# becuase the meter thread must report to organizer at the same rate as yeti threads, data is only exchanged every 2 seconds.
				test_duration += 1			# if the duration is odd, the last second of data gets cut off, this extends the duration 1 second to get the last bit of data
			measurment_freq = int(input('enter measurment frequency as integer: '))
			value = input('press enter to start test ')
			break                       
		except ValueError:
			print('not a valid entry')
		
	worker_in_q = queue.Queue()             # make queues
	worker_out_q = queue.Queue()    
	input_q = queue.Queue()

											# make objects for threading
	O1 = Organizer(filename, input_q=input_q, worker_out_q=worker_out_q, worker_in_q=worker_in_q, connections=connections, duration=test_duration)

	workers = []
	meters = []
	startup_time = time.time()

	for yeti in connections:				#add each yeti object to worker to be threaded
		if yeti.mac != 'independent':
			workers.append(Yeti(worker_in_q=worker_in_q, time=startup_time, worker_out_q=worker_out_q, portobj=yeti))

		for meter in connections[yeti]:		#collect meters for meter_polling object
			meters.append(Meter(hexstring=cmds[meter.serial_number], portobj=meter))

	M1 = Meter_polling(Meters=meters, time=startup_time, frequency=measurment_freq, worker_in_q=worker_in_q, worker_out_q=worker_out_q)	#make meter_polling object and add to workers
	workers.append(M1)

	O1_thread = th.Thread(target=O1.run, daemon=True)
	worker_threads = [th.Thread(target=worker.run, daemon=True) for worker in workers]

	O1_thread.start()
	for w in worker_threads:
		w.start()
	
	I_thread = th.Thread(target=interupt, args=[input_q], daemon=True)
	I_thread.start()

	O1_thread.join()

	print('COMPLETE')

if __name__ == '__main__':
	main()
