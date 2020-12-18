import os
import pathlib
import bpy

class LocalPartListLoader:
    # --------------------------------------------------------------------------
    # Load list of local parts available
    # --------------------------------------------------------------------------
    def load(self, dir):
        configurations = {}

        if os.path.isdir(dir) == False:
            print('Local part directory does not exists.')
            return configurations

        # Scan directory
        with os.scandir(dir) as entries:
            for entry in entries:
                entrypath = os.path.join(dir, entry.name)

                # File
                if os.path.isfile(entrypath):
                    # Check if it is a blend file
                    if pathlib.Path(entry.name).suffix == '.blend':
                        # Configuration name
                        name = os.path.splitext(entry.name)[0]

                        # Bump maps available for the configuration
                        bumps = {}
                        with os.scandir(os.path.join(dir,'bump')) as bump_files:
                            for bump_file in bump_files:
                                if bump_file.name.startswith(name):
                                    bumps[bump_file.name] = os.path.realpath(os.path.join(dir,'bump', bump_file.name))

                        # Save configuration
                        configurations[name] = {
                            'path': os.path.realpath(entrypath),
                            'bumps': bumps
                        }

                # Directory
                elif os.path.isdir(entrypath):
                    configurations = {**configurations, **self.load(entrypath)}

        return configurations
