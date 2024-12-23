#! /bin/bash

__MAILCOW_TOOLS_PATH=$(which mailcow-tools)

if [ -z "$__MAILCOW_TOOLS_PATH" ]; then
    echo "Global mailcow-tools not found, checking local mailcow-tools"

    VENV_NAME=$(basename $(pwd))
    if [ -f "./main.py" ] && [ "${VENV_NAME}" == "mailcow-tools" ]; then
        echo "Using local mailcow-tools"
        __MAILCOW_TOOLS_PATH="python3 ./main.py"
    else
        echo "mailcow-tools not found"
        exit 1
    fi
fi

__MAILCOW_TOOLS_MODULE_NAMES=($($__MAILCOW_TOOLS_PATH "__autocomplete__modules"))

declare -A __MAILCOW_TOOLS_MODULES

for module_name in ${__MAILCOW_TOOLS_MODULE_NAMES[@]}; do
    __MODULE_COMMANDS=$($__MAILCOW_TOOLS_PATH "__autocomplete__commands" "${module_name}")
    __MAILCOW_TOOLS_MODULES["${module_name}"]="${__MODULE_COMMANDS}"
done

# Enable autocompletion for the mailcow-tools command
_mailcow_tools_autocomplete() {
    local cur prev opts
    COMPREPLY=()
    
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local autocomplete_module=false
    local autocomplete_command=false

    # If the previous word is "mailcow-tools" or "./mailcow-tools", suggest modules
    # If the previous word is a module, suggest commands for that module
    if [[ ${prev} == "mailcow-tools" || ${prev} == "./mailcow-tools" ]]; then
        autocomplete_module=true
    else
        # Check if the previous word is a valid module
        if [[ -n ${__MAILCOW_TOOLS_MODULES[${prev}]} ]]; then
            autocomplete_command=true
        else
            # If the previous word is not a valid module, do not autocomplete
            return 1
        fi
    fi

    # If the previous word is "mailcow-tools" or "./mailcow-tools", suggest modules
    # when cur starts with a module name
    if [[ ${autocomplete_module} == true ]]; then
        
        # If the length of cur is 0, show all modules
        if [[ ${#cur} -eq 0 ]]; then
            COMPREPLY=(${__MAILCOW_TOOLS_MODULE_NAMES[@]})
            return 0
        fi

        COMPREPLY=($(compgen -W "${__MAILCOW_TOOLS_MODULE_NAMES[*]}" -- ${cur}))
    fi

    # If the previous word is a module, suggest commands for that module
    # When a command starts with cur, suggest the command
    # Do not suggest a command if no valid module is found before the command
    if [[ ${autocomplete_command} == true ]]; then
        local module_commands=(${__MAILCOW_TOOLS_MODULES[${prev}]})

        if [[ ${#cur} -eq 0 ]]; then
            COMPREPLY=(${module_commands[@]})
            return 0
        else
            COMPREPLY=($(compgen -W "${module_commands[*]}" -- ${cur}))
            return 0
        fi
    fi

    return 0
}

# Register the autocompletion function for mailcow-tools and ./mailcow-tools
complete -F _mailcow_tools_autocomplete mailcow-tools
complete -F _mailcow_tools_autocomplete ./mailcow-tools
