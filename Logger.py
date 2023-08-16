import pandas as pd
import numpy as np
import tkinter as tk
import customtkinter as ctk
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle 

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)


ctk.set_appearance_mode('Dark')
mplstyle.use('fast')

def _quit(app):
    app.destroy()
    exit()

class APP(ctk.CTk):
    def __init__(self):
        super().__init__()

        # configure application window
        self.title('MAPPL Logger')
        scrn_w = self.winfo_screenwidth() - 100
        scrn_h = self.winfo_screenheight() - 100
        self.config(background='black')
        self.geometry(f'{scrn_w}x{scrn_h}+50+25')

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=4)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=5)

        self.protocol("WM_DELETE_WINDOW", lambda:_quit(self))
        
        # selection frame
        self.selection_frame = ctk.CTkFrame(self, corner_radius=5, bg_color='black', fg_color='grey18')
        self.selection_frame.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky='nsew')


        # Graph Frame
        self.graph_frame = ctk.CTkFrame(self, corner_radius=0, bg_color='black', fg_color='grey18')
        self.graph_frame.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
        self.graph_frame.rowconfigure(0, weight=1)
        self.graph_frame.columnconfigure(0, weight=1)
         
        plt.style.use('dark_background') 

        fig1, ax1 = plt.subplots()
        plt.grid(color='.5')
        plt.subplots_adjust(left=.05, right=.95, top=.95, bottom=.05)
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

        # Parameter Frame
        self.graph_frame = ctk.CTkFrame(self, corner_radius=5, bg_color='black', fg_color='grey18')
        self.graph_frame.grid(row=0, rowspan=2, column=0, padx=5, pady=5, sticky='nsew')



    def log_data(self):
        pass

    def update_graph(self):
        pass

if __name__ == '__main__':
    app = APP()
    app.mainloop()