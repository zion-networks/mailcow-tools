import logging
import os
import json
import requests
from typing import List
from modules.module import Module
from config import get_use_https

class Alias(Module):
    def __init__(self):
        super().__init__("alias")
    
    """
    List all aliases

    Path: GET /api/v1/get/alias/all
    """
    @staticmethod
    def list(no_print : bool = False):
        logger = logging.getLogger(__name__)
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/get/alias/all"
        
        response = requests.get(endpoint, headers={"X-API-Key": api_key}, verify=validate_certificate)
        
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response content: {response.content}")
        
        if response.status_code > 299 or ('type' in response.json() and response.json()['type'] == 'error'):
            logger.error(f"[{response.status_code}] Failed to list aliases: {response.json()['msg']}")
            return
        
        data = response.json()
        if len(data) == 0 and not no_print:
            logger.warning(f"[{response.status_code}] No aliases found")
            return
        
        if not no_print:
            logger.info(f"[{response.status_code}] Found {len(data)} aliases:")
        
        if not no_print:
            for alias in data:
                is_active = True if alias['active'] == 1 else False
                
                if is_active:
                    logger.info(f"  - ✅ {alias['address']} => {alias['goto']}")
                else:
                    logger.info(f"  - 🚫 {alias['address']} => {alias['goto']}")

        return data
    
    """
    Create an alias for a mailbox

    Path: POST /api/v1/add/alias

    @param mailbox_id: The mailbox ID
    @param goto_mailbox_ids: The mailbox IDs to forward to
    @param ignore: Whether to ignore the alias (default: False)
    @param learn_spam: Whether to learn spam (default: False)
    @param learn_ham: Whether to learn ham (default: False)
    @param active: Whether the alias is active (default: True)

    @return: The alias data
    """
    @staticmethod
    def create(mailbox_id : str, goto_mailbox_ids : List[str], ignore : bool = False, learn_spam : bool = False, learn_ham : bool = False, active : bool = True):
        from modules.mailbox import Mailbox
        
        logger = logging.getLogger(__name__)
        
        mailcow_host = os.getenv("MAILCOW_TOOLS_MAILCOW_HOST")
        api_key = os.getenv("MAILCOW_TOOLS_MAILCOW_API_KEY")
        validate_certificate = True if os.getenv("MAILCOW_TOOLS_VALIDATE_CERTIFICATE") == "true" else False
        endpoint = f"{('https' if get_use_https() else 'http')}://{mailcow_host}/api/v1/add/alias"
        
        if not Mailbox.validate_mailbox_id(mailbox_id, no_print=True):
            logger.error(f"Invalid mailbox ID: {mailbox_id}")
            return
        
        if not goto_mailbox_ids or len(goto_mailbox_ids) == 0:
            logger.error(f"No goto mailbox IDs provided for alias {mailbox_id}")
            return
        
        if learn_spam and learn_ham:
            logger.error("Cannot learn spam and ham at the same time")
            return
        
        if ignore and (learn_spam or learn_ham):
            logger.error("Cannot ignore and learn spam or ham at the same time")
            return
        
        for goto_mailbox_id in goto_mailbox_ids:
            if not Mailbox.validate_mailbox_id(goto_mailbox_id, no_print=True):
                logger.warning(f"Goto mailbox ID {goto_mailbox_id} is not a valid email address, skipping alias")
                continue
        
        post_data = {
            "address": mailbox_id,
            "goto": ",".join(goto_mailbox_ids),
            "goto_null": "1" if ignore else "0",
            "goto_spam": "1" if learn_spam else "0",
            "goto_ham": "1" if learn_ham else "0",
            "active": "1" if active else "0"
        }
        
        post_data_json = json.dumps(post_data)
        
        logger.debug(f"Post data being sent: {post_data_json}")
        
        response = requests.post(endpoint, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, verify=validate_certificate, data=post_data_json, allow_redirects=False)
        
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response content: {response.content}")
        
        data = response.json()
        
        if response.status_code > 299 or ('type' in data and data['type'] == 'error'):
            logger.error(f"[{response.status_code}] Failed to create alias: {data['msg']}")
            return

        logger.info(f"[{response.status_code}] Alias created successfully for {mailbox_id}")
        
        return data
    
    def print_help(self):
        logger = logging.getLogger(__name__)
        logger.info("Available commands for alias module:")
        logger.info("  list: List all aliases")
        logger.info("  create <mailbox_id(str)> <goto_mailbox_ids(str)> [ignore(true|false)] [learn_spam(true|false)] [learn_ham(true|false)] [active(true|false)]: Create an alias")

    def print_commands(self):
        print("list create")

def __getattr__(name):
    return Alias