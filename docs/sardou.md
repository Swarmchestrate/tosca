# Sardou TOSCA Library

This page is primarily for developers building tooling around TOSCA.
Sardou is the Swarmchestrate TOSCA toolkit, which validates, extracts
and translate various information from a Swarmchestrate TOSCA template.

## Quickstart

Install [Puccini](https://github.com/tliron/go-puccini/).

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

### System Requirements

* Python 3.12
* Minimum GLIBC 2.34 (Ubuntu 22.04 or higher)

### Puccini

[Puccini](https://github.com/tliron/go-puccini) provides a TOSCA Parser, which
Swarmchestrate uses to validate templates and complete the representation graph.
It must be installed before using Sardou.

Prefer the latest (currently unreleased) version. Build from source from
[Go-Puccini](https://github.com/tliron/go-puccini) or use the prebuilts attached to
[this Sardou release](https://github.com/Swarmchestrate/tosca/releases/tag/v0.2.4).

??? note "Rust Puccini"

	Puccini is being [re-written in Rust](https://github.com/tliron/puccini). Until its release, we are using the
	Go version of Puccini, 0.22.x
  
You can install the recommended Puccini on Linux with:
```sh
wget https://github.com/Swarmchestrate/tosca/releases/download/v0.2.4/go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb
sudo dpkg -i go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb || sudo apt --fix-broken install -y
```


### Sardou

You may then install Sardou from PyPi using `uv` or `pip`.

=== "uv"

	```bash
	uv add Sardou
	```


=== "pip"

	```bash
	pip install Sardou
	```

## Command-line Usage

The Sardou CLI currently only performs validation. Run it against
any SAT or CDT. If *processed succesfully*, the template is valid.

```bash
sardou templates/BookInfo.yaml
```

## Library Usage

Import the Sardou TOSCA Library

```python
from sardou import Sardou # note the uppercase S
```

### Validation

To validate a TOSCA template, create a new `Sardou` object, passing it an SAT or CDT.
This will validate the template and complete the representation, inheriting from parent
types.

```python
>>> sat = Sardou("my_app.yaml")
Processed successfully: my_app.yaml

>>> sat
{'description': 'stressng on Swarmchestrate', 'nodeTemplates': {'resource-1': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::EC2.micro.t3': {'description': 'An EC2 compute node from the University of Westminster provision\n', 'parent': 'eu.swarmchestrate:0.1::Resource'} ...
```

The template is not resolved at this point (i.e. statisfied requirements and created
relationships) - that functionality is to come. If there are errors or warnings, they
will be presented at this time.

#### Exploring the Template

Get the raw, uncompleted (original YAML) with the `raw` attribute.

```python
>>> sat.raw
{'tosca_definitions_version': 'tosca_2_0', 'description': 'stressng on Swarmchestrate', 'imports': [{'namespace': 'swch' ...
```

You can traverse YAML maps using dot notation if needed (which leads to some unexpected behaviour,
so this may not be a long-term feature):

```python
>>> sat.nodeTemplates
{'resource-1': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::EC2.micro.t3' ...
```

### Applications

!!! warning

	The functionality described here only works on Swarm Application Templates.


#### Quality of Service Policies

Grab the QoS requirements as a Python object with `get_qos()`
You could dump this to JSON or YAML.

```python
>>> sat.get_qos()
[{'energy': {'type': 'swch:QoS.Energy.Budget', 'properties': {'priority': 0.3, 'target': 10}}}...
```

#### Resource Requirements

Grab the Resource requirements as a Python object with `get_requirements()`
You could dump this to JSON or YAML.

```python
>>> sat.get_requirements()
{'worker-node': {'metadata': {'created_by': 'floria-tosca-lib', 'created_at': '2025-09-16T14:51:24Z', 'description': 'Generated from node worker-node', 'version': '1.0'}, 'capabilities': {'host': {'properties': {'num-cpus': {'$greater_than': 4}, 'mem-size': {'$greater_than': '8 GB'}}}, ...
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

### Capacities

You can create a Sardou object from a CDT with the same approach as for SATs.

```python
>>> cdt = Sardou("my_cap.yaml")
Processed successfully: my_cap.yaml
```

!!! warning

	The below methods only work on Capacity Description Templates.

#### Capacity Details

Given a CDT, Sardou can extract the capability details of each available flavour,
as well as the [overall capacity](cdt.md#cdt-overall-capacity), if defined.

```python
>>> cdt.get_capacities()
t.get_capacities()
({'m2-medium-sztaki': {'capacity': {'instances': 4}, 'energy': {'consumption': 0.1, 'energy-type': 'non-green', 'powered-type': 'mains-powered'}, 'host': {'bandwidth': '1000', 'disk-size': '20', 'mem-size': '8 GB', 'num-cpus': 4},
```

#### Resource Description Templates

You can generate a Resource Description Template (RDT) with a CDT and an
accepted offer. An RDT is an internal template used to pass deployment
configuration for the Swarm to the Cluster Builder component.

```python
>>> offer = json.load("ra-sztaki-offer.json")
>>> cdt.generate_rdt(selected_offer=offer, output_path="sztaki-rdt.yaml")
```

Which will generate an RDT at the given `output_path`.

### Resources

You can then create a new Sardou object from an RDT.

```python
>>> rdt = Sardou("sztaki-rdt.yaml")
Processed successfully: sztaki-rdt.yaml
```

!!! warning

	This method only works on Resource Description Templates.


#### Cluster Configuration Details

Get the cluster configuration details for the resources as a Python object with `get_cluster()`
You could dump this to JSON or YAML.

```python
>>> rdt.get_cluster()
{'resource-1': {'image_id': 'ami-0c02fb291006c7d929', 'instance_type': 't3.micro', 'key_name': 'mykey', 'region_name': 'us-east-1' ...
```

