import logging
import os
import requests
from modules.module import Module

class DomainAdmin(Module):
    def __init__(self):
        super().__init__("domain-admin")
        
    def print_help(self):
        pass
    
    def print_commands(self):
        pass

def __getattr__(name):
    return DomainAdmin