# TOSCA in Swarmchestrate

This repository is home to TOSCA in the [Swarmchestrate](https://www.swarmchestrate.eu/) project, which will use TOSCA v2.0 to describe applications and capacities managed in a Swarmchestrate Universe.


## Floria TOSCA Library

Floria validates and extracts info from a Swarmchestrate TOSCA template.

### Prerequisites
- Python 3.10+
- [Puccini](https://github.com/tliron/puccini)
  - Minimum GLIBC 2.34 (Ubuntu 22.04 or higher)
  
Install Puccini on Linux by:
```sh
wget https://github.com/tliron/puccini/releases/download/v0.22.7/puccini_0.22.7_linux_amd64.deb
sudo dpkg -i puccini_0.22.7_linux_amd64.deb || sudo apt --fix-broken install -y
rm -f puccini_0.22.7_linux_amd64.deb
```

### Installation

Install using `pip` pointed at this GitHub repo. PyPI package coming soon.

```bash
pip install git+https://github.com/Swarmchestrate/tosca.git
```

### Usage

Import the Floria TOSCA Library

```python
from floria import Floria # note the uppercase F
```

Create a new `Floria` object, passing it the path to your Swarmchestrate TOSCA template.
This will validate the template. If there are errors or warnings, they will be presented here.

```python
>>> tosca = Floria("my_app.yaml")
Processed successfully: my_app.yaml 
```

Grab the QoS requirements as a Python object.
You could wrap this as a dictionary and dump to JSON or YAML.

```python
>>> tosca.get_qos()
[{'energy': {'type': 'swch:QoS.Energy.Budget', 'properties': {'priority': 0.3, 'target': 10}}}...
```

Grab the Resource requirements as a Python object.
You could dump this to JSON or YAML.

```python
>>> tosca.get_requirements()
{'worker-node': {'metadata': {'created_by': 'floria-tosca-lib', 'created_at': '2025-09-16T14:51:24Z', 'description': 'Generated from node worker-node', 'version': '1.0'}, 'capabilities': {'host': {'properties': {'num-cpus': {'$greater_than': 4}, 'mem-size': {'$greater_than': '8 GB'}}}, ...
```

You can traverse YAML maps using dot notation if needed.

```python
>>> tosca.service_template.node_templates
{'swarm': {'type': 'swch:Swarm', 'directives': ['substitute']}, ...
```

## Devs

It is recommended that developers open a GitHub Codespace on this repository, which includes dependencies and a Makefile for running Puccini manually.

## TOSCA Template Validation with Puccini

This is an added feature that provides a Python validation library and script to check whether TOSCA service templates are valid using the [Puccini](https://github.com/tliron/puccini) parser.

##### Validation Library (`lib/validation.py `)
- A library that defines the `validate_template()` function to validate a single TOSCA YAML file.
- Returns `True` if the template is valid, `False` if not.

##### Validation Script (`run_validation.py`)
- A script that searches the `templates/` folder and validates all `.yaml` files in one run.
- Prints total successes/failures and exits with code `1` if any file fails.
  
Run:
- `python3 run_validation.py`


## Contact

Contact Jay at Westminster for support with TOSCA and/or this repository.
