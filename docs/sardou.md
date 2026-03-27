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

## Usage

### Command-line

A basic CLI is available to perform only validation. Run it against
any template. If *processed succesfully*, the template is valid.

```bash
sardou templates/BookInfo.yaml
```

### Library

For all other uses, import the Sardou TOSCA Library. For further info
on working with the Library, visit the [next page](sardou_lib.md) in this section.

```python
from sardou import Sardou
```
