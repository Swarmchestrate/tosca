# Capacity Description Template

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
tosca_definitions_version: tosca_2_0

description: AWS EC2 capacity in US East

metadata:
  name: cap-aws-uow-us
  author: University of Westminster
  date: 2026-01-12
  version: 0.1
  tags:
  - provider: aws
  - region: us-east-1

imports:
- namespace: swch
  url: https://raw.githubusercontent.com/Swarmchestrate/tosca/refs/heads/main/profiles/eu.swarmchestrate/profile.yaml
```

## Define a Base Resource Type (recommended)

Create a base node type for the capacity provider. In this example `EC2` captures the generic
AWS EC2 shape and shared properties for all instance sizes.

```yaml
node_types:
  EC2:
    description: >
      An EC2 compute node from the University of Westminster provision
    properties:
      region_name:
        type: string
        required: true
        description: >
          AWS region defaults to us-east-1
        default: us-east-1
      image_id:
        type: string
        required: true
        description: >
          The ID of the Amazon Machine Image (AMI) used to launch the EC2 instance.
        default: ami-0c02fb55956c7d316
      instance_type:
        type: string
        required: true
        description: >
          The type of EC2 instance (e.g., t2.micro, m5.large) specifying compute resources.
      key_name:
        type: string
        required: false
        description: >
          The name of the SSH key pair used to access the EC2 instance.
        default: g-key
      security_group_ids:
        type: list
        required: false
        entry_schema: string
        description: >
          A list of security group IDs that control inbound and outbound traffic for the EC2 instance.
        default:
        - sg-0bb1c123456789abc
      tags:
        type: map
        required: false
        entry_schema: string
        description: >
          Key-value pairs used to tag and categorise the EC2 instance (e.g., environment: production).
        default:
          managed_by: swarmchestrate
    capabilities:
      capacity:
        properties:
          instances:
            type: integer
            required: true
            description: Number of instances
      host:
        properties:
          num-cpus:
            type: string
            required: true
            description: Number of vCPUs
          mem-size:
            type: string
            required: true
            description: Memory size in GB
          disk-size:
            type: string
            required: true
            description: Disk size in GB
          bandwidth:
            type: string
            required: true
            description: Network bandwidth in Mbps
      os:
        properties:
          type:
            type: string
            required: true
            description: Operating system type
            default: linux
          version:
            type: string
            required: true
            description: Operating system version
            default: "22.04"
          distribution:
            type: string
            required: true
            description: Operating system distribution
            default: ubuntu
      resource:
        properties:
          provider:
            type: string
            required: true
            description: Resource provider
            default: Amazon
          capacity-provider:
            type: string
            required: true
            description: Capacity provider
            default: uow
          type:
            type: string
            required: true
            description: Resource type
            default: cloud
      pricing:
        properties:
          cost:
            type: float
            required: true
            description: Cost per hour in USD
      locality:
        properties:
          continent:
            type: string
            required: true
            description: Continent where the resource is located
            default: N.America
          country:
            type: string
            required: true
            description: Country where the resource is located
            default: USA
          city:
            type: string
            required: true
            description: City where the resource is located
            default: N.Virginia
      energy:
        properties:
          consumption:
            type: float
            required: true
            description: Energy consumption in watts per hour
          powered-type:
            type: string
            required: false
            description: Type of power used (e.g., renewable, non-renewable)
            default: mains-powered
          energy-type:
            type: string
            required: false
            description: Specific type of energy (e.g., solar, wind, coal)
            default: non-green
```

## Derive Specific Instance Flavours

Derive specific instance types from the base to encode size-specific defaults. Override only what differs: e.g. `instance_type`, host capacity, pricing, and energy metrics.

```yaml
service_template:

  node_templates:

    EC2.t3.micro:
      type: EC2
      description: >
        An EC2 t3.micro compute node from the University of Westminster provision
      properties:
        instance_type: t3.micro
      capabilities:
        capacity:
          properties:
            instances: 100
        host:
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

    EC2.t3.small:
      type: EC2
      description: >
        An EC2 t3.small compute node from the University of Westminster provision
      properties:
        instance_type: t3.small
      capabilities:
        capacity:
          properties:
            instances: 100
        host:
          properties:
            num-cpus: 2
            mem-size: 2
            disk-size: 20
            bandwidth: 100
        pricing:
          properties:
            cost: 0.02
        energy:
          properties:
            consumption: 15.0
```

Repeat for other sizes (e.g. `EC2.t3.medium`, `EC2.t3.large`)
changing type, CPU, memory, disk, bandwidth, cost, and energy to match the 
resource you provide.

