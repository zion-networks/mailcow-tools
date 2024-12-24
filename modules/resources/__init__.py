import logging
import os
import requests
from modules.module import Module

class Resources(Module):
    def __init__(self):
        super().__init__("resources")
        
    def print_help(self):
        pass
    
    def print_commands(self):
        pass

def __getattr__(name):
    return Resources