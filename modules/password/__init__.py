import csv
import json
import random
import requests
import logging
import os
import string
from config import get_use_https

from modules.module import Module

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
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
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
    
    """
    Set a password for a mailbox
    
    Path: /api/v1/edit/mailbox/
    
    @param mailbox_id: The ID of the mailbox to set the password for
    @param password: The password to set for the mailbox
    """
    @staticmethod
    def set(mailbox_id : str, password : str, no_print : bool = False) -> bool:
        logger = logging.getLogger(__name__)
        
        logger.debug(f"Setting password for mailbox {mailbox_id} to {password}")
        
        if not Password.validate(password, no_print=True):
            logger.error("Failed to validate password")
            return False
        
        from modules.mailbox import Mailbox
        if not Mailbox.exists(mailbox_id):
            logger.error(f"Mailbox {mailbox_id} not found")
            return False
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/edit/mailbox/"
        
        data = {
            "items": [ mailbox_id ],
            "attr": {
                "password": password,
                "password2": password
            }
        }
        
        post_data_json = json.dumps(data)
        
        response = requests.post(endpoint, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, verify=validate_certificate, data=post_data_json, allow_redirects=False)
        json_response = response.json()
        
        if response.status_code > 299 or ('type' in json_response and json_response['type'] == 'error'):
            logger.error(f"[{response.status_code}] Failed to set password: {json_response['msg']}")
            return False
        
        if not no_print:
            logger.info("Password set successfully")
        
        return True
    
    """
    Set a password for a mailbox from a CSV file
    
    Path: /api/v1/edit/mailbox/
    
    @param path_to_csv: The path to the CSV file
    @param has_headers: Whether the CSV file has headers (default: True)
    @param delimeter: The delimeter to use for the CSV file (default: ,)
    @param array_delimeter: The delimeter to use for the array in the CSV file (default: |)
    """
    @staticmethod
    def set_batch(path_to_csv : str, has_headers : bool = True, delimeter : str = ",", array_delimeter : str = "|") -> bool:
        logger = logging.getLogger(__name__)
        
        if not os.path.exists(path_to_csv):
            logger.error(f"File {path_to_csv} does not exist")
            return False
        
        with open(path_to_csv, "r") as file:
            reader = csv.reader(file, delimiter=delimeter)
            
            if has_headers:
                next(reader)
            
            for row in reader:
                mailbox_id = row[0]
                password = row[2]
                
                if not Password.set(mailbox_id, password, no_print=True):
                    logger.error(f"Failed to set password for mailbox {mailbox_id}")
                    continue
                else:
                    if logger.level == logging.DEBUG:
                        logger.debug(f"Set password for mailbox {mailbox_id} to {password}")
                    else:
                        logger.info(f"Set password for mailbox {mailbox_id}")
        
        return True

    def print_help(self):
        logger = logging.getLogger(__name__)
        logger.info("Available commands for password module:")
        logger.info("  generate: Generate a password")
        logger.info("  policy: Retrieve the policy for password generation")
        logger.info("  validate <password(str)>: Validate a password")
        logger.info("  set <mailbox_id(str) <password(str)>: Set a password for a mailbox")
        logger.info("  set_batch <path_to_csv(str)>: Set a password for a mailbox from a CSV file")
        
    def print_commands(self):
        print("generate policy validate set set_batch")

def __getattr__(name):
    return Password