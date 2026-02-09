# Sardou TOSCA Library

This page is primarily for developers building tooling around TOSCA.
Sardou is the Swarmchestrate TOSCA toolkit, which validates, extracts
and translate various information from a Swarmchestrate TOSCA template.

## Quickstart

Install Puccini:

```bash
wget https://github.com/Swarmchestrate/tosca/releases/download/v0.2.4/go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb
sudo dpkg -i go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb || sudo apt --fix-broken install -y
```

Install Sardou:

```bash
uv add sardou
```

Run the Sardou CLI to validate an SAT or CDT:

```bash
sardou templates/BookInfo.yaml
```

## Setup

### Prerequisites

* Python 3.12
* Minimum GLIBC 2.34 (Ubuntu 22.04 or higher)
* Puccini: Should work with any 0.22.x version, but prefer the latest (currently unreleased) version. Build from source from [Go-Puccini](https://github.com/tliron/go-puccini) or use the prebuilts attached to [this release](https://github.com/Swarmchestrate/tosca/releases/tag/v0.2.4) in this repository
  
You can install the recommended Puccini on Linux with:
```sh
wget https://github.com/Swarmchestrate/tosca/releases/download/v0.2.4/go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb
sudo dpkg -i go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb || sudo apt --fix-broken install -y
```

### Install

Install from PyPi using uv or pip

=== "uv"

	```bash
	uv add Sardou
	```


=== "pip"

	```bash
	pip install Sardou
	```

## Usage

### Command-line Interface

The Sardou CLI currently only performs validation. Run it against
any SAT or CDT. If processed succesfully, the template is valid.

```bash
sardou templates/BookInfo.yaml
```

### Library

Import the Sardou TOSCA Library

```python
from sardou import Sardou # note the uppercase S
```

#### Validation

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

### Exploring the Template

Get the raw, uncompleted (original YAML) with the `raw` attribute.

```python
>>> tosca.raw
{'tosca_definitions_version': 'tosca_2_0', 'description': 'stressng on Swarmchestrate', 'imports': [{'namespace': 'swch' ...
```

You can traverse YAML maps using dot notation if needed (which leads to some unexpected behaviour,
so this may not be a long-term feature)

```python
>>> tosca.nodeTemplates
{'resource-1': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::EC2.micro.t3' ...
```

### Capacities Detail

**NOTE** This only works on CDTs.

Grab capacity detail from a CDT using `get_capacities()`

```python
>>> tosca.get_capacities()
t.get_capacities()
({'m2-medium-sztaki': {'capacity': {'instances': 4}, 'energy': {'consumption': 0.1, 'energy-type': 'non-green', 'powered-type': 'mains-powered'}, 'host': {'bandwidth': '1000', 'disk-size': '20', 'mem-size': '8 GB', 'num-cpus': 4},
```

### Quality of Service Policies

Grab the QoS requirements as a Python object with `get_qos()`
You could dump this to JSON or YAML.

```python
>>> tosca.get_qos()
[{'energy': {'type': 'swch:QoS.Energy.Budget', 'properties': {'priority': 0.3, 'target': 10}}}...
```

### Resource Requirements

Grab the Resource requirements as a Python object with `get_requirements()`
You could dump this to JSON or YAML.

```python
>>> tosca.get_requirements()
{'worker-node': {'metadata': {'created_by': 'floria-tosca-lib', 'created_at': '2025-09-16T14:51:24Z', 'description': 'Generated from node worker-node', 'version': '1.0'}, 'capabilities': {'host': {'properties': {'num-cpus': {'$greater_than': 4}, 'mem-size': {'$greater_than': '8 GB'}}}, ...
```

### Cluster Configuration Details

Get the cluster configuration details for the resources as a Python object with `get_cluster()`
You could dump this to JSON or YAML.

```python
>>> tosca.get_cluster()
{'resource-1': {'image_id': 'ami-0c02fb291006c7d929', 'instance_type': 't3.micro', 'key_name': 'mykey', 'region_name': 'us-east-1' ...
```

### Kubernetes Manifests (manifestGenerator.py)

- Provides the function get_kubernetes_manifest(tosca_yaml: str, image_pull_secret: str = "test") -> list.
- **Purpose**: Converts a TOSCA YAML template into Kubernetes manifests (Deployments + Services).
- **Supported fields**: image, args, env, ports, volumes, nodeSelector, replicas, imagePullSecrets.
- Automatically injects an external imagePullSecret if provided.

**Input**:
- A valid TOSCA YAML template as a string. 
- Optional: name of an imagePullSecret to include in all generated Deployments.

**Output:**
- A list of dictionaries representing Kubernetes manifests ready to be serialized to YAML.

#### Manifest Generation Script (run_manifest_generator.py)
- Takes a single TOSCA YAML file and generates Kubernetes manifests as a multi-document YAML file (output.yaml).
- Usage: update the TOSCA_FILE and OUTPUT_FILE variables in the script and run:

```python
python3 run_manifest_generator.py
```