import logging
import os
import requests
from modules.module import Module

class Rewriting(Module):
    def __init__(self):
        super().__init__("rewriting")
        
    def print_help(self):
        pass
    
    def print_commands(self):
        pass

def __getattr__(name):
    return Rewriting