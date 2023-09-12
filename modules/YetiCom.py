import json
import subprocess
import serial
import serial.tools.list_ports
import time

def capture(*args, port=None, inputs='', values=False, every=False, cmd='state'):
#captures desired data from a yeti where *args should be a list of endpoints names(str) you want. if values is true it only returns values(type=list) otherwise it returns as a dict.
#SysInfo being true pulls using the SysInfo mos command, but defualt is state command, inputs is a optional json string containing the values you wish to update
	if port:
		raw = subprocess.run(['mos','--port', f'{port}', 'call', f'{cmd}', f'{inputs}'], capture_output=True)

	else:
		raw = subprocess.run(['mos','call', f'{cmd}', f'{inputs}'], capture_output=True)	

	data = bytes.decode(raw.stdout, encoding='utf-8', errors='strict')
	try:
		jdata = json.loads(data)

	except:
		print('no data recieved')
		return

	if cmd != 'Sys.GetInfo':
		jdata = jdata['body']['state']

	if every:
		output = {key: [value] for key, value in jdata.items()}
	else:
		output = {item:[jdata[item]] for item in args}
		
	if values:
		return list(output.values())
	else:
		#print(output)
		return output

def test():
	lst=[]
	for i in range(10000000):
		lst.append(i*i)
	return

def main():
	timer = time.time()
	print(capture(port='COM8', every=True))

	print(time.time() - timer)
	

if __name__ == '__main__':
	main()
