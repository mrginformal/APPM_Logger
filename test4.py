import tkinter as tk

class DraggableFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        
        self.drag_data = {"x": 0, "y": 0, "width": 0}

    def on_click(self, event):
        """Record the initial position and width of the frame when the mouse button is pressed."""
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["width"] = self.winfo_width()

    def on_drag(self, event):
        """Handle dragging for resizing the frame."""
        # Calculate distance moved by mouse
        delta_x = event.x - self.drag_data["x"]

        # Update frame width
        new_width = self.drag_data["width"] + delta_x

        # Apply the new width
        self.configure(width=new_width)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("400x400")

    frame = DraggableFrame(root, bg="red", width=200, height=100)
    frame.pack(pady=100, padx=100)

    root.mainloop()
