import logging
import os
import requests
from modules.module import Module

class Queue(Module):
    def __init__(self):
        super().__init__("queue")
        
    def print_help(self):
        pass
    
    def print_commands(self):
        pass

def __getattr__(name):
    return Queue