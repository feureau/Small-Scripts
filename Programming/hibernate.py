import os
import time
import sys

def hibernate_timer():
    # 1. Prompt and validate user input for Hours or Minutes
    while True:
        print("Enter the time before hibernating.")
        print("Use 'h' for hours or 'm' for minutes (e.g., '2h', '45m', '1.5h').")
        user_input = input("Time: ").strip().lower()
        
        if not user_input:
            print("Input cannot be empty.\n")
            continue
            
        # Determine the unit based on the last character
        if user_input.endswith('h'):
            unit = 'hours'
            num_str = user_input[:-1] # Remove the 'h' to get just the number
            multiplier = 3600         # 60 * 60 seconds in an hour
        elif user_input.endswith('m'):
            unit = 'minutes'
            num_str = user_input[:-1] # Remove the 'm'
            multiplier = 60
        else:
            # If they just type a number without a letter, default to minutes
            unit = 'minutes'
            num_str = user_input
            multiplier = 60
            
        try:
            # Convert the extracted number string to a float
            value = float(num_str)
            if value <= 0:
                print("Please enter a positive number.\n")
                continue
            break # Exit the loop if everything is valid
        except ValueError:
            print("Invalid input. Please use a format like '2h' or '30m'.\n")

    # 2. Convert to total seconds
    seconds = int(value * multiplier)

    print(f"\nThe computer will hibernate in {value} {unit}.")
    print("Press Ctrl+C at any time to cancel.\n")

    # 3. Countdown loop (Upgraded to handle HH:MM:SS)
    try:
        while seconds > 0:
            # Calculate hours, minutes, and seconds
            mins, secs = divmod(seconds, 60)
            hours, mins = divmod(mins, 60)
            
            # Format the display differently if it's over an hour
            if hours > 0:
                timer_display = f"{hours:02d}:{mins:02d}:{secs:02d}"
            else:
                timer_display = f"{mins:02d}:{secs:02d}"
            
            # The end="\r" overwrites the current line
            print(f"Time remaining: {timer_display} ", end="\r")
            
            time.sleep(1)
            seconds -= 1
            
    except KeyboardInterrupt:
        print("\n\nTimer canceled by user. The computer will not hibernate.")
        sys.exit(0)

    # 4. Hibernate the computer
    print("\n\nTime's up! Hibernating the computer now...")
    os.system("shutdown /h")

if __name__ == "__main__":
    hibernate_timer()