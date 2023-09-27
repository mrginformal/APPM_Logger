import pandas as pd
import serial
import serial.tools.list_ports
import numpy as np
import tkinter as tk
import customtkinter as ctk
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle 
import sys
import math
import time
import multiprocessing as mp
import threading as th
from pathlib import Path
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from APPMControl import send_cmd, build_cmd

ctk.set_appearance_mode('Dark')
mplstyle.use('fast')

class Meter:             # holds basic info for each meter
    
    def __init__(self, hexstring=None, portobj=None, temp_correction=False):
        self.name = portobj.serial_number
        self.cmd = hexstring
        self.port = portobj
        self.temp_correction = temp_correction

########## Meter Class || runs in seperate process, job is to actually do all of the data polling from the meters, and package it up
class Meter_polling:        

    def __init__(self, Meters=None, frequency=30, sample_count=1, pipe=None):
        self.meters = Meters
        self.freq = frequency
        self.on = True
        self.name = 'meter_polling'
        self.sample_count = sample_count
        self.pipe = pipe
        self.meter_initial_offcal0_values = None
        self.calibration_temp = 23      #Celcius
        self.ports = [m.port for m in self.meters]

    def run(self):
        start = time.time() + 1
        adjusted_start = start
        interval = 1 / self.freq
        # this will produce no whole numbers, 10hz polling, 3hz update, 3.33 per update, 4 would actually happen before packet was sent off, meaning you actually have scan of 2.5hz, not 3 but good enough
        count = 0
        meters = self.meters
        ports = self.ports
        reset_energy_cmd = [build_cmd('write sysconfig b00000011_00000000_00000000_00000000')]	#makes hex commands for reseting and enabling energy accumulation
        enable_energy_cmd = [build_cmd('write sysconfig b00000011_00000000_00000000_00000001')]
        enable_energy_plus_tempcorrection = [build_cmd('write sysconfig b00000011_00000000_00000000_10000001')]
        get_temps_cmd = [build_cmd('read temp')]
        pageread_2_cmd = [build_cmd('pageread 2')]


        for p in ports:
            p.open()

        # resets and enables energy accumulation for all meters, and enable temp correction if selected
        send_cmd(reset_energy_cmd * len(ports), ports)					

        reset_energy_cmd_list = []
        temp_correction_enabled_meters = []

        for m in self.meters:
            if m.temp_correction:
                reset_energy_cmd_list += enable_energy_plus_tempcorrection
                temp_correction_enabled_meters.append(m)
            else:
                reset_energy_cmd_list += enable_energy_cmd

        send_cmd(reset_energy_cmd_list, ports)
        temp_correction_enabled_ports = [m.port for m in temp_correction_enabled_meters]

        # this section read page two of the eprom on temp_correction enabled meters, and then uses the values to get a ADC drift coefficient that was writen there during calibration. 
        # the first two bytes of page 2 are used, first byte is sign, and second byte represend the coefficient * 100. so a coefficient of -0.37 would be (1, 37)
        
        page_data = send_cmd(pageread_2_cmd * len(temp_correction_enabled_meters), temp_correction_enabled_ports)
        for i, m in enumerate(temp_correction_enabled_meters):
            data = page_data[i]['2'][0:2]
            if not data[0]:
                setattr(m, 'temp_coefficient', data[1] / 100)
            elif data[0] == 1:
                setattr(m, 'temp_coefficient', data[1] / -100)
            else:
                raise ValueError(f'No valid Temp Calibration for meter {m.name}')

        self.meter_initial_offcal0_values = send_cmd([build_cmd('read offcal0')] * len(self.meters), self.ports)
        
        hex_cmds = [m.cmd for m in meters]
        while self.on:
            # a dict that contains the data for each meter(each meters name is the key), then data is the value(another dic with values for each param)
            data = []					        

            while True:
                while (time.time() - adjusted_start) < (interval * count):
                    pass

                measurment = send_cmd(hex_cmds, ports)
                timestamp = time.time() - start
                for i, m in enumerate(measurment):
                    m['timestamp'] = timestamp
                    m['M_ID'] = meters[i].name

                data.append(measurment)
                count += 1
                if not count % (self.sample_count):
                    break
                
            if not count % (self.sample_count * 20):
                temps = send_cmd(get_temps_cmd*len(temp_correction_enabled_meters), temp_correction_enabled_ports)
                update_cmds = []
                for i, m in enumerate(temp_correction_enabled_meters):
                    # note, offcal0 is a twos complement register, meaning that if the new offcal value crosses the zero point it could break with this simple implementation                    
                    new_offcal = round(self.meter_initial_offcal0_values[i]['offcal0'] - (temps[i]['temp'] - self.calibration_temp) * m.temp_coefficient * 33.3)       # (temp_coefficient lsb/ degree C) * (33.3 offcal0 bits / lsb)
                    update_cmds += [build_cmd(f'write offcal0 {new_offcal}')]

                send_cmd(update_cmds, temp_correction_enabled_ports)

            formatted_data = [dict(zip(lst[0].keys(), zip(*(x.values() for x in lst))))	for lst in zip(*data)]

            self.pipe.send(formatted_data)

            # check if there is a packet in the pipe, if it does, it removes it vai recieve, and then using pipe.poll(None) to block indefinetly until another packet comes
            # this effective makes a toggle, where the first packet puases, and the second resumes, if either packet = 'stop' then it closes the thread
            if self.pipe.poll():                
                packet = self.pipe.recv() 
                if packet == 'STOP':
                    self.on = False
                    break

                packet2 = self.pipe.recv()
                if packet2 == 'STOP':
                    self.on = False
                    break
                else:
                    adjusted_start = start + packet2           #on resume, with will always be packet2, it will send the duration puased, so that the meters loop does not think its behind schedule

        print('closeing ports')
        for p in ports:
            p.close()

        # small timer before thread dies, to ensure pipes and other things in other threads close out correctly
        time.sleep(.1)                          
    
class APP(ctk.CTk):
    def __init__(self):
        super().__init__()

        ############## configure application window
        self.title('MAPPL Logger')
        scrn_w = self.winfo_screenwidth() - 100
        scrn_h = self.winfo_screenheight() - 100
        self.config(background='black')
        self.geometry(f'{scrn_w}x{scrn_h}+50+25')

        self.grid_rowconfigure(0, weight=0, minsize=scrn_h * .52)
        self.grid_rowconfigure(1, weight=3)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=6)
        self.grid_columnconfigure(2, weight=1)

        self.protocol("WM_DELETE_WINDOW", self._quit)
    
        ############## Application variables
        self.font1 = ctk.CTkFont(family='Arial Baltic', size=20, weight='bold')
        self.font2 = ctk.CTkFont(family='Arial Baltic', size=14, weight='bold')
    
        self.text_filename = ctk.StringVar(value='FilePath: ')
        self.is_valid_filename = False
        self.pause_button_state = False
        self.start_button_state = True

        self.start_time = 0
        self.start_datetime = ctk.StringVar(value='YYYY-MM-DD HH:MM:SS')
        self.formatted_end_time = ctk.StringVar(value='YYYY-MM-DD HH:MM:SS')
        self.remaining_time = ctk.StringVar(value='HH:MM:SS')
        self.duration_paused = 0
        self.paused_time = None

        self.measurment_parameters = ['Temp_Correction', 'Volts', 'Amps', 'Power', 'Probe Temperature', 'Reactive Power', 'Cumulative Imported Energy', 'Cumulative Exported Energy', 'Cumulative Imported Reactive Energy', 'Cumulative Exported Reactive Energy', 'Power Factor']
        self.string_map = { 'Volts': 'volts',                        
                            'Amps': 'amps',
                            'Power': 'power',
                            'Probe Temperature': 'temp',
                            'Reactive Power': 'rctpower',
                            'Cumulative Imported Energy': 'ienergy',
                            'Cumulative Exported Energy': 'eenergy',
                            'Cumulative Imported Reactive Energy': 'irctenergy',
                            'Cumulative Exported Reactive Energy': 'erctenergy',
                            'Power Factor': 'pf'}
        
        self.parameter_selections = {}
        self.measurment_freq = ctk.IntVar(value=30)
        self.test_duration_text = ctk.StringVar()

        self.comports = []
        self.meters = []

        self.graph_time_selection = ctk.StringVar(value='Previous Minute')
        self.graph_time_options = {'Previous Minute': 60,
                                   'Previous 5 Minutes': 300}
        
        
        ############## selections frame
        self.selection_frame = ctk.CTkScrollableFrame(self, corner_radius=5, bg_color='black', fg_color='grey18', orientation='horizontal')
        self.selection_frame.grid(row=0, column=1, padx=5, pady=(5,0), sticky='nsew')

        self.meter_label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text='Meter', fg_color='grey18', text_color='yellow2', font=self.font1, anchor='e')
        self.meter_label.grid(row=0, column=0, padx=5, pady=3, sticky='nsew')

        self.meter_label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text='All', fg_color='grey18', text_color='yellow2', font=self.font1, anchor='w')
        self.meter_label.grid(row=0, column=1, padx=5, pady=3, sticky='nsew')

        for i, label in enumerate(self.measurment_parameters):
            label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text=label, fg_color='grey18', text_color='yellow2', font=self.font2, anchor='e')
            label.grid(row=i+1, column=0, padx=(5,15), pady=3, sticky='nsew') 


        ############## Graph Frame
        self.graph_frame = ctk.CTkFrame(self, corner_radius=0, bg_color='black', fg_color='grey18')
        self.graph_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=(0,5), sticky='nsew')
        self.graph_frame.rowconfigure(0, weight=1)
        self.graph_frame.columnconfigure(0, weight=1)
         
        plt.style.use('dark_background') 

        fig1, ax1 = plt.subplots()
        plt.grid(color='.5')
        plt.subplots_adjust(left=.03, right=.83, top=.95, bottom=.08)
        self.fig1 = fig1
        self.ax1 = ax1
        self.ax1.spines[['top', 'bottom', 'left', 'right']].set_color('0.18')
        self.ax1.spines[['top', 'bottom', 'left', 'right']].set_linewidth(4)
        self.ax1.xaxis.label.set_color('.5')
        self.ax1.yaxis.label.set_color('.5')
        self.ax1.grid(False)

        self.ax1.tick_params(axis='both', width=3, colors='.5', which='both', size=10)

        self.canvas1 = FigureCanvasTkAgg(self.fig1, self.graph_frame)
        self.canvas1.get_tk_widget().grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        self.canvas1.draw()
        

        ############## Options Frame
        self.options_frame = ctk.CTkFrame(self, corner_radius=5, bg_color='black', fg_color='grey18')
        self.options_frame.grid(row=0, column=0, padx=5, pady=(5,0), sticky='nsew')
        self.options_frame.columnconfigure((0,1,2), weight=1)
        self.options_frame.rowconfigure((0,1,2,3,4,5,6,7), weight=1)
    

        self.scan_button = ctk.CTkButton(self.options_frame, corner_radius=5, text='Scan Meters', fg_color='yellow2',text_color_disabled='black', text_color='grey18', font=self.font1, command=self.scan_meters, hover_color='grey50')
        self.scan_button.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')

        self.start_button = ctk.CTkButton(self.options_frame, corner_radius=5, text='Start', fg_color='yellow2', text_color='grey18', font=self.font1, command=self.log_data, hover_color='grey50')
        self.start_button.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')
    
        self.pause_button = ctk.CTkButton(self.options_frame, corner_radius=5, text='Pause', fg_color='yellow2', text_color='grey18', font=self.font1, command=self.pause_logging, hover_color='grey50')
        self.pause_button.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')

        self.normalize_button = ctk.CTkButton(self.options_frame, corner_radius=5, text='Normalize', fg_color='grey50', text_color='grey18', font=self.font1, state='disabled', text_color_disabled='black', command=self.normalize_data, hover_color='grey50')
        self.normalize_button.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')

        self.save_as_button = ctk.CTkButton(self.options_frame, corner_radius=5, text='SaveAs', fg_color='yellow2', text_color='grey18', font=self.font1, text_color_disabled='black', command=self.get_filename, hover_color='grey50')
        self.save_as_button.grid(row=4, column=0, padx=5, pady=5, sticky='nsew')
        self.file_path_label = ctk.CTkLabel(self.options_frame, corner_radius=5, textvariable=self.text_filename, fg_color='black', text_color='yellow2', font=self.font2, width=200)
        self.file_path_label.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky='nsew')

        self.start_time_header = ctk.CTkLabel(self.options_frame, corner_radius=5, text='Start Time:', fg_color='grey18', text_color='yellow2', font=self.font2)
        self.start_time_header.grid(row=5, column=0, padx=5, pady=5, sticky='nsew')
        self.start_time_label = ctk.CTkLabel(self.options_frame, corner_radius=5, textvariable=self.start_datetime, fg_color='grey18', text_color='yellow2', font=self.font2)
        self.start_time_label.grid(row=6, column=0, padx=5, pady=5, sticky='nsew')

        self.estimated_completion_header = ctk.CTkLabel(self.options_frame, corner_radius=5, text='Estimated Finish:', fg_color='grey18', text_color='yellow2', font=self.font2)
        self.estimated_completion_header.grid(row=5, column=1, padx=5, pady=5, sticky='nsew')
        self.estimated_completion_label = ctk.CTkLabel(self.options_frame, textvariable=self.formatted_end_time, corner_radius=5, fg_color='grey18', text_color='yellow2', font=self.font2)
        self.estimated_completion_label.grid(row=6, column=1, padx=5, pady=5, sticky='nsew')

        self.time_remaining_header = ctk.CTkLabel(self.options_frame, corner_radius=5, text='Time Remaining:', fg_color='grey18', text_color='yellow2', font=self.font2)
        self.time_remaining_header.grid(row=5, column=2, padx=5, pady=5, sticky='nsew')   
        self.time_remaining_label = ctk.CTkLabel(self.options_frame, textvariable=self.remaining_time, corner_radius=5, fg_color='grey18', text_color='yellow2', font=self.font2)
        self.time_remaining_label.grid(row=6, column=2, padx=5, pady=5, sticky='nsew')   


        ############### Options Frame 2(right side)
        self.options2_frame = ctk.CTkFrame(self, corner_radius=5, bg_color='black', fg_color='grey18')
        self.options2_frame.grid(row=0, column=2, padx=5, pady=(5,0), sticky='nsew')
        self.options2_frame.columnconfigure(0, weight=1)


        self.duration_label = ctk.CTkLabel(self.options2_frame, corner_radius=5, text='Duration(s)', fg_color='grey18', text_color='yellow2', font=self.font1)
        self.duration_label.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

        self.duration_textbox = ctk.CTkEntry(self.options2_frame, corner_radius=5, textvariable=self.test_duration_text, font=self.font2, fg_color='black', text_color='yellow2')
        self.duration_textbox.grid(row=1, column=0, padx=20, pady=5, sticky='nsew')

        self.measurment_frequency = ctk.CTkLabel(self.options2_frame, corner_radius=5, text='Measurment Frequency(hz)', fg_color='grey18', text_color='yellow2', font=self.font1)
        self.measurment_frequency.grid(row=2, column=0, padx=5, pady=5, sticky='nsew')

        self.measurment_frequency = ctk.CTkLabel(self.options2_frame, corner_radius=5, textvariable=str(self.measurment_freq), fg_color='grey18', text_color='yellow2', font=self.font1, anchor='center')
        self.measurment_frequency.grid(row=3, column=0, padx=5, pady=5, sticky='nsew')

        self.freq_slider = ctk.CTkSlider(self.options2_frame, variable=self.measurment_freq, from_=1, to=60, number_of_steps=60, button_color='yellow2', progress_color='yellow2', button_hover_color='grey50')
        self.freq_slider.grid(row=4, column=0, padx=5, pady=5, sticky='nsew')

        self.graph_label = ctk.CTkLabel(self.options2_frame, corner_radius=5, text='Graph Time Span', fg_color='grey18', text_color='yellow2', font=self.font1)
        self.graph_label.grid(row=5, column=0, padx=5, pady=5, sticky='nsew')
        
        self.graph_time_menu = ctk.CTkOptionMenu(self.options2_frame, corner_radius=5, values=list(self.graph_time_options.keys()), variable=self.graph_time_selection, width=200, button_color='black', button_hover_color='grey50',font=self.font2, dropdown_font=self.font2, dropdown_fg_color='black', fg_color='black', text_color='yellow2', dropdown_text_color='grey50' )
        self.graph_time_menu.grid(row=6, column=0, padx=20, pady=5, sticky='nsew')

    def pause_logging(self):
        if self.pause_button_state:             # If the state is False, this means that it is not paused
            self.pause_button_state = False
            self.pause_button.configure(text='Pause')
            self.duration_paused += (time.time() - self.paused_time)
            self.pipe_conn2.send(self.duration_paused)

            if self.duration:
                self.end_time = self.start_time + float(self.duration) + self.duration_paused
                self.formatted_end_time.set(datetime.fromtimestamp(self.end_time).replace(microsecond=0))
            self.update_time_remaining()
        else:
            self.pause_button_state = True
            self.pause_button.configure(text='Resume')
            self.pipe_conn2.send('Toggle')
            self.paused_time = time.time()

    def update_time_remaining(self):
        if not self.pause_button_state:

            if hasattr(self, 'end_time'):
                time_remaining = self.end_time - time.time()
                total_minutes, seconds = divmod(round(time_remaining), 60)
                hours, minutes = divmod(total_minutes, 60)
                self.remaining_time.set(f"{hours:02}:{minutes:02}:{seconds:02}")
        
                if time_remaining > 0:
                    # Call the update function again after 1000ms (1 second)
                    self.after(1000, self.update_time_remaining)
                else:
                    self.remaining_time.set("00:00")

    def generate_cmd_string(self, meter):       # meter in this case comes from parameter_selection dictionaries, it is a dictrionary with paramter,button key,value pairs
        cmd_str = ''
        for parameter, button in meter.items():
            if parameter != 'Temp_Correction':
                if button.get():
                    cmd_str += f'read {self.string_map[parameter]} '
            else:
                if button.get():
                    temp_correction_enabled = True
                else:
                    temp_correction_enabled = False

        return cmd_str, temp_correction_enabled

    def save(self, header=True, mode='a'):
        if self.data_table is not None:
            self.data_table.sort_values('timestamp').to_csv(self.filename, mode=mode, header=header)
            print('saving')
        self.data_table = None                  # when ever a save to csv is done, it clears that data to ensure the memory doesn't fill up, this is an append based system

    def get_filename(self):
        filename = tk.filedialog.asksaveasfilename(defaultextension='.csv', title='Save output data as: ', filetypes = [('CSV files', '*csv')])
        self.filename = Path(filename)
        if self.filename.exists():
            self.filename.unlink()      # deletes any previous file with this name, they are asked if they want to overwrite by the tkinter save as window

        self.text_filename.set(filename[-35:])
        self.is_valid_filename = True

    def log_data(self):
        if self.start_button_state:             # toggle the button to running, second press will stop the test, and stop the logging, save the data

            try:
                self.meters = []
                
                for meter, item in self.parameter_selections.items():
                    text_cmd, temp_correction_enabled = self.generate_cmd_string(item)
                    if text_cmd:
                        hex_cmd = build_cmd(text_cmd)
                        for p in self.comports:
                            if p.serial_number == meter:
                                port = p
                        self.meters.append(Meter(hexstring=hex_cmd, portobj=port, temp_correction=temp_correction_enabled))

                if not self.meters:
                    raise ValueError('No meters or commands detected')

                if not self.is_valid_filename:
                    raise ValueError('No valid Filename selected')
                
                # this effectively sets the update frequency to always have approximately 200 updates before the graph has fully moved across the screen based on graph time span
                freq = self.measurment_freq.get()
                updates_per_window = 300
                sample_count = math.ceil((self.graph_time_options[self.graph_time_selection.get()] / updates_per_window) * freq) # the number cannot be below 1, so it gets rounded up

                # Disable input buttons so they can't mess with anything, and color them so its clear they are disabled.
                self.duration_textbox.configure(state='disabled')
                self.freq_slider.configure(state='disabled')
                self.graph_time_menu.configure(state='disabled')
                self.scan_button.configure(state='disabled', fg_color='grey50')
                self.normalize_button.configure(state='normal', fg_color='yellow2')
                self.save_as_button.configure(state='disabled', fg_color='grey50')

                # clear parameter seletions so they can be used for data visualization selection, and disable all selections
                for button in self.all_checkboxes:
                    button.deselect()
                    button.configure(state='disable', border_color='grey18')
                
                for meter, params in self.parameter_selections.items():
                    for param, button in params.items():       
                        if not button.get():
                            button.deselect()
                            button.configure(state='disabled', border_color='grey18')
                            
                        else:
                            if param == 'Temp_Correction':
                                button.configure(state='disabled')
                            else:
                                button.configure(state='normal', fg_color='black')  # all of the buttons that are suposed to be enabled, we make sure they are, becuase the select all function can change them
                                button.select()

                ########### MultiThreading and Multiprocessing initialization
                conn1, conn2 = mp.Pipe(duplex=True)
                self.pipe_conn2 = conn2
                self.lock = th.Lock()
                self.stop_flag = th.Event()
                self.data_updated_flag = th.Event()
                self.data_table = None
                self.graph_table = None


                M_polling = Meter_polling(Meters=self.meters, frequency=freq, sample_count=sample_count, pipe=conn1)

                data_thread = th.Thread(target=self.collect_data, daemon=True)
                meter_process = mp.Process(target=M_polling.run, daemon=True)
                plotting_thread = th.Thread(target=self.plot_data, daemon=True)

                data_thread.start()
                meter_process.start()
                plotting_thread.start()

                self.start_button_state = False
                self.start_button.configure(text='Stop')

            except Exception as err:
                message_box = tk.Toplevel(self)
                message_box.configure(background='grey50')
                message_box.title('Error Message')
                message_box.geometry(f'300x150+{(int(self.winfo_screenwidth()/2) - 150)}+{(int(self.winfo_screenheight()/2) - 75)}')
                textbox = ctk.CTkTextbox(message_box, corner_radius=5, text_color='black', bg_color='grey50', fg_color='grey50', wrap='word')
                textbox.insert("0.0", err)
                textbox.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

        else:
            self.pipe_conn2.send('STOP')
            self.stop_flag.set()

            if self.filename.is_file():
                self.save(header=False)
            else:
                self.save()

            self.complete_message()


    def complete_message(self):
        exit_box = tk.Toplevel(self)
        exit_box.rowconfigure(0, weight=1)
        exit_box.columnconfigure(0, weight=1)
        exit_box.configure(background='grey50')
        exit_box.title('Complete!')
        exit_box.geometry(f'300x150+{(int(self.winfo_screenwidth()/2))}+{(int(self.winfo_screenheight()/2))}')
        exit_text_box = ctk.CTkLabel(exit_box, corner_radius=5,text_color='black', font=self.font1, bg_color='grey50', text='Your test is complete!', anchor='center')
        exit_text_box.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

        exit_box.protocol("WM_DELETE_WINDOW", self._quit)

    def collect_data(self):                     # becuase the pipe is not able to hold a large amount of data, i need to have a dedicated function that is continually emptying the pipe, and adding it to the data set
        pipe = self.pipe_conn2
        timer = time.time()                     # timer for autosave
        self.start_time = time.time()
        dtime = datetime.now().replace(microsecond=0)
        self.start_datetime.set(dtime)
        elapsed_time = 0

        try:
            self.duration = float(self.test_duration_text.get())
            self.formatted_end_time.set(datetime.fromtimestamp(self.start_time + self.duration).replace(microsecond=0))
            self.end_time = self.start_time + self.duration
        except:
            self.duration = 0
            self.formatted_end_time.set('N/A')

        self.update_time_remaining()
        graph_table_length = self.measurment_freq.get() * self.graph_time_options[self.graph_time_selection.get()] * len(self.meters)

        while True:
            data = [pd.DataFrame(m) for m in pipe.recv()]
            with self.lock:                 # aquire a lock before updating main data set
                self.data_table = pd.concat([self.data_table] + data, copy=False, ignore_index=True)
                self.graph_table = pd.concat([self.graph_table] + data, copy=False, ignore_index=True).sort_values('timestamp').tail(graph_table_length)

            self.data_updated_flag.set()

            if time.time() - timer > 120:   # approximately every 120 seconds, save
                timer = time.time()
                if self.filename.is_file():
                    self.save(header=False)
                else:
                    self.save()

            if self.stop_flag.is_set():
                break

            if self.duration != 0:
                if time.time() > self.end_time:
                    self.pipe_conn2.send('STOP')

                    if self.filename.is_file():
                        self.save(header=False)
                    else:
                        self.save()
                    
                    self.complete_message()
                    break
  
    def scan_meters(self):

        ports = serial.tools.list_ports.comports()
        comports = []
        
        for p in ports:
            if p.serial_number and p.serial_number[:3] == '_M_':
                with serial.Serial(baudrate=115200, port=p.device) as port:
                    setattr(port, 'serial_number', p.serial_number)
                    comports.append(port)

        self.comports = sorted(comports, key=lambda comport: comport.serial_number)

        for widget in self.selection_frame.winfo_children():              #all existing buttons need to be deleted before making the new ones, but we only want to delete the buttons
            col_num = widget.grid_info()['column']
            if col_num not in (0,1):
                if isinstance(widget, (ctk.CTkCheckBox, ctk.CTkLabel)):
                    widget.destroy()

        self.meter_label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text='Meter', fg_color='grey18', text_color='yellow2', font=self.font1, anchor='center')
        self.meter_label.grid(row=0, column=0, padx=5, pady=3, sticky='nsew')

        self.meter_label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text='All', fg_color='grey18', text_color='yellow2', font=self.font1, anchor='w')
        self.meter_label.grid(row=0, column=1, padx=5, pady=3, sticky='nsew')

        self.all_checkboxes = []

        for i, label in enumerate(self.measurment_parameters):
            check_box = ctk.CTkCheckBox(self.selection_frame, text=None, border_width=3, corner_radius=10, command=lambda i=i: self.all_parameter_select(i), hover_color='grey50', checkbox_width=50, border_color='black', fg_color='black')
            check_box.grid(row=i+1, column=1, padx=5, pady=3, sticky='nse')
            self.all_checkboxes.append(check_box)

            label = ctk.CTkLabel(self.selection_frame, corner_radius=0, text=label, fg_color='grey18', text_color='yellow2', font=self.font2, anchor='center')
            label.grid(row=i+1, column=0, padx=(5,15), pady=3, sticky='nsew') 

        for col, m in enumerate(comports):
            ctk.CTkLabel(self.selection_frame, corner_radius=5, text=m.serial_number[4:], fg_color='grey18', text_color='yellow2', font=self.font1, anchor='w').grid(row=0, column=col+2, padx=5, pady=5, sticky='nsew')
            self.parameter_selections[m.serial_number] = {key: ctk.CTkCheckBox(self.selection_frame, text=None, corner_radius=10, checkbox_width=50, hover_color='grey50', border_color='black', fg_color='black', border_width=3) for key in self.measurment_parameters}
            for row, (_, button) in enumerate(self.parameter_selections[m.serial_number].items()):
                button.grid(row=row+1, column=col+2, padx=5, pady=3, sticky='nse')

    def all_parameter_select(self, row):
        if self.all_checkboxes[row].get():
            for meter in self.parameter_selections.values():
                for i, button in enumerate(meter.values()):
                    if i == row:
                        button.select()
                        button.configure(fg_color='grey50')
                        button.configure(state='disabled')
        else:
            for meter in self.parameter_selections.values():
                for i, button in enumerate(meter.values()):
                    if i == row:
                        button.deselect()
                        button.configure(fg_color='black')
                        button.configure(state='normal')


    def plot_data(self):
        self.lines = {}
        active_buttons = {}     # a subset of all buttons, only contains active buttons for simplicity later
        for meter, params in self.parameter_selections.items():
            self.lines[meter] = {}
            for param, button in params.items():
                if param != 'Temp_Correction':
                    if button.cget('state') == 'normal':
                        if meter in active_buttons:
                            active_buttons[meter][param] = button
                        else:
                            active_buttons[meter] = {param: button}

                        line, = self.ax1.plot([],[])
                        self.lines[meter][param] = line

        while True:
            timer = time.time()
            if self.stop_flag.is_set():
                break
            
            self.data_updated_flag.wait()
            self.data_updated_flag.clear()
            self.update_graph(active_buttons)

    def update_graph(self, active_buttons):
        with self.lock:
            if not self.graph_table.empty:
                x_data = np.array([])
                y_min = None
                y_max = None
                for meter, params in active_buttons.items():
                    if x_data.size == 0:              # this gets the timestamp data for 1 meter, but since its the same for all meters, there is no need to repeat it for each meter
                        x_data = self.graph_table[self.graph_table['M_ID'] == meter]['timestamp'].values
                        x_min = x_data[0]
                        x_max = x_data[-1]

                    for param, button in params.items():
                        line = self.lines[meter][param]
                        if button.get():
                            line.set_visible(True)
                            y_data = self.graph_table[self.graph_table['M_ID'] == meter][self.string_map[param]].values
                            line.set_data(x_data, y_data)
                            last_datapoint = round(y_data[-1],3)
                            line.set_label(f'{param}:{meter} \n{last_datapoint}')
                            # This section sets the x and y limits for viewing the graph based on only visible/selected parameters
                            if y_min:
                                if min(y_data) < y_min:
                                    y_min = min(y_data)
                            else:
                                y_min = min(y_data)

                            if y_max:
                                if max(y_data) > y_max:
                                    y_max = max(y_data)
                            else: 
                                y_max = max(y_data)
                        else:
                            line.set_visible(False)  

                if not y_max == None and not y_min == None:
                    self.ax1.set_xlim(x_min - 1, x_max + 1)
                    self.ax1.set_ylim((y_min) -  .05 * np.abs(y_min) - .1 , (y_max) + .05 * np.abs(y_max) + .1)

                self.ax1.legend(loc='upper left', bbox_to_anchor=(1, .5 + .025*(len(self.ax1.get_lines()))), labelcolor='linecolor') # puts the legend to the side, and ajusts the verticle based on number of lines

                self.canvas1.draw_idle()

    def normalize_data(self):
        pass

    def _quit(self):
        self.destroy()
        sys.exit()

        
if __name__ == '__main__':
    mp.freeze_support()
    app = APP()
    app.mainloop()