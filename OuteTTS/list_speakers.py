import outetts

# Create a default config
config = outetts.ModelConfig()

# Create the interface using the config
interface = outetts.Interface(config=config)

# Print available speakers
interface.print_default_speakers()
