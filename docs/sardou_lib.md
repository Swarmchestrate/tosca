# Working with Sardou

This page is for developers building tooling around TOSCA and provides
further direction for working with the Python Library. For an overview,
see the [previous page](sardou.md) in this section. This page assumes you
have imported Sardou.

```python
from sardou import Sardou
```

## Validation

To validate a TOSCA template, create a new `Sardou` object, passing it a template
file path, or the template content directly as a Python dict.
This will validate the template and complete the representation, inheriting from parent
types.

=== "From path"

	```python
	>>> sat = Sardou("my_app.yaml")
	Processed successfully: my_app.yaml
	```

=== "From content"

	```python
	>>> sat_dict = {
	...     "tosca_definitions_version": "tosca_2_0",
	...     "imports": [
	...         {
	...             "namespace": "swch",
	...             "url": "https://raw.githubusercontent.com/Swarmchestrate/tosca/refs/heads/main/profiles/eu.swarmchestrate/profile.yaml",
	...         }
	...     ],
	...     "service_template": {
	...         "node_templates": {
	...             "myservice": {
	...                 "type": "swch:Microservice",
	...                 "properties": {
	...                     "image": "docker.io/istio/examples-bookinfo-details-v1:1.20.3",
	...                     "replicas": 1,
	...                 },
	...             }
	...         }
	...     },
	... }
	>>> sat = Sardou(content=sat_dict)
	Processed successfully
	```

The template is not resolved at this point (i.e. statisfied requirements and created
relationships) - that functionality is to come. If there are errors or warnings, they
will be presented at this time.

## Exploring the Template

Get the raw, uncompleted (original YAML) with the `raw` attribute.

```python
>>> sat.raw
{'tosca_definitions_version': 'tosca_2_0', 'description': 'stressng on Swarmchestrate', 'imports': [{'namespace': 'swch' ...
```

You can traverse YAML maps using dot notation if needed (which leads to some unexpected behaviour,
so this may not be a long-term feature):

```python
>>> sat.nodeTemplates
{'stressng': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::Kubernetes.APIObject': ...
```

Or at any point, you can get a regular Python dictionary:

```python
>>> sat.nodeTemplates._to_dict()
{'stressng': {'metadata': {}, 'description': '', 'types': {'eu.swarmchestrate:0.1::Kubernetes.APIObject': ...
```

## Applications

!!! warning

	The functionality described here only works on Swarm Application Templates.


### Policies

The policy getters below return dictionaries whose top-level keys are
user-defined names and whose values are sub-dictionaries that vary
by policy type. You might dump the returned dictionary to JSON or YAML.

All policies that target specific Microservices (as opposed to a policy
targeting the application as a whole) will contain a
[`targets` key](policy.md#targets) in their sub-dictionary.

#### Reconfiguration

Grab the reconfiuration policies as a Python object with `get_reconfiguration()`.
In addition to `targets`, [the following keys](policy.md#types.reconfiguration)
are present in the sub-dicts.

```python
>>> sat.get_reconfiguration()
{'frontend_reconfiguration': {'constants': {'cpu_util_threshold': '80'}, 'rule': 'if cpu_util_prct > cpu_util_threshold:\n  scale_out(details_v1, productpage_v1)\nelse:\n  pass\n', 'targets': ['details_v1', 'productpage_v1']}, ...
```

#### Quality of Service Policies

Grab the QoS requirements as a Python object with `get_qos()`. In 
addition to `targets`, specific QoS keys are present in the sub-dicts,
along with a `type` key indicating the specific sub-type. You can view
these details [in the reference here](policy.md#types.qos).

```python
>>> sat.get_qos()
{'bandwidth': {'priority': 0.5, 'target': 800, 'type': 'eu.swarmchestrate:0.1::QoS.Performance.Bandwidth'} ...
```

#### Scheduling Policies

Grab the scheduling policies as a Python object with `get_scheduling()`.
Only `targets` and `type` key (indicating the specific sub-type) are
present in the sub-dicts. Scheduling policy types [can be seen here](policy.md#types.scheduling).

```python
>>> sat.get_scheduling()
{'frontend_colocation': {'type': 'eu.swarmchestrate:0.1::Scheduling.Colocation', 'targets': ['details_v1', 'productpage_v1']} ...
```

### Resource Requirements

Grab the Resource requirements as a Python object with `get_requirements()`
You could dump this to JSON or YAML.

```python
>>> sat.get_requirements()
{'details_v1': {'expression': "lambda vals: ((vals['host.num-cpus'] >= 1) and (vals['host.mem-size'] >= 2) and (any(entry in vals['network.explicit-tcp-allow'] for entry in ['ALL', 80])))", 'colocated': ['productpage_v1'],  ...
```

### Monitoring Details

Get the monitoring details, which include `metrics` and `slo-constraints` per
Microservice, with the `get_monitoring()` function. Dump to YAML or JSON.

```python
>>> sat.get_monitoring()
{'details_v1': {'metrics': {'raw': [{'name': 'cpu_util_instance', 'sensor': 'Netdata', 'config': {'scope_contexts': 'k8s.cgroup.cpu', 'results-aggregation': 'SUM'}, 'collection_frequency': '30 sec', 'collection_output': 'all'}], 'composite': [{'name': 'cpu_util_prct', 'formula': 'mean( cpu_util_instance )', 'collection_frequency': '30 sec', 'collection_output': 'all', 'window_type': 'sliding', 'window_size': '5 min', 'grouping': 'per_zone'}]}, 'slo-constraints': {'name': 'cpu_utilization', 'metric': 'cpu_util_prct', 'operator': '>', 'threshold': 80.0}}}
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

## Capacities

You can create a Sardou object from a CDT with the same approach as for SATs.

```python
>>> cdt = Sardou("my_cap.yaml")
Processed successfully: my_cap.yaml
```

!!! warning

	The below methods only work on Capacity Description Templates.

### Capacity Details

Given a CDT, Sardou can extract the capability details of each available flavour,
as well as the [overall capacity](cdt.md#cdt-overall-capacity), if defined.

```python
>>> cdt.get_capacities()
{'cloud_flavours': {'m2-large': {'energy': {'consumption': 0.1, 'energy-type': 'non-green', 'powered-type': 'mains-powered'},
```

The following top-level keys are possible, depending on the capacity:

`cloud_flavours`{ #cap.cloud-flavours }

:   Map of flavour definitions, keyed by flavour name with values specifying all
	[defined **capabilities**](capacity.md#capacity).

`cloud_capacity_raw`{ #cap.cloud-capacity-raw }

:   Map of overall available countable resources, keyed by name according
	to [capabilities in OverallCapacity](capacity.md#overallcapacity),
	with integer values.

`cloud_capacity_flavour`{ #cap.cloud-capacity-flavour }

:   Map of overall available countable resources, keyed by names defined
	in `cloud_flavours` above, with integer values specifying number of instances.

`edge_instances`{ #cap.edge-instances }

:   Map of edge instance definitions keyed by edge name with values specifying all
	[defined **capabilities**](capacity.md#capacity).


### Resource Description Templates

You can generate a Resource Description Template (RDT) with a CDT and an
accepted offer. An RDT is an internal template used to pass deployment
configuration for the Swarm to the Cluster Builder component.

```python
>>> offer = json.load("ra-sztaki-offer.json")
>>> cdt.generate_rdt(selected_offer=offer, output_path="sztaki-rdt.yaml")
```

Which will generate an RDT at the given `output_path`.

## Resources

You can then create a new Sardou object from an RDT.

```python
>>> rdt = Sardou("sztaki-rdt.yaml")
Processed successfully: sztaki-rdt.yaml
```

!!! warning

	This method only works on Resource Description Templates.


### Cluster Configuration Details

Get the cluster configuration details for the resources as a Python object with `get_cluster()`
You could dump this to JSON or YAML.

```python
>>> rdt.get_cluster()
{'ra-sztaki-cloud-hu_swarm2_details_v1_t2-large-ubuntu-uow': {'ami': 'ami-customuow', 'cloud': 'aws', 'custom_ingress_ports': [{'from': 80, 'protocol': 'TCP', 'to': 80}], 'instance_type': 't2.large', 'ssh_key': 'g-key', 'security_groups': ['0eb63f2b-b656-47a1-a0e7-3da0a993379e'], 'ssh_user': 'ubuntu', 'node_labels': {'labels.swarmchestrate.io/ms_id': 'details_v1'}}, ...
```