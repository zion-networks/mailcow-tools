# Mailcow Tools

> [!NOTE]
> Mailcow Tools is still in very early development. A lot of features are still missing and the code structure is not final at all.

[Mailcow]([https://](https://mailcow.email/)) is a great option to run your very own mailserver. It comes with tons of features and one of them is the [REST API](https://mailcow.docs.apiary.io). The API is the counterpart of this tool.

Mailcow Tools allows you to manage any Mailcow instance right from the terminal. But it does not just map the REST routes to commands - it also comes with some handy additions, like batch creation of mailboxes.

### Getting started

1. Clone this repository: `git clone git@github.com:zion-networks/mailcow-tools.git`
2. Move to the directory: `cd mailcow-tools`
3. Make it a venv: `python3 -m venv .`
4. Activate the venv: `source bin/activate`
5. Install the required packages `pip install -r requirements.txt`
6. (Optional) Enable bash autocompletion: `source bash_autocomplete.sh`
7. Use it: `./mailcow-tools.sh help`

The `help` command will list you all available modules. Using `./mailcow-tools.sh help <module>` you can also see the help for a specific module.