import logging
import os
import requests
from modules.module import Module

class Domain(Module):
    def __init__(self):
        super().__init__("domain")
        
    def print_help(self):
        pass
    
    def print_commands(self):
        pass
def __getattr__(name):
    return Domain