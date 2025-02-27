import tkinter as tk
from tkinter import messagebox
import time
from datetime import datetime, timedelta

class CountdownTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Countdown Timer")

        # Initialize target time and remaining time
        self.target_time = None
        self.time_left = 0
        self.running = False

        # Create UI elements
        self.create_widgets()

    def create_widgets(self):
        # Target time entry
        self.label = tk.Label(self.root, text="Enter target time (HH:MM:SS):")
        self.label.pack(pady=10)

        self.time_entry = tk.Entry(self.root)
        self.time_entry.pack(pady=10)

        # Start button
        self.start_button = tk.Button(self.root, text="Start Timer", command=self.start_timer)
        self.start_button.pack(pady=10)

        # Pause button
        self.pause_button = tk.Button(self.root, text="Pause Timer", command=self.pause_timer)
        self.pause_button.pack(pady=10)

        # Reset button
        self.reset_button = tk.Button(self.root, text="Reset Timer", command=self.reset_timer)
        self.reset_button.pack(pady=10)

        # Label to display the remaining time
        self.time_label = tk.Label(self.root, text="Time left: 00:00:00:000", font=("Helvetica", 16))
        self.time_label.pack(pady=20)

    def start_timer(self):
        try:
            # Get the target time from the entry field in HH:MM:SS format
            target_time_str = self.time_entry.get().strip()
            target_time = datetime.strptime(target_time_str, "%H:%M:%S").time()

            # Get the current time
            current_time = datetime.now().time()

            # Convert times to datetime objects for easy comparison
            current_datetime = datetime.combine(datetime.today(), current_time)
            target_datetime = datetime.combine(datetime.today(), target_time)

            # If the target time is earlier today, we need to count down to the next occurrence of that time
            if target_datetime < current_datetime:
                target_datetime += timedelta(days=1)  # Add one day to target datetime

            # Calculate the remaining time until the target time
            self.time_left = int((target_datetime - current_datetime).total_seconds() * 1000)  # milliseconds
            self.running = True
            self.update_timer()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid time in HH:MM:SS format.")

    def update_timer(self):
        if self.running and self.time_left > 0:
            # Convert the time left (milliseconds) into hours, minutes, seconds, and milliseconds
            hours, remainder = divmod(self.time_left, 3600000)
            minutes, remainder = divmod(remainder, 60000)
            seconds, milliseconds = divmod(remainder, 1000)
            time_str = f"{hours:02}:{minutes:02}:{seconds:02}:{milliseconds:03}"

            # Update the label with the current countdown
            self.time_label.config(text=f"Time left: {time_str}")

            # Decrease time by 100ms (for milliseconds precision)
            self.time_left -= 100
            self.root.after(100, self.update_timer)  # Update every 100 milliseconds
        elif self.time_left <= 0:
            self.time_label.config(text="Time's up!")
            self.running = False
            messagebox.showinfo("Countdown Timer", "The countdown has finished!")

    def pause_timer(self):
        self.running = False

    def reset_timer(self):
        self.running = False
        self.time_left = 0
        self.time_label.config(text="Time left: 00:00:00:000")
        self.time_entry.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    timer = CountdownTimer(root)
    root.mainloop()
