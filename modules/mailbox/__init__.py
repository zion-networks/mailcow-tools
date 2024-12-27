import csv
import logging
import requests
import os
import json
import re
from config import get_use_https
from modules.alias import Alias
from modules.module import Module
from modules.password import Password

"""
Represents a mailbox object in Mailcow
"""
class Mailbox(Module):
    def __init__(self, mailbox_id : str|None = None, full_name : str|None = None, password : str|None = None, quota : int = 1024, active : bool = True, force_password_change : bool = False, tls_enforce_in : bool = True, tls_enforce_out : bool = True):
        super().__init__("mailbox")
        
        self.mailbox_id = mailbox_id
        self.full_name = full_name
        self.password = password
        self.quota = quota
        self.active = active
        self.force_password_change = force_password_change
        self.tls_enforce_in = tls_enforce_in
        self.tls_enforce_out = tls_enforce_out

    """
    Get all mailboxes
    Path: GET /api/v1/get/mailbox/all
    """
    @staticmethod
    def list(include_aliases : bool = True, no_print : bool = False):
        logger = logging.getLogger(__name__)
        
        if include_aliases:
            aliases = Alias.list(no_print=True)
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/get/mailbox/all"
        
        response = requests.get(endpoint, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, verify=validate_certificate, allow_redirects=False)
        
        data = response.json()
        if response.status_code > 299 or ('type' in data and data['type'] == 'error'):
            logger.error(f"[{response.status_code}] Failed to get mailboxes: {data['msg']}")
            return

        if len(data) == 0 and not no_print:
            logger.warning(f"[{response.status_code}] No mailboxes found")
            return
        
        if not no_print:
            logger.info(f"[{response.status_code}] Found {len(data)} mailboxes with {len(aliases)} aliases:")
        
        for mailbox in data:
            mailbox_aliases = []
            if include_aliases:
                mailbox_aliases = [alias for alias in aliases if alias['goto'] == mailbox['username']]
                mailbox['aliases'] = mailbox_aliases
            
            if not no_print:
                quota_used = int(mailbox['quota_used']) / 1024 / 1024 if 'quota_used' in mailbox else 0
                quota = int(mailbox['quota']) / 1024 / 1024 if 'quota' in mailbox else 0
                
                logger.info(f"  - {'✅' if mailbox['active'] == 1 else '🚫'} {mailbox['username']}: {mailbox['name']} ({quota_used} MB / {quota} MB)")
                
                if include_aliases and len(mailbox_aliases) > 0:
                    for alias in mailbox_aliases:
                        logger.info(f"       - {'✅' if alias['active'] == 1 else '🚫'} {alias['address']} => {alias['goto']}")
    
        return data
    
    """
    Check if a mailbox exists
    Path: GET /api/v1/get/mailbox/{mailbox_id}
    
    @param mailbox_id: The mailbox ID
    @return: True if the mailbox exists, False otherwise
    """
    @staticmethod
    def exists(mailbox_id : str, no_print : bool = False) -> bool:
        logger = logging.getLogger(__name__)
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/get/mailbox/{mailbox_id}"
        
        response = requests.get(endpoint, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, verify=validate_certificate, allow_redirects=False)
        
        data = response.json()
        
        if response.status_code > 299 or ('type' in data and data['type'] == 'error'):
            logger.error(f"[{response.status_code}] Failed to check if mailbox exists: {data['msg']}")
            return False
        
        if len(data) == 0:
            if not no_print:
                logger.warning(f"[{response.status_code}] Mailbox {mailbox_id} does not exist")
                
            return False
        
        if not no_print:
            logger.info(f"[{response.status_code}] Mailbox {mailbox_id} exists")
            
        return True
    
    """
    Create a new mailbox
    
    Path: POST /api/v1/add/mailbox
    
    @param mailbox_id: The mailbox ID
    @param full_name: The full name of the mailbox
    @param password: The password of the mailbox
    @param quota: The quota of the mailbox in MB (default: 1024)
    @param active: Whether the mailbox is active (default: True)
    @param force_password_change: Whether to force the password change (default: False)
    @param tls_enforce_in: Whether to enforce TLS in (default: True)
    @param tls_enforce_out: Whether to enforce TLS out (default: True)
    
    @return: The mailbox data
    """
    @staticmethod
    def create(mailbox_id : str, full_name : str|None = None, password : str|None = None, quota : int = 1024, active : bool = True, force_password_change : bool = False, tls_enforce_in : bool = True, tls_enforce_out : bool = True):
        logger = logging.getLogger(__name__)
        
        if not Mailbox.validate_mailbox_id(mailbox_id, no_print=True):
            logger.error(f"Invalid mailbox ID: {mailbox_id}")
            return
        
        if Mailbox.exists(mailbox_id):
            logger.error(f"Mailbox {mailbox_id} already exists")
            return
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/add/mailbox"
        
        local_part = mailbox_id.split("@")[0]
        domain_part = mailbox_id.split("@")[1]
        
        if not full_name:
            full_name = local_part
        
        if not password:
            password = Password.generate()
            
            if password is None:
                logger.error("Failed to generate password")
                return
            
            logger.info(f"Generated password for {mailbox_id}: {password}")
        
        post_data = {
            "local_part": local_part,
            "domain": domain_part,
            "name": full_name,
            "quota": str(quota),
            "password": password,
            "password2": password,
            "active": "1" if active else "0",
            "force_pw_update": "1" if force_password_change else "0",
            "tls_enforce_in": "1" if tls_enforce_in else "0",
            "tls_enforce_out": "1" if tls_enforce_out else "0"
        }
        
        post_data_json = json.dumps(post_data)
        
        logger.debug(f"Post data being sent: {post_data_json}")
        
        response = requests.post(endpoint, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, verify=validate_certificate, data=post_data_json, allow_redirects=False)
        
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response content: {response.content}")
        
        data = response.json()
        
        if response.status_code > 299 or ('type' in data and data['type'] == 'error'):
            logger.error(f"[{response.status_code}] Failed to create mailbox: {data['msg']}")
            return
        
        logger.info(f"[{response.status_code}] Mailbox {mailbox_id} created successfully")
        
        return post_data
    
    """
    Batch create mailboxes from a CSV file
    
    @param path_to_csv: The path to the CSV file
    @param has_headers: Whether the CSV file has headers (default: True)
    @param save_to_csv: The path to the CSV file to save the created mailboxes (default: None)
    @param override_csv: Whether to override the CSV file (default: False)
    @param delimeter: The delimeter of the CSV file (default: ",")
    @param array_delimeter: The delimeter of the array (default: "|")
    """
    @staticmethod
    def create_batch(path_to_csv : str|None = None, has_headers : bool = True, save_to_csv : str|None = None, override_csv : bool = False, delimeter : str = ",", array_delimeter : str = "|"):
        logger = logging.getLogger(__name__)
        
        if path_to_csv is None:
            logger.error("Path to CSV file is required")
            return
        
        if not os.path.exists(path_to_csv):
            logger.error(f"File {path_to_csv} does not exist")
            return
        
        if delimeter not in [",", ";", "|", ":", "\t"]:
            logger.error(f"Invalid delimeter: {delimeter}")
            return
                
        # check if file has any contents
        with open(path_to_csv, "r") as file:
            if file.read().strip() == "":
                logger.error(f"File {path_to_csv} is empty")
                return
        
        if save_to_csv and os.path.exists(save_to_csv):
            if not override_csv:
                logger.error(f"File {save_to_csv} already exists")
                return
            else:
                logger.warning(f"File {save_to_csv} already exists, overwriting file")
        
        created_mailboxes = []
        with open(path_to_csv, "r") as file:
            reader = csv.reader(file, delimiter=delimeter)
            
            if has_headers:
                next(reader)
            
            for row in reader:
                mailbox_id = row[0] if len(row) > 0 else None
                full_name = row[1] if len(row) > 1 else None
                password = row[2] if len(row) > 2 else None
                quota = row[3] if len(row) > 3 and row[3].isdigit() else 1024
                active = row[4] if len(row) > 4 else True
                force_password_change = row[5] if len(row) > 5 else False
                tls_enforce_in = row[6] if len(row) > 6 else True
                tls_enforce_out = row[7] if len(row) > 7 else True
                aliases = row[8] if len(row) > 8 else None
                
                # validate mailbox_id to be a valid email address
                if not Mailbox.validate_mailbox_id(mailbox_id, no_print=True):
                    logger.warning(f"Mailbox ID {mailbox_id} is not a valid email address, skipping mailbox")
                    continue
                
                if len(row) > 2 and len(row[2]) > 0 and not Password.validate(password):
                    logger.warning(f"User defined password for {mailbox_id} does not meet the password policy, skipping mailbox")
                    continue
                
                if len(row) > 3 and len(row[3]) > 0 and not row[3].isdigit():
                    logger.warning(f"User defined quota for {mailbox_id} is not a valid number, fallback to default quota of 1024")
                    quota = 1024
                
                if not password or len(password) == 0:
                    password = Password.generate()
                    
                    if password is None:
                        logger.error("Failed to generate password")
                        continue
                    
                    logger.info(f"Generated password for {mailbox_id}: {password}")
                
                mailbox_domain = mailbox_id.split("@")[1]
                
                aliases_list = []
                if aliases and len(aliases) > 0:
                    aliases_list = aliases.split(array_delimeter)
                
                for alias in aliases_list:
                    if not Mailbox.validate_mailbox_id(f"{alias}@{mailbox_domain}", no_print=True):
                        logger.warning(f"Alias {alias}@{mailbox_domain} is not a valid email address, skipping alias")
                        aliases_list.remove(alias)
                        continue
                
                Mailbox.create(mailbox_id, full_name, password, quota, active, force_password_change, tls_enforce_in, tls_enforce_out)
                
                for alias in aliases_list:
                    Mailbox.create_alias(f"{alias}@{mailbox_domain}", [mailbox_id], active=active)
                    
                created_mailboxes.append({
                    "mailbox_id": mailbox_id,
                    "full_name": full_name,
                    "password": password,
                    "quota": quota,
                    "active": active,
                    "force_password_change": force_password_change,
                    "tls_enforce_in": tls_enforce_in,
                    "tls_enforce_out": tls_enforce_out,
                    "aliases": aliases_list
                })
                
            if save_to_csv:
                with open(save_to_csv, "w") as file:
                    file.write(f"mailbox_id{delimeter}full_name{delimeter}password{delimeter}quota{delimeter}active{delimeter}force_password_change{delimeter}tls_enforce_in{delimeter}tls_enforce_out{delimeter}aliases\n")
                    
                    for created_mailbox in created_mailboxes:
                        file.write(f"{created_mailbox['mailbox_id']}{delimeter}{created_mailbox['full_name']}{delimeter}{created_mailbox['password']}{delimeter}{created_mailbox['quota']}{delimeter}{created_mailbox['active']}{delimeter}{created_mailbox['force_password_change']}{delimeter}{created_mailbox['tls_enforce_in']}{delimeter}{created_mailbox['tls_enforce_out']}{delimeter}{array_delimeter.join(created_mailbox['aliases'])}\n")
                    
                    logger.info(f"Mailboxes created successfully and updated CSV file at {save_to_csv}")
    
    """
    Create a batch template for creating mailboxes
    """
    @staticmethod
    def create_batch_template(path_to_csv : str, with_example : bool = False, overwrite : bool = False, delimeter : str = ",", array_delimeter : str = "|"):
        logger = logging.getLogger(__name__)
        
        if os.path.exists(path_to_csv):
            if not overwrite:
                logger.error(f"File {path_to_csv} already exists")
                return
            else:
                logger.warning(f"File {path_to_csv} already exists, overwriting file")
        
        if delimeter not in [",", ";", "|", ":", "\t"]:
            logger.error(f"Invalid delimeter: {delimeter}")
            return
        
        csv_data = f"mailbox_id{delimeter}full_name{delimeter}password{delimeter}quota{delimeter}active{delimeter}force_password_change{delimeter}tls_enforce_in{delimeter}tls_enforce_out{delimeter}aliases"
        
        if with_example:
            csv_data += f"user@domain.tld{delimeter}Full Name{delimeter}password{delimeter}1234{delimeter}true{delimeter}false{delimeter}true{delimeter}true{delimeter}alias1{array_delimeter}alias2{array_delimeter}alias3"
        
        with open(path_to_csv, "w") as file:
            file.write(csv_data)
            file.write("\n")
        
        logger.info(f"Batch template created at {path_to_csv}")
    
    """
    Validate a mailbox ID
    """
    @staticmethod
    def validate_mailbox_id(mailbox_id : str, no_print : bool = False):
        logger = logging.getLogger(__name__)
        
        if not mailbox_id or len(mailbox_id) == 0 or "@" not in mailbox_id:
            if not no_print:
                logger.warning(f"Mailbox ID {mailbox_id} is not a valid email address, skipping mailbox")
                
            return False
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", mailbox_id):
            if not no_print:
                logger.warning(f"Mailbox ID {mailbox_id} is not a valid email address, skipping mailbox")
                
            return False
        
        return True
    
    """
    Delete a mailbox
    """
    @staticmethod
    def delete(mailbox_id : str):
        logger = logging.getLogger(__name__)
        logger.warning("Delete a mailbox is not implemented yet")
        pass
    
    def print_help(self):
        logger = logging.getLogger(__name__)
        logger.info("Available commands for mailbox module:")
        logger.info("  list: List all mailboxes")
        logger.info("  exists <mailbox_id(str)>: Check if a mailbox exists")
        logger.info("  create <mailbox_id(str)> [full_name(str)] [password(str)] [quota(int)] [active(true|false)] [force_password_change(true|false)] [tls_enforce_in(true|false)] [tls_enforce_out(true|false)]: Create a new mailbox")
        logger.info("  create_batch <path_to_csv(str)> [has_headers(true|false)] [save_to_csv(str)] [override_csv(true|false)] [delimeter(,)] [array_delimeter(|)]: Batch create mailboxes from a CSV file")
        logger.info("  create_batch_template <path_to_csv(str)> [with_example(true|false)] [overwrite(true|false)] [delimeter(,)] [array_delimeter(|)]: Create a batch template for creating mailboxes")
        logger.info("  delete <mailbox_id>: Delete a mailbox")

    def print_commands(self):
        print("list exists create create_batch create_batch_template delete")

def __getattr__(name):
    return Mailbox