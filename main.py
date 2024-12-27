import os
import re
import sys
import importlib
import coloredlogs, logging
import requests
import typing
from dotenv import load_dotenv

from config import USE_HTTPS

"""
Mailcow Tools is a tool for managing mailboxes and domains in Mailcow.
"""
class MailcowTools:
    """
    Main function to run the Mailcow Tools.
    """
    def main(self):
        if len(sys.argv) == 2 and sys.argv[1] == "__autocomplete__modules":
            self._print_modules()
            return
        
        if len(sys.argv) == 3 and sys.argv[1] == "__autocomplete__commands":
            self._print_commands(sys.argv[2])
            return
        
        load_dotenv()
        
        self.logger = self.init_logger()
        self.logger.info("Mailcow Tools v0.1.0 by Zion Networks UG")
        self.logger.info("----------------------------------------")
        self.logger.info("")
        self.logger.info("Mailcow Tools is a tool for managing Mailcow instances.")
        self.logger.info("Need support? Visit https://www.zion-networks.de/ or contact us at support@zion-networks.de")
        self.logger.info("")
        
        if len(sys.argv) == 1 or sys.argv[1] == "help":
            help_module = sys.argv[2] if len(sys.argv) > 2 else None
            
            if help_module:
                self.print_help(help_module)
            else:
                self.print_help()

            return
        
        self.MAILCOW_HOST = os.getenv("MAILCOW_HOST")
        self.MAILCOW_API_KEY = os.getenv("MAILCOW_API_KEY")
        self.VALIDATE_CERTIFICATE = True if os.getenv("VALIDATE_CERTIFICATE") == "true" else False
        
        # Remove the trailing slash from the mailcow host
        self.MAILCOW_HOST = self.MAILCOW_HOST.rstrip("/")
        
        # Remove leading and trailing whitespace from the mailcow host and API key
        self.MAILCOW_HOST = self.MAILCOW_HOST.strip()
        self.MAILCOW_API_KEY = self.MAILCOW_API_KEY.strip()
        
        self.check_environment()
        self.check_mailcow_host()
        
        # Parse arguments, but all of them are optional
        module = sys.argv[1] if len(sys.argv) > 1 else None
        command = sys.argv[2] if len(sys.argv) > 2 else None
        args = sys.argv[3:] if len(sys.argv) > 3 else []
        
        if not module:
            self.logger.error("Module is required")
            self.print_help()
            return
        
        if not self.exists_module(module):
            self.logger.error(f"Module {module} does not exist")
            self.print_help()
            return
        
        module_instance = self.load_module(module)
        
        if not command:
            self.logger.error("Command is required")
            module_instance.print_help()
            return
        
        # Command is a static method in the module class
        if not hasattr(module_instance, command):
            self.logger.error(f"Command {command} does not exist in module {module}")
            module_instance.print_help()
            return
        
        command_instance = getattr(module_instance, command)
        if not callable(command_instance):
            self.logger.error(f"Command {command} is not callable in module {module}")
            return
        
        self.logger.debug(f"Running command {command} in module {module}")
        args = self.prepare_args(command_instance, args)
        
        if args is None:
            return
        
        self.logger.debug(f"Calling command {command} with arguments {args}")
        response = command_instance(*args)
        
        if response and isinstance(response, str):
            for line in response.splitlines():
                self.logger.debug(f"[{module}.{command}] {line}")
        elif response and isinstance(response, dict):
            for key, value in response.items():
                self.logger.debug(f"[{module}.{command}] {key}: {value}")
        elif response and isinstance(response, list):
            for item in response:
                self.logger.debug(f"[{module}.{command}] {item}")
        else:
            self.logger.debug(f"[{module}.{command}] {response}")

    def prepare_args(self, command_instance : type, args : list) -> list|None:
        arg_count = command_instance.__code__.co_argcount
        arg_names = command_instance.__code__.co_varnames
        arg_defaults = command_instance.__defaults__
        arg_types = typing.get_type_hints(command_instance)
        
        args_required = []
        for i in range(arg_count):
            if arg_names[i] not in arg_defaults:
                args_required.append(arg_names[i])
        
        # check if at least the required arguments are present
        if len(args) < arg_count - (len(arg_defaults) if arg_defaults else 0):
            self.logger.error(f"Not enough arguments provided for command {command_instance.__name__}")
            self.logger.error(f"Required arguments: {args_required}")
            return None
        
        # try to convert the positional arguments to the correct type based on the type hints
        for i in range(len(args)):
            arg_name = arg_names[i]
            arg_value = args[i]
            arg_type = arg_types[arg_name]
            
            self.logger.debug(f"Expected type for {arg_name} with value {arg_value}: {arg_type}")
            
            if arg_type == bool:
                self.logger.debug(f"Converting argument {arg_name} with value {arg_value} to boolean")
                arg_value = arg_value.lower() == "true" or arg_value.lower() == "1" or arg_value.lower() == "yes" or arg_value.lower() == "y"
            elif arg_type == int:
                self.logger.debug(f"Converting argument {arg_name} with value {arg_value} to integer")
                arg_value = int(arg_value)
            elif arg_type == float:
                self.logger.debug(f"Converting argument {arg_name} with value {arg_value} to float")
                arg_value = float(arg_value)
            else:
                self.logger.debug(f"Argument {arg_name} with value {arg_value} remains unchanged ({arg_type})")
            
            args[i] = arg_value
        
        return args

    """
    Initialize logging.
    """
    def init_logger(self):
        self.LOG_LEVEL = os.getenv("MAILCOW_TOOLS_LOG_LEVEL")
        
        if self.LOG_LEVEL is None:
            self.LOG_LEVEL = "DEBUG"
        
        coloredlogs.install(level=self.LOG_LEVEL)
        logger = logging.getLogger('core')
        
        logger.info(f"Logging level set to {self.LOG_LEVEL}")
        
        return logger
    
    """
    Check if the environment variables are set.
    """
    def check_environment(self):
        self.logger.debug("Checking environment variables")
        
        if not self.MAILCOW_HOST:
            self.logger.error("MAILCOW_HOST is not set")
            sys.exit(1)
        
        if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$", self.MAILCOW_HOST):
            self.logger.error(f"MAILCOW_HOST is not a valid domain: {self.MAILCOW_HOST}")
            sys.exit(1)
            
        response = os.system(f"ping -c 1 {self.MAILCOW_HOST} > /dev/null 2>&1")
        if response != 0:
            self.logger.error(f"MAILCOW_HOST is not reachable at {self.MAILCOW_HOST}")
            sys.exit(1)
        
        self.logger.debug(f"MAILCOW_HOST: {self.MAILCOW_HOST}")
        
        if not self.MAILCOW_API_KEY:
            self.logger.error("MAILCOW_API_KEY is not set")
            sys.exit(1)
        
        if not re.match(r"^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$", self.MAILCOW_API_KEY):
            self.logger.error(f"MAILCOW_API_KEY is not a valid key: {self.MAILCOW_API_KEY}")
            sys.exit(1)
        
        self.logger.debug(f"MAILCOW_API_KEY: ******-******-******-******-{self.MAILCOW_API_KEY[-6:]}")

    """
    Check if the mailcow host is reachable and a valid Mailcow API is available.
    """
    def check_mailcow_host(self):
        global USE_HTTPS
        
        self.logger.debug(f"Checking mailcow host at {self.MAILCOW_HOST}")
        
        if not self.VALIDATE_CERTIFICATE:
            self.logger.warning("CERTIFICATE VALIDATION IS DISABLED")
            self.logger.warning("This is not recommended for production environments")
            requests.packages.urllib3.disable_warnings()
        
        # Disable following redirects
        response = requests.get(f"http://{self.MAILCOW_HOST}/", verify=self.VALIDATE_CERTIFICATE, allow_redirects=False)
        
        if response.status_code == 301 or response.status_code == 302:
            self.logger.debug(f"Mailcow host {self.MAILCOW_HOST} is redirecting to {response.headers['Location']}")
            
            if response.headers['Location'].startswith(f"https://{self.MAILCOW_HOST}"):
                self.logger.debug(f"Mailcow host {self.MAILCOW_HOST} is redirecting to HTTPS")
                USE_HTTPS = True
        elif response.status_code != 200:
            self.logger.error(f"Mailcow host {self.MAILCOW_HOST} is not reachable over HTTP")
            sys.exit(1)
        else:
            self.logger.debug(f"Mailcow host {self.MAILCOW_HOST} is reachable over HTTP")
            USE_HTTPS = False
        
        # When MailcowTools.USE_HTTPS is true, the http route probably redirects to https, so https is used
        if USE_HTTPS:
            response = requests.get(f"https://{self.MAILCOW_HOST}/", verify=self.VALIDATE_CERTIFICATE, allow_redirects=False)
            
            if response.status_code != 200:
                self.logger.error(f"Mailcow host {self.MAILCOW_HOST} is not reachable over HTTPS")
                sys.exit(1)
            else:
                self.logger.debug(f"Mailcow host {self.MAILCOW_HOST} is reachable over HTTPS")
        
        # When MailcowTools.USE_HTTPS is false, the http route is not redirecting to https, so https is used if possible, otherwise http is used
        else:
            response = requests.get(f"https://{self.MAILCOW_HOST}/", verify=self.VALIDATE_CERTIFICATE, allow_redirects=False)
            
            if response.status_code != 200:
                self.logger.warning(f"Mailcow host {self.MAILCOW_HOST} is not reachable over HTTPS")
                USE_HTTPS = False
            else:
                self.logger.debug(f"Mailcow host {self.MAILCOW_HOST} is also reachable over HTTPS")
                USE_HTTPS = True
        
        if USE_HTTPS:
            self.logger.debug(f"Using HTTPS for mailcow host {self.MAILCOW_HOST}")
        else:
            self.logger.debug(f"Using HTTP for mailcow host {self.MAILCOW_HOST}")
        
        # Validate the API key using the endpoint /api/v1/get/status/containers
        # Check HTTP status code of the mailcow host
        response = requests.get(f"{('https://' if USE_HTTPS else 'http://')}{self.MAILCOW_HOST}/api/v1/get/status/containers", headers={"X-API-Key": self.MAILCOW_API_KEY, "Content-Type": "application/json"}, verify=self.VALIDATE_CERTIFICATE, allow_redirects=False)
        data = response.json()
        if 'type' in data and data['type'] == 'error':
            self.logger.error(f"API key is invalid: {data['message']}")
            sys.exit(1)
        
        self.logger.debug(f"API key is valid")

    """
    Print help message.
    """
    def print_help(self, module : str|None = None):
        
        if not module:
            module_names = self.get_module_names(include_help=True)
            
            self.logger.info(f"Usage: python3 {os.path.basename(__file__)} <module> <command>")
            self.logger.info("")
            self.logger.info("General Commands:")
            self.logger.info("  help: Print this help message")
            self.logger.info("  help <module>: Print help message for a module")
            self.logger.info("")
            self.logger.info("Modules:")
            
            # TODO: Load module description from static function of the respective module class
            
            for module_name in module_names:
                self.logger.info(f"  {module_name}: ...")
            
            self.logger.info("")
            self.logger.info("Examples:")
            self.logger.info(f"  python3 {os.path.basename(__file__)} mailbox list - List all mailboxes")
            self.logger.info(f"  python3 {os.path.basename(__file__)} mailbox create contact@example.com - Create a new mailbox with default settings")
            self.logger.info(f"  python3 {os.path.basename(__file__)} mailbox delete contact@example.com - Delete a mailbox")
        
        else:
            if not self.exists_module(module):
                self.logger.error(f"Module {module} does not exist")
                self.print_help()
                return
            
            module_instance = self.load_module(module)()
            module_instance.print_help()

    """
    Check if a module exists.
    """
    def exists_module(self, module : str) -> bool:
        return os.path.exists(f"modules/{module}/")
    
    """
    Load a module from modules/<module>/__init__.py and return the class type.
    Each module implements the Module class from modules/module.py
    Each module has an __init__.py file that contains the Module class to be loaded
    """
    def load_module(self, module : str, instantiate : bool = True, no_print : bool = False):
        if not no_print:
            self.logger.debug(f"Loading modules/{module} ...")
        
        # Run __init__.py and call which is contained in the __init__.py file
        module_loader = importlib.import_module(f"modules.{module}")
        
        # Check if the module has a valid Module class
        if not hasattr(module_loader, module.capitalize()):
            if not no_print:
                self.logger.error(f"Module {module} does not have a valid class")
            return None
        
        # Set the USE_HTTPS value in the module
        from config import set_use_https
        set_use_https(USE_HTTPS)

        module_type = getattr(module_loader, module.capitalize())
        
        if instantiate:
            try:
                module_instance = module_type()
            except Exception as e:
                self.logger.error(f"Failed to create instance of module {module}: {e}")
                return None
        else:
            module_instance = module_type
        
        return module_instance
    
    """
    Get all module names.
    
    @return: List of module names
    """
    def get_module_names(self, include_help : bool = False) -> list[str]:
        module_folders = os.listdir(f"modules")
        
        module_names = []
        for folder in module_folders:
            # Append only those modules that have an __init__.py file with a class that is a subclass of Module
            if os.path.isdir(f"modules/{folder}") and os.path.isfile(f"modules/{folder}/__init__.py"):
                
                with open(f"modules/{folder}/__init__.py", "r") as file:
                    contents = file.read()
                    expected_class_name = "".join([part.capitalize() for part in folder.split("-")])
                    class_pattern = re.compile(f"class(.*){expected_class_name}(.*)(Module)(.*):")
                    
                    if class_pattern.search(contents):
                        module_names.append(folder)
        
        if include_help:
            module_names.append("help")
        
        return module_names
    
    """
    Internal function for bash autocomplete.
    """
    def _print_modules(self):
        module_names = self.get_module_names(include_help=True)
        print(" ".join(module_names))
    
    """
    Internal function for bash autocomplete.
    """
    def _print_commands(self, module : str):
        if module == "help":
            pass # help is a special command, so we don't need to print anything
        else:
            module_instance = self.load_module(module, no_print=True)
            module_instance.print_commands()

if __name__ == "__main__":
    mt = MailcowTools()
    mt.main()
