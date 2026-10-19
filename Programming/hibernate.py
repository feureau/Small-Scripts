import os
import time
import sys


def parse_duration(user_input: str):
    """Parse a duration string (e.g., '2h', '45m', '30s', '15') into (value, unit, seconds)."""
    user_input = user_input.strip().lower()
    if not user_input:
        raise ValueError("Input cannot be empty.")

    # Determine the unit based on the last character
    if user_input.endswith('h'):
        unit = 'hours'
        num_str = user_input[:-1]  # Remove the 'h' to get just the number
        multiplier = 3600          # 60 * 60 seconds in an hour
    elif user_input.endswith('m'):
        unit = 'minutes'
        num_str = user_input[:-1]  # Remove the 'm'
        multiplier = 60
    elif user_input.endswith('s'):
        unit = 'seconds'
        num_str = user_input[:-1]  # Remove the 's'
        multiplier = 1
    else:
        # If they just type a number without a letter, default to minutes
        unit = 'minutes'
        num_str = user_input
        multiplier = 60

    try:
        # Convert the extracted number string to a float
        value = float(num_str)
    except ValueError:
        raise ValueError("Invalid input. Please use a format like '2h', '30m', or '45s'.")

    if value <= 0:
        raise ValueError("Please enter a positive number.")

    seconds = int(round(value * multiplier))
    return value, unit, seconds


def hibernate_timer():
    # 1. Check for command-line argument first, otherwise prompt interactively
    value = unit = seconds = None

    if len(sys.argv) > 1:
        raw_arg = "".join(sys.argv[1:])
        try:
            value, unit, seconds = parse_duration(raw_arg)
        except ValueError as e:
            print(f"Error: {e}\n")

    # Prompt and validate user input if not provided (or invalid) via CLI
    while seconds is None:
        print("Enter the time before hibernating.")
        print("Use 'h' for hours, 'm' for minutes, or 's' for seconds (e.g., '2h', '45m', '1.5h').")
        user_input = input("Time: ")

        try:
            value, unit, seconds = parse_duration(user_input)
        except ValueError as e:
            print(f"{e}\n")

    # Format display value cleanly (e.g., '2' instead of '2.0')
    display_val = int(value) if value.is_integer() else value
    print(f"\nThe computer will hibernate in {display_val} {unit}.")
    print("Press Ctrl+C at any time to cancel.\n")

    # 3. Countdown loop using monotonic clock to prevent timer drift
    end_time = time.monotonic() + seconds

    try:
        while True:
            remaining = round(end_time - time.monotonic())
            if remaining <= 0:
                break

            # Calculate hours, minutes, and seconds
            mins, secs = divmod(remaining, 60)
            hours, mins = divmod(mins, 60)

            # Format the display differently if it's over an hour
            if hours > 0:
                timer_display = f"{hours:02d}:{mins:02d}:{secs:02d}"
            else:
                timer_display = f"{mins:02d}:{secs:02d}"

            # The end="\r" overwrites the current line; <8 pads to clear leftover chars
            print(f"Time remaining: {timer_display:<8}", end="\r", flush=True)

            # Sleep until the next whole second tick
            sleep_duration = (end_time - time.monotonic()) - (remaining - 1)
            time.sleep(max(0.05, min(1.0, sleep_duration)))

    except KeyboardInterrupt:
        print("\n\nTimer canceled by user. The computer will not hibernate.")
        sys.exit(0)

    # 4. Hibernate the computer
    print(f"Time remaining: {'00:00':<8}")
    print("\nTime's up! Hibernating the computer now...")
    os.system("shutdown /h")


if __name__ == "__main__":
    hibernate_timer()