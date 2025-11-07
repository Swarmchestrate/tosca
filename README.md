# TOSCA in Swarmchestrate

This repository is home to TOSCA in the [Swarmchestrate](https://www.swarmchestrate.eu/) project, which will use TOSCA v2.0 to describe applications and capacities managed in a Swarmchestrate Universe.


## Sardou TOSCA Library

Sardou validates and extracts info from a Swarmchestrate TOSCA template.

### Prerequisites
- Python 3.11+
- Puccini: Should work with any 0.22.x version, but prefer the latest (currently unreleased) version. Build from source from [Go-Puccini](https://github.com/tliron/go-puccini) or use the prebuilts attached to [this release](https://github.com/Swarmchestrate/tosca/releases/tag/v0.2.4) in this repository
  - Minimum GLIBC 2.34 (Ubuntu 22.04 or higher)
  
Install Puccini on Linux by:
```sh
wget https://github.com/Swarmchestrate/tosca/releases/download/v0.2.4/go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb
sudo dpkg -i go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb || sudo apt --fix-broken install -y
```

### Installation

Install using the PyPi package

```bash
pip install Sardou
```

### Usage

Import the Sardou TOSCA Library

```python
from sardou import Sardou # note the uppercase S
```

Create a new `Sardou` object, passing it the path to your Swarmchestrate TOSCA template.
This will validate the template and complete the representation, inheriting from parent
types.

```python
>>> tosca = Sardou("my_app.yaml")
Processed successfully: my_app.yaml

>>> tosca
{'description': 'stressng on Swarmchestrate', 'nodeTemplates': {'resource-1': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::EC2.micro.t3': {'description': 'An EC2 compute node from the University of Westminster provision\n', 'parent': 'eu.swarmchestrate:0.1::Resource'} ...
```

The template is not resolved at this point (i.e. statisfied requirements and created
relationships) - that functionality to come. If there are errors or warnings, they will be
presented at this time.

Get the raw, uncompleted (original YAML) with the `raw` attribute.

```python
>>> tosca.raw
{'tosca_definitions_version': 'tosca_2_0', 'description': 'stressng on Swarmchestrate', 'imports': [{'namespace': 'swch' ...
```

Grab the QoS requirements as a Python object with `get_qos()`
You could dump this to JSON or YAML.

```python
>>> tosca.get_qos()
[{'energy': {'type': 'swch:QoS.Energy.Budget', 'properties': {'priority': 0.3, 'target': 10}}}...
```

Grab the Resource requirements as a Python object with `get_requirements()`
You could dump this to JSON or YAML.

```python
>>> tosca.get_requirements()
{'worker-node': {'metadata': {'created_by': 'floria-tosca-lib', 'created_at': '2025-09-16T14:51:24Z', 'description': 'Generated from node worker-node', 'version': '1.0'}, 'capabilities': {'host': {'properties': {'num-cpus': {'$greater_than': 4}, 'mem-size': {'$greater_than': '8 GB'}}}, ...
```

Get the specification of the resources as a Python object with `get_cluster()`
You could dump this to JSON or YAML.

```python
>>> tosca.get_cluster()
{'resource-1': {'image_id': 'ami-0c02fb291006c7d929', 'instance_type': 't3.micro', 'key_name': 'mykey', 'region_name': 'us-east-1' ...
```

You can traverse YAML maps using dot notation if needed (which leads to some unexpected behaviour,
so this may not be a long-term feature)

```python
>>> tosca.nodeTemplates
{'resource-1': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::EC2.micro.t3' ...
```

## Devs

It is recommended that developers open a GitHub Codespace on this repository, which includes dependencies and a Makefile for running Puccini manually.

## TOSCA Template Validation with Puccini

This is an added feature that provides a Python validation library and script to check whether TOSCA service templates are valid using the [Go-Puccini](https://github.com/tliron/go-puccini) parser.

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
