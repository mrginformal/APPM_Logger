import tkinter as tk
from datetime import datetime, timedelta

def update_timer():
    # Get the current time difference
    elapsed_time = datetime.now() - start_time
    remaining_time = ten_minutes - elapsed_time

    # Convert the remaining time to minutes and seconds
    minutes, seconds = divmod(remaining_time.second, 60)
    
    # Update the label with the new time
    timer_label.config(text=f"{minutes:02}:{seconds:02}")

    if remaining_time > timedelta(seconds=0):
        # Call the update function again after 1000ms (1 second)
        window.after(1000, update_timer)
    else:
        timer_label.config(text="00:00")

# Set up the main window
window = tk.Tk()
window.title("10 Minute Timer")
window.geometry("200x100")

# Define the 10 minutes duration and the starting time
ten_minutes = timedelta(minutes=10)
start_time = datetime.now()

# Create a label to display the timer
timer_label = tk.Label(window, font=("Arial", 30), text="10:00")
timer_label.pack(pady=20)

# Call the update function to start the countdown
update_timer()

window.mainloop()
