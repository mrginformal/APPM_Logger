import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation

class RealTimePlotter(tk.Tk):
    def __init__(self):
        super().__init__()

        self.left_frame = ttk.Frame(self)
        self.right_frame = ttk.Frame(self)
        self.left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        self.right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)

        self.x_data = []
        self.data1 = []
        self.data2 = []
        self.current_index = 0
        self.max_points = 100
        self.show_data1 = True
        self.show_data2 = True
        self.running = True

        self.pause_button = ttk.Button(self.left_frame, text="Pause/Resume", command=self.toggle_stream)
        self.toggle_data1_button = ttk.Button(self.left_frame, text="Toggle Data 1", command=self.toggle_data1_visibility)
        self.toggle_data2_button = ttk.Button(self.left_frame, text="Toggle Data 2", command=self.toggle_data2_visibility)

        self.pause_button.pack(pady=5)
        self.toggle_data1_button.pack(pady=5)
        self.toggle_data2_button.pack(pady=5)

        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, self.right_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.line1, = self.ax.plot([], [], label="Data 1", color="blue")
        self.line2, = self.ax.plot([], [], label="Data 2", color="red")

        self.ani = FuncAnimation(self.figure, self.update_plot, interval=50)

    def toggle_stream(self):
        self.running = not self.running

    def toggle_data1_visibility(self):
        self.show_data1 = not self.show_data1

    def toggle_data2_visibility(self):
        self.show_data2 = not self.show_data2

    def update_plot(self, _):
        if self.running:
            self.current_index += 1
            self.x_data.append(self.current_index)
            self.data1.append(np.random.randn())
            self.data2.append(np.random.randn())

            # Keep the data lists to a fixed size
            if len(self.x_data) > self.max_points:
                self.x_data.pop(0)
                self.data1.pop(0)
                self.data2.pop(0)

            self.line1.set_data(self.x_data, self.data1)
            self.line2.set_data(self.x_data, self.data2)
            
            self.ax.relim()
            self.ax.autoscale_view()

            if not self.show_data1:
                self.line1.set_visible(False)
            else:
                self.line1.set_visible(True)

            if not self.show_data2:
                self.line2.set_visible(False)
            else:
                self.line2.set_visible(True)

            self.ax.legend()
            self.canvas.draw_idle()

if __name__ == "__main__":
    app = RealTimePlotter()
    app.mainloop()