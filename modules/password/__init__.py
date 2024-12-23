import random
import requests
import logging
import os
import string
from config import get_use_https

from modules.module import Module
from main import MailcowTools

class Password(Module):
    def __init__(self):
        super().__init__("password")

    """
    Retrieve the policy for password generation from the server
    Path: /api/v1/get/passwordpolicy
    """
    @staticmethod
    def policy(no_print : bool = False):
        logger = logging.getLogger(__name__)
        
        mailcow_host = os.getenv("MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/get/passwordpolicy"
        
        response = requests.get(endpoint, headers={"X-API-Key": api_key}, verify=validate_certificate, allow_redirects=False)
        
        if response.status_code == 301 or response.status_code == 302:
            logger.error(f"[{response.status_code}] Unexpected redirect to {response.headers['Location']}")
            return
        
        data = response.json()
        
        if 'type' in data and data['type'] == 'error':
            raise Exception(f"[{response.status_code}] Failed to get password policy: {data['msg']}")
        
        min_length = data['length']
        min_chars = data['chars']
        min_special_chars = data['special_chars']
        min_lowerupper = data['lowerupper']
        min_numbers = data['numbers']
        
        if not no_print:
            logger.info(f"[{response.status_code}] Password policy retrieved successfully:")
            logger.info(f"Must have a minimum length of: {min_length}")
            logger.info(f"Must contain at least alphabetic characters: {min_chars}")
            logger.info(f"Must contain at least uppercase characters: {min_lowerupper}")
            logger.info(f"Must contain at least digits: {min_numbers}")
            logger.info(f"Must contain at least special characters: {min_special_chars}")
        
        return data
    
    """
    Generate a password
    """
    @staticmethod
    def generate(policy = None):
        logger = logging.getLogger(__name__)
        
        if policy is None:
            policy = Password.policy(no_print=True)
            
        if policy is None:
            logger.error("Failed to retrieve password policy")
            return
        
        min_length = int(policy['length'])
        min_chars = int(policy['chars'])
        min_special_chars = int(policy['special_chars'])
        min_lowerupper = int(policy['lowerupper'])
        min_numbers = int(policy['numbers'])
        
        if sum([min_chars, min_lowerupper, min_numbers, min_special_chars]) > min_length:
            logger.warning("Password policy is not valid. Minimum length is less than the sum of the other policy requirements. Adjusting minimum length to match the sum of the other policy requirements.")
            min_length = sum([min_chars, min_lowerupper, min_numbers, min_special_chars])
        
        # generate random alphanumeric string of length min_length
        password = list(''.join(random.choices(string.ascii_letters + string.digits, k=min_length)))
        
        # Replace characters in password to meet policy requirements by those who are already oversatisfied
        # Use characters that are not already in the password if possible
        max_iterations = 1000  # Set a maximum number of iterations to prevent infinite loop
        iteration_count = 0
        password_ready = False
        while not password_ready and iteration_count < max_iterations:
            for i in range(min_length):
                if password[i].isalpha() and min_chars > 0:
                    password[i] = random.choice(string.ascii_letters)
                    min_chars -= 1
                elif password[i].isupper() and min_lowerupper > 0:
                    password[i] = random.choice(string.ascii_uppercase)
                    min_lowerupper -= 1
                elif password[i].isdigit() and min_numbers > 0:
                    password[i] = random.choice(string.digits)
                    min_numbers -= 1
                elif password[i] in string.punctuation and min_special_chars > 0:
                    password[i] = random.choice(string.punctuation)
                    min_special_chars -= 1
                
                if min_chars == 0 and min_lowerupper == 0 and min_numbers == 0 and min_special_chars == 0:
                    password_ready = True
            
            iteration_count += 1
        
        if not password_ready:
            return Password.generate(policy)
        
        logger.info(f"Generated password: {''.join(password)}")
        
        return ''.join(password)
    
    """
    Validate a password
    """
    @staticmethod
    def validate(password : str, policy : dict|None = None, no_print : bool = False):
        logger = logging.getLogger(__name__)
        
        if policy is None:
            policy = Password.policy(no_print=True)
        
        if policy is None:
            logger.error("Failed to retrieve password policy")
            return False
        
        if len(password) < int(policy['length']):
            logger.error(f"Password is too short. Minimum length is {int(policy['length'])}")
            return False
        
        if sum([password.count(char) for char in string.ascii_letters]) < int(policy['chars']):
            logger.error(f"Password does not contain enough alphabetic characters. Minimum is {int(policy['chars'])}")
            return False
        
        if sum([password.count(char) for char in string.ascii_uppercase]) < int(policy['lowerupper']):
            logger.error(f"Password does not contain enough uppercase characters. Minimum is {int(policy['lowerupper'])}")
            return False
        
        if sum([password.count(char) for char in string.digits]) < int(policy['numbers']):
            logger.error(f"Password does not contain enough digits. Minimum is {int(policy['numbers'])}")
            return False
        
        if sum([password.count(char) for char in string.punctuation]) < int(policy['special_chars']):
            logger.error(f"Password does not contain enough special characters. Minimum is {int(policy['special_chars'])}")
            return False
        
        if not no_print:
            logger.info("Password is valid")
        
        return True

    def print_help(self):
        logger = logging.getLogger(__name__)
        logger.info("Available commands for password module:")
        logger.info("  generate: Generate a password")
        logger.info("  policy: Retrieve the policy for password generation")
        logger.info("  validate <password(str)>: Validate a password")

    def print_commands(self):
        print("generate policy validate")

def __getattr__(name):
    return Password