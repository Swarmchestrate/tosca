# Authoring Capacities

The Capacity Description Template (CDT) defines the resources available for a
specific capacity. Like the SAT, it follows TOSCA v2.0 and uses the same custom
Swarmchestrate profile.

!!! warning ""

    The specification is not entirely finalised or fixed. Field names and types
    may change over the course of the project.

## Top Matter

Start every CDT with the same structure used in a SAT: `tosca_definitions_version`, a
human-friendly `description`, and optional `metadata` that records authorship and tagging
Follow with your profile identifier and imports.
```yaml
tosca_definitions_version: tosca_2_0 # (1)!

description: AWS EC2 capacity in US East # (2)!

metadata: # (3)!
  name: cap-aws-uow-us
  author: University of Westminster
  date: 2026-01-12
  version: 0.1
  tags:
  - provider: aws
  - region: us-east-1
  kind: CDT # (4)!

imports: # (5)!
- namespace: swch
  url: https://raw.githubusercontent.com/Swarmchestrate/tosca/refs/heads/main/profiles/eu.swarmchestrate/profile.yaml
```

1. This line indicates the TOSCA version and is **mandatory**.
2. A `description` of the capacity is *recommended*.
3. Providing `metadata` is *optional* - you may add additional custom fields.
4. `kind` is entirely *optional*, but please do not create a custom field with this name.
5. Importing the Swarmchestrate profile from this `url` is required. We recommend a namespace called `swch`.

## Define a Base Resource Type (recommended)

Create a base node type or blueprint for the capacity provider. This type should
derive from one of the supported capacity types:

- [`EC2Capacity`](capacity.md#ec2capacity)for capacities providing AWS EC2 instances
- [`OpenStackCapacity`](capacity.md#openstackcapacity) for capacities providing OpenStack instances
- [`EdgeCapacity`](capacity.md#edgecapacity) for capacities providing edge devices

!!! tip

    Each capacity type will require different properties to ensure successful deployment.
    Click on the capacity type in the list above to see what properties are required.

In the below example `UoW-EC2` will extend the generic `EC2Capacity` with capabilities and
properties that are specific to instance types from the University of Westminster AWS
provision. We will use this type to simplify our definition of concrete instances later.

```yaml
# (1)!
node_types:

  UoW-EC2: # (2)!
    derived_from: swch:EC2Capacity # (3)!

    description: > # (4)!
      Blueprint for an EC2 compute node from the UoW provision
```

1. This is a top-level key. If you are familiar with the SAT, note we are not yet in a `service_template`.
2. A name for this base node type, which you will reference later.
3. The type tells the orchestrator that this represents a resource capacity.
4. A `description` is *optional*. The `>` is YAML syntax for multi-line strings.

### Define Common Properties

Properties provide the configuration required for deploying or configuring
resources. Where these are common across instances in your capacity, it is
recommended to bake them into the base resource type. In the example below, we
set defaults for `region_name` and `image_id`, since all instances from our
provision are deployed in the same region and use the same Amazon Machine Image.

!!! tip
    Recall that each capacity type will *require* certain properties. Not all
    required properties need to be defined here - some will be defined later
    when authoring concrete instances.

```yaml
node_types: # (1)!
  UoW-EC2:
    derived_from: swch:EC2Capacity
    description: >
      Blueprint for an EC2 compute node from the UoW provision

    properties:

      region_name: # (2)!
        default: us-east-1

      image_id:
        default: ami-0c02fb55956c7d316
```

1. As above.
2. We can set defaults for multiple properties like so.

### Define Common Capabilities

Capabilities describe the attributes of a cloud instance or edge device.
These are used during matchmaking to assign the appropriate resource to
host the microservices of an application.

```yaml
node_types: # (1)!
  UoW-EC2:
    derived_from: swch:EC2Capacity
    description: >
      Blueprint for an EC2 compute node from the UoW provision
    properties:
      region_name:
        default: us-east-1
      image_id:
        default: ami-0c02fb55956c7d316

    capabilities:

      os: # (2)!
        properties:
          type:
            default: linux
          version:
            default: "22.04"
          distribution:
            default: ubuntu

      resource: # (3)!
        properties:
          capacity-provider:
            default: uow

      locality: # (4)!
        properties:
          continent:
            default: N.America
          country:
            default: USA
          city:
            default: N.Virginia
```

1. As above.
2. Here we describe the operating system set by our default `image_id`.
3. We set ourselves as the `capacity-provider`.
4. Describing the location of the default region we have set in this blueprint.


## Derive Specific Instance Flavours

Derive specific instance types from the base to encode size-specific defaults. Override only what differs. Typically, with cloud instances, this will always be the *instance type* as well as the capabilities that are specific to that type, such as host hardware, price, and energy. However,
it may be necessary to set other properties or capabilities depending on your specific case.

!!! important "Capacity by Flavour"

    At this time, you may specify the number of available instances of this specific
    flavour, by specifying the `instances` property on the `capacity` capability. See
    the note on **Overall Capacity** below if you are limited not by number of instances,
    but by hardware.


```yaml
service_template:

  node_templates: # (1)!

    t3-micro: # (2)!

      type: UoW-EC2 # (3)!

      properties:
        instance_type: t3.micro # (4)!

      capabilities: 

        capacity: # (5)!
          properties:
            instances: 100

        host: # (6)!
          properties:
            num-cpus: 2
            mem-size: 1
            disk-size: 20
            bandwidth: 100
        pricing:
          properties:
            cost: 0.0139
        energy:
          properties:
            consumption: 13.0
```

1. These will already exist if you specified OverallCapacity in the step above.
2. A name for the resource your are offering.
3. Using the base resource type we defined above.
4. Configuration options for this specific resource - here only the EC2 `instance_type`.
5. Specifying the number of available instances of this flavour.
6. The rest of the capabilities according to the chosen `instance_type`.

Repeat for other flavours changing type, CPU, memory, disk, bandwidth, cost, and
energy to match the resource you provide.
{ #cdt-overall-capacity }

??? important "Overall Capacity"

    If the amount of resource you can provide from this capacity is limited by
    hardware, you should specify an [`OverallCapacity`](capacity.md#overallcapacity),
    indicating the total CPU, memory, disk and/or bandwidth available. This sits
    under `node_templates` and is by convention the first node in your `CDT`.

    ```yaml
    service_template:

      node_templates:

        MyOverall: # (1)!
          type: swch:OverallCapacity

          capabilities: # (2)!
            capacity:
              properties:
                num-cpus: 40
                mem-size: 1000
                disk: 10000
    ```

    1. The name of this node can be anything you choose, but you must refer to the `OverallCapacity` node from the profile.
    2. Specify the total amounts of resource available under the `capacity` key.

## Edge

Edge nodes are defined in the same way, just use the `EdgeCapacity` type from the
profile to create these. Here is a small example:

```yaml
node_types:
  UoW-rPi:
    derived_from: swch:EdgeCapacity
    description: >
      A Raspberry Pi edge node from the University of Westminster
    properties:
      ssh_user:
        default: ubuntu
    capabilities:
      host:
        properties:
          num-cpus:
            default: 4
          mem-size:
            default: 16
          disk-size:
            default: 200
          bandwidth:
            default: 1000
      pricing:
        properties:
          cost:
            default: 0.00
      energy:
        properties:
          consumption:
            default: 0.01

service_template:
  node_templates:
    device-1:
      type: UoW-rPi
      properties:
        ip: 172.12.1.1

    device-2:
      type: UoW-rPi
      properties:
        ip: 172.12.1.2
```