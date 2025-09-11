# TOSCA in Swarmchestrate

This repository is home to TOSCA in the [Swarmchestrate](https://www.swarmchestrate.eu/) project, which will use TOSCA v2.0 to describe applications and capacities managed in a Swarmchestrate Universe.

Any `.yaml` files committed to the `templates/` directory will be validated on pushes or pull requests by [Puccini](https://github.com/tliron/puccini), using a GitHub Action.

## Devs

It is recommended that developers open a GitHub Codespace on this repository, which includes dependencies and a Makefile for running Puccini manually. Simply drop a TOSCA service template into the `templates/` directory and run `make parse`. 

## TOSCA Template Validation with Puccini

This is an added feature that provides a Python validation library and script to check whether TOSCA service templates are valid using the [Puccini](https://github.com/tliron/puccini) parser.

#### Prerequisites
- Python 3.8+
- Puccini CLI
  
Install Puccini CLI on Linux by:
- `wget https://github.com/tliron/puccini/releases/download/v0.22.6/puccini_0.22.6_linux_amd64.deb`
- `sudo dpkg -i puccini_0.22.6_linux_amd64.deb || sudo apt --fix-broken install -y`
- `rm -f puccini_0.22.6_linux_amd64.deb`

##### Validation Library (`validation.py `)
- A library that defines the `validate_template()` function to validate a single TOSCA YAML file.
- Returns `True` if the template is valid, `False` if not.

##### Validation Script (`run_validation.py`)
- A script that searches the `templates/` folder and validates all `.yaml` files in one run.
- Prints total successes/failures and exits with code `1` if any file fails.
  
Run:
- `python3 run_validation.py`

#### When to Use What
- Use `validation.py` when you want to integrate validation inside another Python project.
  - Import it in your code with: `from validation import validate_template`
- Use `run_validation.py` when you want batch validation of all templates.

## Contact

Contact Jay at Westminster for support with TOSCA and/or this repository.
