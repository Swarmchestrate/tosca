# Author Guide

The Swarmchestrate Application Template (SAT) conforms closely to the v2.0 of
the TOSCA Specification and uses a custom Swarmchestrate profile being developed
by the project.

TOSCA and by association, the SAT, are specified in YAML, a
superset of JSON. YAML does away with some of the noisy JSON syntax, relying on
indentation instead, for a more human readable representation.

!!! warning ""

    The specification is not entirely finalised or fixed. Field names and types
    may change over the course of the project.

## Top Matter

Every SAT begins in the same way:

* Reference the TOSCA v2.0 Specification
* *Optionally* describe the application
* *Optionally* provide application metadata
* Import the custom Swarmchestrate profile as `swch`

*Optional fields provide additional information for humans*

```yaml
tosca_definitions_version: tosca_2_0

description: stressng on Swarmchestrate

metadata:
  name: stressng
  author: Jay DesLauriers
  date: 2025-08-10
  version: 1.0
  tags:
  - demo

imports:
- namespace: swch
  url: https://raw.githubusercontent.com/Swarmchestrate/tosca/refs/heads/main/profiles/eu.swarmchestrate/profile.yaml
```

## Defining the Swarm

The next section of the SAT defines the `service_template` and `node_templates`
keys. The first entry, or **node**, under `node_templates` is recommended to be
the required `swarm` node. 

Each node in a TOSCA template is assigned a type, and
here we use the `Swarm` type from the `swch` namespace we created in the top
matter. Types from the custom Swarmchestrate profile are rich in functionality,
and the `Swarm` type is later used to deploy the required compute resources for
the application. Simply use it as shown below, with the `substitute` directive.

```yaml
service_template:

  node_templates:

    swarm:
      type: swch:Swarm
      directives:
      - substitute
```

## Defining a Microservice

The rest of the `node_templates` section should be populated with
nodes that describe your application microservices and their resource
requirements. Each node describes one microservice.

These nodes should use the `Microservice` type from the Swarmchestrate
profile at `swch`, which offers the most common configuration options
for OCI containerised applications to be deployed to Kubernetes. These
options are defined under the `properties` key.

The only required property is `image`, which should define the full
path to the OCI container image for the microservice. Other available
properties are defined in the [SAT Microservice Specification](application.md).
`

```yaml
    # Indented under node_templates (same level as swarm)
    stressng:
      type: swch:Microservice
      properties:
        image: lorel/docker-stress-ng
        args: ['--cpu', '0', '--cpu-method', 'pi', '-l', '20']
```

## Defining Resource Requirements

Attached to each Microservice are its resource requirements. This
information is generally required so that Swarmchestrate can make
the most intelligent decisions about the initial deployment. 

The `requirements` key should express a requirement for `host`,
which should be described by a TOSCA `node_filter`. Node filters
are logical expressions that indicate a desired resource configuration.
The syntax is not immediately intuitive, so a full list of examples is
available in the SAT Resource Specification.

In the below example, the microservice requires a resource that is
located in London that has exactly 4 CPUs.

```yaml
    # Continuation of the example above. Not a new node.
    stressng:
      type: swch:Microservice
      properties:
        image: lorel/docker-stress-ng
        args: ['--cpu', '0', '--cpu-method', 'pi', '-l', '20']
      requirements:
      - host:
          node_filter:
            $and:
              - $equal:
                  - $get_property: [ SELF, TARGET, CAPABILITY, host, num-cpus ]
                  - 4
              - $equal:
                  - $get_property: [ SELF, TARGET, CAPABILITY, locality, city ]
                  - london
```

## Defining QoS Policies

QoS policies drive reconfiguration in Swarmchestrate. QoS policies target
a specific metric value and make intelligent reconfiguration decisions to
ensure these targets are met. They are defined as TOSCA Policies, under the
`policies` key of the `service_template` section.

Policies specify a priority, to be used in case of competing policies (high
priority policies take precedence). They also specify a tolerance - an
allowable over/under for the target value. Most importantly, policies specify
an exact `target` value, or `targets`, which can be `greater_than`, `less_than`
or `in_range`.

A full list of policies is available in the [SAT Policy Specification](policy.md).

```yaml
  # Indented under service_template (same level as node_templates)
  policies:
  - type: swch:QoS.Performance.ResponseTime
    properties:
      priority: 90
      tolerance: 0.2
      targets:
      - less_than: 200ms
```
