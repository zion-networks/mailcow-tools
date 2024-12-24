import logging
import os
import requests
from modules.module import Module

class Fail2Ban(Module):
    def __init__(self):
        super().__init__("fail2ban")
        
    def print_help(self):
        pass
    
    def print_commands(self):
        pass

def __getattr__(name):
    return Fail2Ban