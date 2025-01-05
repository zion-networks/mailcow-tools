import logging
import os
import requests
import re
import csv
from config import get_use_https
from modules.module import Module

"""
Represents a sync job object in Mailcow
"""
class Syncjob(Module):
    RE_HOSTNAME = r"^[a-zA-Z0-9.-]+$"
    RE_IPV4 = r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$"
    RE_IPV6 = r"^[a-fA-F0-9:]+$"
    
    def __init__(self):
        super().__init__("syncjob")
        
    """
    Get all sync jobs
    Path: GET /api/v1/get/syncjobs/all/no_log
    """
    @staticmethod
    def list():
        logger = logging.getLogger(__name__)
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/get/syncjobs/all/no_log"
        
        response = requests.get(endpoint, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, verify=validate_certificate, allow_redirects=False)
        
        data = response.json()
        if response.status_code > 299 or ('type' in data and data['type'] == 'error'):
            logger.error(f"[{response.status_code}] Failed to get sync jobs: {data['msg']}")
            return
        
        if len(data) == 0:
            logger.warning(f"[{response.status_code}] No sync jobs found")
            return
        
        logger.info(f"[{response.status_code}] Found {len(data)} sync jobs:")
        
        for syncjob in data:
            is_active = True if syncjob['active'] == 1 else False
            id = syncjob['id']
            user = syncjob['user1']
            host = syncjob['host1']
            destination = syncjob['user2']
            interval = syncjob['mins_interval']
            last_run = syncjob['last_run'] if 'last_run' in syncjob and syncjob['last_run'] else "Never"
            last_success = True if syncjob['success'] == 1 else False
            is_running = True if syncjob['is_running'] == 1 else False
            
            if is_active:
                if is_running:
                    logger.info(f"  - 🔄 {id}: {user}@{host} => {destination} (⌛ {interval} min) | 🕒 Syncing ...)")
                else:
                    if last_success:
                        logger.info(f"  - ✅ {id}: {user}@{host} => {destination} (⌛ {interval} min) | 🕒 {last_run})")
                    elif last_run == "Never":
                        logger.info(f"  - ⌛ {id}: {user}@{host} => {destination} (⌛ {interval} min) | 🕒 {last_run})")
                    else:
                        logger.info(f"  - ❌ {id}: {user}@{host} => {destination} (⌛ {interval} min) | 🕒 {last_run})")
            else:
                logger.info(f"  - ⏸️ {id}: {user}@{host} => {destination} (⌛ {interval} min) | 🕒 {last_run})")
        
        return data
    
    """
    Create a sync job
    Path: POST /api/v1/add/syncjob
    
    @param mailbox_id: The mailbox ID (example: mailbox@domain.tld)
    @param delete_duplicates_destination: Whether to delete duplicates in the destination mailbox (default: False)
    @param delete_from_source: Whether to delete messages from the source mailbox (default: False)
    @param delete_non_existing_destination: Whether to delete messages from the destination mailbox that do not exist in the source mailbox (default: False)
    @param automap: Whether to automap the mailbox (default: True)
    @param skip_cross_duplicates: Whether to skip cross duplicates (default: False)
    @param active: Whether the sync job is active (default: True)
    @param subscribe_all: Whether to subscribe to all messages (default: True)
    @param host: The host of the source mailbox (example: imap.example.com)
    @param port: The port of the source mailbox (default: 993)
    @param user: The username of the source mailbox (example: username or username@domain.tld)
    @param password: The password of the source mailbox
    @param encryption: The encryption method of the source mailbox (allowed: SSL, TLS, PLAIN)
    @param interval: The interval of the sync job in minutes (default: 20)
    @param subfolder: The subfolder of the source mailbox (default: "")
    @param max_age: The max age of the sync job in days (default: 0, 0 means no limit)
    @param max_bytes_per_second: The max bytes per second of the sync job (default: 0, 0 means no limit)
    @param timeout_remote: The timeout of the remote mailbox in seconds (default: 600)
    @param timeout_local: The timeout of the local mailbox in seconds (default: 600)
    @param exclude: The exclude regex filter of the sync job (default: "")
    @param custom_params: The custom params of the sync job (default: "")
    """
    @staticmethod
    def create(mailbox_id : str,
               host : str = "",
               port : int = 993,
               user : str = "",
               password : str = "",
               encryption : str = None,
               delete_duplicates_destination : bool = False,
               delete_from_source : bool = False,
               delete_non_existing_destination : bool = False,
               automap : bool = True,
               skip_cross_duplicates : bool = False,
               active : bool = True,
               subscribe_all : bool = True,
               interval : int = 20,
               subfolder : str = None,
               max_age : int = 0,
               max_bytes_per_second : int = 0,
               timeout_remote : int = 600,
               timeout_local : int = 600,
               exclude : str = None,
               custom_params : str = None):
        
        logger = logging.getLogger(__name__)
        
        if not mailbox_id or '@' not in mailbox_id:
            logger.error(f"Invalid mailbox ID {mailbox_id}")
            logger.error(f"Mailbox ID must be a valid email address (example: mailbox@domain.tld)")
            return
        
        if not host or not re.match(Syncjob.RE_HOSTNAME, host) and not re.match(Syncjob.RE_IPV4, host) and not re.match(Syncjob.RE_IPV6, host):
            logger.error(f"Invalid host {host} for mailbox {mailbox_id}")
            logger.error(f"Host must be a valid hostname or IP address (examples: imap.example.com, example.com, imap.mail.example.com, 192.168.1.1)")
            return
        
        logger.debug(f"Creating sync job for mailbox {mailbox_id}@{host}")
        
        if port < 1 or port > 65535:
            logger.error(f"Invalid port {port} for mailbox {mailbox_id}")
            logger.error(f"Port must be a valid port number (examples: 993, 143, 25, 587, 465)")
            return
        
        if not user:
            logger.error(f"Invalid username {user} for mailbox {mailbox_id}")
            logger.error(f"User must be a valid username (example: username or username@domain.tld)")
            return
        
        if not password or len(password) == 0:
            logger.error(f"Invalid password for mailbox {mailbox_id}")
            logger.error(f"Password must be a valid password (example: supersecret)")
            return
        
        if not encryption:
            # try to determine the encryption method from the port
            if port == 993:
                logger.info(f"Determined encryption method SSL for mailbox {mailbox_id}")
                encryption = "SSL"
            elif port == 587:
                logger.info(f"Determined encryption method TLS for mailbox {mailbox_id}")
                encryption = "TLS"
            elif port == 143:
                logger.info(f"Determined encryption method PLAIN for mailbox {mailbox_id}")
                encryption = "PLAIN"
            else:
                logger.error(f"Could not determine encryption method for port {port}, please specify the encryption method")
                return
            
        if encryption not in ["SSL", "TLS", "PLAIN"]:
            logger.error(f"Invalid encryption {encryption} for mailbox {mailbox_id}")
            logger.error(f"Encryption must be a valid encryption method (Allowed: SSL, TLS, PLAIN)")
            return
        
        if interval < 1:
            logger.error(f"Invalid interval {interval} for mailbox {mailbox_id}")
            logger.error(f"Interval must be a valid interval number (Example: 20)")
            return
        
        if max_age < 0:
            logger.error(f"Invalid max age {max_age} for mailbox {mailbox_id}")
            logger.error(f"Max age must be a valid max age number (Allowed: 0 (no limit), or any positive number)")
            return
        
        if max_bytes_per_second < 0:
            logger.error(f"Invalid max bytes per second {max_bytes_per_second} for mailbox {mailbox_id}")
            logger.error(f"Max bytes per second must be a valid max bytes per second number (Allowed: 0 (no limit), or any positive number)")
            return
        
        if timeout_remote < 1:
            logger.error(f"Invalid timeout remote {timeout_remote} for mailbox {mailbox_id}")
            logger.error(f"Timeout remote must be a valid timeout remote number (Allowed: 1 (no limit), or any positive number)")
            return
        
        if timeout_local < 1:
            logger.error(f"Invalid timeout local {timeout_local} for mailbox {mailbox_id}")
            logger.error(f"Timeout local must be a valid timeout local number (Allowed: 1 (no limit), or any positive number)")
            return
        
        if exclude:
            try:
                re.compile(exclude)
            except Exception as e:
                logger.error(f"Invalid exclude {exclude} for mailbox {mailbox_id}")
                logger.error(f"Exclude must be a valid regex filter (example: (?i)spam|(?i)junk)")
                return
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/add/syncjob"
        
        data = {
            "username": mailbox_id,
            "delete2duplicates": "1" if delete_duplicates_destination else "0",
            "delete1": "1" if delete_from_source else "0",
            "delete2": "1" if delete_non_existing_destination else "0",
            "automap": "1" if automap else "0",
            "skipcrossduplicates": "1" if skip_cross_duplicates else "0",
            "active": "1" if active else "0",
            "subscribeall": "1" if subscribe_all else "0",
            "host1": host,
            "port1": port,
            "user1": user,
            "password1": password,
            "enc1": encryption,
            "mins_interval": interval,
            "subfolder2": subfolder,
            "maxage": max_age,
            "maxbytespersecond": max_bytes_per_second,
            "timeout1": timeout_remote,
            "timeout2": timeout_local,
            "exclude": exclude if exclude else "",
            "custom_params": custom_params if custom_params else ""
        }
        
        response = requests.post(endpoint, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, verify=validate_certificate, allow_redirects=False, json=data)
        
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"[{response.status_code}] Failed to create sync job! Response is not valid JSON.")
            logger.error(f"Response: {response.text}")
            logger.error(f"Data sent: {data}")
            return
        
        if response.status_code > 299 or ('type' in data and data['type'] == 'error'):
            logger.error(f"[{response.status_code}] Failed to create sync job: {data['msg']}")
            return
        
        logger.info(f"[{response.status_code}] Sync job created successfully")
        
        return data
    
    """
    Create a sync job from a CSV file
    Path: POST /api/v1/add/syncjob
    
    @param path_to_csv: The path to the CSV file
    @param has_headers: Whether the CSV file has headers (default: True)
    @param username_with_domain: Whether the username has the domain (default: True)
    @param host: The host of the source mailbox (example: imap.example.com)
    @param port: The port of the source mailbox (default: 993)
    @param encryption: The encryption method of the source mailbox (allowed: SSL, TLS, PLAIN)
    @param delimeter: The delimeter of the CSV file (default: ",")
    @param delete_duplicates_destination: Whether to delete duplicates in the destination mailbox (default: False)
    @param delete_from_source: Whether to delete messages from the source mailbox (default: False)
    @param delete_non_existing_destination: Whether to delete messages from the destination mailbox that do not exist in the source mailbox (default: False)
    @param automap: Whether to automap the mailbox (default: True)
    @param skip_cross_duplicates: Whether to skip cross duplicates (default: False)
    @param active: Whether the sync job is active (default: True)
    @param subscribe_all: Whether to subscribe to all messages (default: True)
    @param interval: The interval of the sync job in minutes (default: 20)
    @param subfolder: The subfolder of the source mailbox (default: "")
    @param max_age: The max age of the sync job in days (default: 0, 0 means no limit)
    @param max_bytes_per_second: The max bytes per second of the sync job (default: 0, 0 means no limit)
    @param timeout_remote: The timeout of the remote mailbox in seconds (default: 600)
    @param timeout_local: The timeout of the local mailbox in seconds (default: 600)
    @param exclude: The exclude regex filter of the sync job (default: "")
    @param custom_params: The custom params of the sync job (default: "")
    """
    @staticmethod
    def create_batch(path_to_csv : str, has_headers : bool = True, username_with_domain : bool = True, host : str = "", port : int = 993, encryption : str = None, delimeter : str = ",", delete_duplicates_destination : bool = False, delete_from_source : bool = False, delete_non_existing_destination : bool = False, automap : bool = True, skip_cross_duplicates : bool = False, active : bool = True, subscribe_all : bool = True, interval : int = 20, subfolder : str = None, max_age : int = 0, max_bytes_per_second : int = 0, timeout_remote : int = 600, timeout_local : int = 600, exclude : str = None, custom_params : str = None):
        logger = logging.getLogger(__name__)
        
        if not os.path.exists(path_to_csv):
            logger.error(f"File {path_to_csv} does not exist")
            return
        
        with open(path_to_csv, "r") as file:
            reader = csv.reader(file, delimiter=delimeter)
            
            if has_headers:
                next(reader)
            
            for row in reader:
                mailbox_id = row[0]
                username = mailbox_id if username_with_domain else mailbox_id.split('@')[0]
                password = row[2]
                
                Syncjob.create(mailbox_id, host, port, username, password, encryption, delete_duplicates_destination, delete_from_source, delete_non_existing_destination, automap, skip_cross_duplicates, active, subscribe_all, interval, subfolder, max_age, max_bytes_per_second, timeout_remote, timeout_local, exclude, custom_params)
    
    """
    Update a sync job
    Path: POST /api/v1/edit/syncjob
    """
    @staticmethod
    def update():
        logger = logging.getLogger(__name__)
        logger.warning("Update a sync job is not implemented yet")
        pass
    
    """
    Delete a sync job
    Path: POST /api/v1/delete/syncjob
    """
    @staticmethod
    def delete():
        logger = logging.getLogger(__name__)
        logger.warning("Delete a sync job is not implemented yet")
        pass
    
    """
    Disable a sync job
    Path: -
    """
    @staticmethod
    def disable(syncjob_id : str):
        logger = logging.getLogger(__name__)
        logger.warning("Disable a sync job is not implemented yet")
        pass
    
    """
    Enable a sync job
    Path: -
    """
    @staticmethod
    def enable(syncjob_id : str):
        logger = logging.getLogger(__name__)
        logger.warning("Enable a sync job is not implemented yet")
        pass
    
    def print_help(self):
        logger = logging.getLogger(__name__)
        logger.info("Available commands for mailbox module:")
        logger.info("  list: List all sync jobs")
        logger.info("  create <mailbox_id(str)> [host(str)] [port(int)] [user(str)] [password(str)] [encryption(SSL|TLS|PLAIN)] [delete_duplicates_destination(true|false)] [delete_from_source(true|false)] [delete_non_existing_destination(true|false)] [automap(true|false)] [skip_cross_duplicates(true|false)] [active(true|false)] [subscribe_all(true|false)] [interval(int)] [subfolder(str)] [max_age(int)] [max_bytes_per_second(int)] [timeout_remote(int)] [timeout_local(int)] [exclude(str)] [custom_params(str)]: Create a new sync job")
        logger.info("  create_batch <path_to_csv(str)> [has_headers(true|false)] [username_with_domain(true|false)] [host(str)] [port(int)] [encryption(SSL|TLS|PLAIN)] [delimeter(str)] [delete_duplicates_destination(true|false)] [delete_from_source(true|false)] [delete_non_existing_destination(true|false)] [automap(true|false)] [skip_cross_duplicates(true|false)] [active(true|false)] [subscribe_all(true|false)] [interval(int)] [subfolder(str)] [max_age(int)] [max_bytes_per_second(int)] [timeout_remote(int)] [timeout_local(int)] [exclude(str)] [custom_params(str)]: Create a new sync job from a CSV file")
        logger.info("  update: Update a sync job")
        logger.info("  delete: Delete a sync job")
        logger.info("  disable <syncjob_id(str)>: Disable a sync job")
        logger.info("  enable <syncjob_id(str)>: Enable a sync job")

    def print_commands(self):
        print("list create create_batch update delete disable enable")

def __getattr__(name):
    return Syncjob
