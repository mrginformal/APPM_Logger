import pandas as pd
import numpy as np
import tkinter as tk
import customtkinter as ctk
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle 
import sys

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)

import os
import sys

extra_path = os.environ.get('Test-Automation-APPM\Firmware\511A_Variation')
if extra_path:
    sys.path.append(extra_path)
    print('hi')

import APPMControl


print('jh')