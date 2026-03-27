# TOSCA in Swarmchestrate

This repository is home to the [Swarmchestrate](https://www.swarmchestrate.eu/)
project documentation.

The [full documentation can be seen here](https://swarmchestrate.github.io/tosca/)
and this should be the first stop for anyone looking to deploy applications
with Swarmchestrate. There is some usual info for developers below.

## Sardou TOSCA Library

This repository also contains the source for the
[TOSCA](https://docs.oasis-open.org/tosca/TOSCA/v2.0/TOSCA-v2.0.html)
Toolkit in Swarmchestrate, named Sardou. Some info for developers is
available in this README.

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

> [!NOTE]
> **Rust Puccini**
>
> Puccini is being [re-written in Rust](https://github.com/tliron/puccini).
> Until its release, we are using the Go version of Puccini, 0.22.x

You can install the recommended Puccini on Linux with:
```sh
wget https://github.com/Swarmchestrate/tosca/releases/download/v0.2.4/go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb
sudo dpkg -i go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb || sudo apt --fix-broken install -y
```


### Sardou

You may then install Sardou from PyPi using `uv` (or `pip`).

```bash
# using uv
uv add Sardou
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
from sardou import Sardou
```

### Validation

To validate a TOSCA template, create a new `Sardou` object, passing it a file path,
or the template content directly as a [Python dict](https://swarmchestrate.github.io/tosca/sardou/#validation). This will validate the template and complete the representation, inheriting from parent types.

```python
# Pass a file path
>>> sat = Sardou("BookInfo.yaml")
Processed successfully: BookInfo.yaml

# Pass content directly as a Python dict
>>> sat = Sardou(content="tosca_definitions_version: tosca_2_0\n...")
Processed successfully

>>> sat
{'path': PosixPath('templates/BookInfo.yaml'), 'description': 'Istio Bookinfo as a Swarmchestrate SAT', 'nodeTemplates': {'details_v1': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::Kubernetes.APIObject': {'description': ...
```

The template is not resolved at this point (i.e. statisfied requirements and created
relationships) - that functionality is to come. If there are errors or warnings, they
will be presented at this time.

#### Exploring the Template

Get the raw, uncompleted (original YAML) with the `raw` attribute.

```python
>>> sat.raw
{'tosca_definitions_version': 'tosca_2_0', 'description': 'Istio Bookinfo as a Swarmchestrate SAT', 'metadata': {'name': 'bookinfo', 'author': 'you', ...
```

You can traverse YAML maps using dot notation if needed (which leads to some unexpected behaviour,
so this may not be a long-term feature):

```python
>>> sat.nodeTemplates
{'details_v1': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::Kubernetes.APIObject': {'description': 'Base type for Kubernetes API objects (persisted resources that can be created/applied on their own, e.g. Service, Deployment, ServiceAccount)...
```

## Going Further

The [rest of the developer docs can be found here](https://swarmchestrate.github.io/tosca/sardou/)

## Contact

Contact Jay at Westminster for support with TOSCA and/or this repository.
