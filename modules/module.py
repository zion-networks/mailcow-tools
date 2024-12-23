"""
Base class for all modules.
"""
class Module:
    def __init__(self, name : str):
        self.name = name

    def print_help(self):
        print(f"Help for module {self.name}")
        raise NotImplementedError("Help method not implemented")
    
    def print_commands(self):
        print(f"Commands for module {self.name}")
        raise NotImplementedError("Commands method not implemented")
