import pandas as pd
import serial
import serial.tools.list_ports
import numpy as np
import tkinter as tk
import customtkinter as ctk
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle 
import matplotlib.gridspec as gridspec
import sys
import time

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)

sys.path.append('modules')
from APPMControl import send_cmd, build_cmd

ctk.set_appearance_mode('Dark')
mplstyle.use('fast')

def _quit(app):
    app.destroy()
    exit()


class Meter_polling:

    def __init__(self, Meters=None, frequency=30, up_freq=1):
        self.meters = Meters
        self.freq = frequency
        self.up_freq = up_freq
        self.on = True
        self.name = 'meter_polling'

    def run(self):
        start = self.start_time
        interval = 1 / self.freq
        counts_per_sample = 1/ self.up_freq
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

    

class APP(ctk.CTk):
    def __init__(self):
        super().__init__()

        # configure application window
        self.title('MAPPL Logger')
        scrn_w = self.winfo_screenwidth() - 100
        scrn_h = self.winfo_screenheight() - 100
        self.config(background='black')
        self.geometry(f'{scrn_w}x{scrn_h}+50+25')

        self.grid_rowconfigure(0, weight=2)
        self.grid_rowconfigure(1, weight=3)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)

        self.protocol("WM_DELETE_WINDOW", lambda:_quit(self))
    
        # Application variables
        self.font1 = ctk.CTkFont(family='Arial Baltic', size=20, weight='bold')
        self.font2 = ctk.CTkFont(family='Arial Baltic', size=14, weight='bold')
    
        self.text_filename = ctk.StringVar()
        self.pause_button_state = False
        self.measurment_parameters = ['Volts', 'Amps', 'Power', 'Probe Temperature', 'Reactive Power', 'Cumulative Imported Energy', 'Cumulative Exported Energy', 'Cumulative Imported Reactive Energy', 'Cumulative Exported Reactive Energy', 'Power Factor']
        self.measurment_freq = ctk.IntVar()

        self.meters = []
        


        # selection frame
        self.selection_frame = ctk.CTkScrollableFrame(self, corner_radius=5, bg_color='black', fg_color='grey18', orientation='horizontal')
        self.selection_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

        self.meter_label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text='Meter', fg_color='grey50', text_color='black', font=self.font2, anchor='w')
        self.meter_label.grid(row=0, column=0, padx=5, pady=3, sticky='nsew')

        for i, label in enumerate(self.measurment_parameters):
              label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text=label, fg_color='grey50', text_color='black', font=self.font2, anchor='w')
              label.grid(row=i+1, column=0, padx=5, pady=3, sticky='nsew') 

        # Graph Frame
        self.graph_frame = ctk.CTkFrame(self, corner_radius=0, bg_color='black', fg_color='grey18')
        self.graph_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')
        self.graph_frame.rowconfigure(0, weight=1)
        self.graph_frame.columnconfigure(0, weight=1)
         
        plt.style.use('dark_background') 

        fig1, ax1 = plt.subplots()
        plt.grid(color='.5')
        plt.subplots_adjust(left=.03, right=.83, top=.95, bottom=.05)
        self.fig1 = fig1
        self.ax1 = ax1
        self.ax1.spines[['top', 'bottom', 'left', 'right']].set_color('0.18')
        self.ax1.spines[['top', 'bottom', 'left', 'right']].set_linewidth(4)
        self.ax1.xaxis.label.set_color('.5')
        self.ax1.yaxis.label.set_color('.5')

        self.ax1.tick_params(axis='both', width=3, colors='.5', which='both', size=10)

        self.canvas1 = FigureCanvasTkAgg(self.fig1, self.graph_frame)
        self.canvas1.get_tk_widget().grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        self.canvas1.draw()


        # Options Frame
        self.options_frame = ctk.CTkFrame(self, corner_radius=5, bg_color='black', fg_color='grey18')
        self.options_frame.grid(row=0, rowspan=1, column=0, padx=5, pady=5, sticky='nsew')
        self.options_frame.columnconfigure(0, weight=1)
        self.options_frame.rowconfigure((0,1,2,3,4,5,6,7,8,9), weight=1)
    

        self.refresh_button = ctk.CTkButton(self.options_frame, corner_radius=5, text='Refresh', fg_color='yellow2', text_color='grey18', font=self.font1, command=self.scan_meters, hover_color='grey50')
        self.refresh_button.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

        self.start_button = ctk.CTkButton(self.options_frame, corner_radius=5, text='Start', fg_color='yellow2', text_color='grey18', font=self.font1, command=self.log_data, hover_color='grey50')
        self.start_button.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
    
        self.pause_button = ctk.CTkButton(self.options_frame, corner_radius=5, text='Pause', fg_color='yellow2', text_color='grey18', font=self.font1, command=self.pause_logging, hover_color='grey50')
        self.pause_button.grid(row=2, column=0, padx=5, pady=5, sticky='nsew')

        # Options Frame 2
        self.options2_frame = ctk.CTkFrame(self, corner_radius=5, bg_color='black', fg_color='grey18')
        self.options2_frame.grid(row=0, column=2, padx=5, pady=5, sticky='nsew')
        self.options2_frame.columnconfigure((0,1), weight=1)


        self.duration_label = ctk.CTkLabel(self.options2_frame, corner_radius=5, text='Duration', fg_color='grey18', text_color='yellow2', font=self.font2)
        self.duration_label.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

        self.duration_textbox = ctk.CTkEntry(self.options2_frame, corner_radius=5, placeholder_text='Enter duration as integer in Seconds', font=self.font2, placeholder_text_color='yellow2', text_color='yellow2')
        self.duration_textbox.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')

        self.measurment_frequency = ctk.CTkLabel(self.options2_frame, corner_radius=5, text='Measurment Frequency', fg_color='grey18', text_color='yellow2', font=self.font2)
        self.measurment_frequency.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

        self.measurment_frequency = ctk.CTkLabel(self.options2_frame, corner_radius=5, textvariable=str(self.measurment_freq), fg_color='grey18', text_color='black', font=self.font1)
        self.measurment_frequency.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')

        self.freq_slider = ctk.CTkSlider(self.options2_frame, variable=self.measurment_freq, from_=1, to=60, number_of_steps=60, command=self.set_freq_var)
        self.freq_slider.grid(row=3, column=1, padx=5, pady=5, sticky='nsew')

    def pause_logging(self):
        if self.pause_button_state:         # If the state is False, this means that it is not paused
            self.pause_button_state = False
            self.pause_button.configure(text='Pause')

        else:
            self.pause_button_state = True
            self.pause_button.configure(text='Resume')


    def log_data(self):
        filename = tk.filedialog.asksaveasfilename(title='Save output data as: ', filetypes = [('CSV files', '*csv')])
        M_polling = Meter_polling(self.meters)
    
        self.update_graph()

    def scan_meters(self):

        ports = serial.tools.list_ports.comports()
        meters = []
        
        for p in ports:
            if p.serial_number and p.serial_number[:3] == '_M_':
                with serial.Serial(baudrate=115200, port=p.device) as port:
                    setattr(port, 'serial_number', p.serial_number)
                    meters.append(port)

        self.meters = meters

        for widget in self.selection_frame.winfo_children():              #all existing buttons need to be deleted before making the new ones, but we only want to delete the buttons
            if isinstance(widget, (ctk.CTkCheckBox, ctk.CTkLabel)):
                widget.destroy()

        self.meter_label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text='Meter', fg_color='grey18', text_color='yellow2', font=self.font2, anchor='w')
        self.meter_label.grid(row=0, column=0, padx=5, pady=3, sticky='nsew')

        self.meter_label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text='All', fg_color='grey18', text_color='yellow2', font=self.font1, anchor='w')
        self.meter_label.grid(row=0, column=1, padx=5, pady=3, sticky='nsew')

        for i, label in enumerate(self.measurment_parameters):
            ctk.CTkCheckBox(self.selection_frame, text=None, corner_radius=10, hover_color='yellow2', checkbox_width=50, border_color='black', fg_color='black', border_width=2).grid(row=i+1, column=1, padx=5, pady=3, sticky='nse')
            label = ctk.CTkLabel(self.selection_frame, corner_radius=5, text=label, fg_color='grey18', text_color='yellow2', font=self.font2, anchor='w')
            label.grid(row=i+1, column=0, padx=5, pady=3, sticky='nsew') 

        parameter_selections = {}
        for col, m in enumerate(meters):
            ctk.CTkLabel(self.selection_frame, corner_radius=5, text=m.serial_number[4:], fg_color='grey18', text_color='yellow2', font=self.font1, anchor='w').grid(row=0, column=col+2, padx=5, pady=5, sticky='nsew')
            parameter_selections[m.serial_number] = {key: ctk.CTkCheckBox(self.selection_frame, text=None, corner_radius=10, checkbox_width=50, hover_color='yellow2', border_color='black', fg_color='black', border_width=2).grid(row=row+1, column=col+2, padx=5, pady=3, sticky='nse') for row, key in enumerate(self.measurment_parameters)}

        print([meter.serial_number for meter in self.meters])


    def update_graph(self):
        for i in range(1000):
            delay =  (i + 1) * 100
            self.after(delay, lambda i=i: self.plot_data(i*2))
        
            
    def plot_data(self, i):
        x_values = np.arange(0,200,.05) #total data points
        if i > 1000:
            current_x_values = x_values[i-1000:i]
        else:
            current_x_values = x_values[:i]
        current_y_values1 = np.sin(current_x_values)
        current_y_values2 = np.cos(current_x_values)

        self.ax1.clear()
        line1 = self.ax1.plot(current_x_values,current_y_values1, label=f'{round(current_y_values1[-1],2)}  :   Cumulative Exported Reactive Energy')
        line2 = self.ax1.plot(current_x_values,current_y_values2, label=f'{round(current_y_values2[-1], 2)}   :   Volts')

        legend = self.ax1.legend(loc='upper left', bbox_to_anchor=(1, .5), labelcolor='linecolor')
        self.canvas1.draw()

    def set_freq_var(self, value):
        print(self.measurment_freq.get())
        
if __name__ == '__main__':
    app = APP()
    app.mainloop()