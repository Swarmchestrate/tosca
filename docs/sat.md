# Authoring Applications

The Swarm Application Template (SAT) conforms closely to the v2.0 of
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
tosca_definitions_version: tosca_2_0 # (1)!

description: stressng on Swarmchestrate # (2)!

metadata: # (3)!
  name: stressng
  author: Jay DesLauriers
  date: 2025-08-10
  version: 1.0
  tags:
  - demo
  kind: SAT # (4)!

imports: # (5)!
- namespace: swch
  url: https://raw.githubusercontent.com/Swarmchestrate/tosca/refs/heads/main/profiles/eu.swarmchestrate/profile.yaml
```

1. This line indicates the TOSCA version and is **mandatory**.
2. A `description` of your app is *optional*.
3. Providing `metadata` is *optional* - you may add additional custom fields.
4. `kind` is entirely *optional*, but please do not create a custom field with this name.
5. Importing the Swarmchestrate profile from this `url` is required. We recommend a namespace called `swch`.

## Defining the Swarm

The next section of the SAT defines the `service_template` and `node_templates`
keys. The first entry, or **node**, under `node_templates` is recommended to be
the required `swarm` node, which is an abstract representation of the cloud and
edge resources that will eventually come to comprise the swarm.

Each node in a TOSCA template is assigned a type, and
here we use the `Swarm` type from the `swch` namespace we created in the top
matter. Types from the custom Swarmchestrate profile are rich in functionality,
and the `Swarm` type is later used to deploy the required compute resources for
the application. Simply use it as shown below, with the `substitute` directive.

```yaml
service_template: # (1)!

  node_templates: # (2)!

    swarm: # (3)!
      type: swch:Swarm 
      directives:
      - substitute
```

1. The `service_template` has two sub-sections - *nodes* and *policies*.
2. TOSCA nodes, under `node_templates`, are the deployable components of the application.
3. The first of these - the cloud and edge resources that make up a swarm - are defined here in abstract. The `substitute` directive indicates that the abstract representation should be swapped with concrete nodes.

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
properties are defined in the [SAT Microservice Specification](microservice.md).
`

```yaml
    # (1)!

    stressng: # (2)!

      type: swch:Microservice # (3)!

      properties: # (4)!
        image: lorel/docker-stress-ng
        args: ['--cpu', '0', '--cpu-method', 'pi', '-l', '20']
```

1. Indented under `node_templates` at the same level as `swarm`.
2. Each microservice must have a unique name in the application.
3. This type tells the orchestrator that this is a microservice to be deployed.
4. Common container configuration options in either Docker and Kubernetes nomenclature are supported.

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
    # (1)!
    stressng:
      type: swch:Microservice
      properties:
        image: lorel/docker-stress-ng
        args: ['--cpu', '0', '--cpu-method', 'pi', '-l', '20']

      requirements: # (2)!
      - host:
          node_filter: # (3)!
            $and:
              - $equal:
                  - $get_property: [ SELF, TARGET, CAPABILITY, host, num-cpus ]
                  - 4
              - $equal:
                  - $get_property: [ SELF, TARGET, CAPABILITY, locality, city ]
                  - london
```

1. Continuation of the example above (not a new node).
2. The `requirements` key should define a *list* of `host` *map* objects (typically with one element).
3. Use `node_filter` to specify resource requirements of this microservice using logical expressions.

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
  # (1)!

  policies: # (2)!
  - type: swch:QoS.Performance.ResponseTime
    properties:
      priority: 90 # (3)!
      tolerance: 0.2 # (4)!
      targets:
      - less_than: 200ms # (5)!
```

1. The `policies` key is a new key under `service_template`.
2. Each list item under policies should define a `type` and `properties`.
3. Priorities are used when policies are in conflict. Higher priority policies take precedence.
4. An tolerance allows for slippage either side of the defined target.
5. Define a `target` when targeting a specific value (allowing for `tolerance`), or one or more `targets` when more nuance is needed.

## Defining Reconfiguration Policies

Where a QoS policy states a target, a Reconfiguration policy states how to
reach it. The policy carries a `rule`, written in MiniZinc, which the platform
solves to decide how many instances of your microservice run, and which nodes
they run on.

The rule is given the state of the system, and returns the arrangement it wants
next:

* `sys_node_count_max`, `sys_node_count_actual` and `sys_pod_count_max` bound
  the problem.
* `sys_mapping_actual` holds the current arrangement, one entry per pod, giving
  the index of the node it runs on, or `0` for a pod that does not exist.
* `sys_node_count_next` and `sys_mapping_next` are the answer, and are marked
  `:: add_to_output` so the platform reads them back.

Your own values reach the rule two ways. Anything in `constants` is yours to
name, written as a string in the SAT and declared as a float in the rule.
Monitored values arrive as arrays indexed by node, one entry per node, under the
name of the metric itself, so the names in the rule match the metrics the
microservice declares. A composite metric grouped `per_instance` gives exactly
this shape.

Three periods govern how often the policy acts, all in seconds. A full
description of each is in the [SAT Policy Specification](policy.md).

```yaml
  # (1)!

  policies:
  - stressng_reconfiguration: # (2)!
      type: swch:Reconfiguration
      properties:
        period_check_slo: 1 # (3)!
        period_evaluation: 300
        period_cooldown: 30
        constants: # (4)!
          threshold_max_node_load: "80.0"
        rule: | # (5)!
          % --- supplied by Swarmchestrate ---
          int: sys_pod_count_max;
          int: sys_node_count_max;
          int: sys_node_count_actual;
          array[1..sys_pod_count_max] of int: sys_mapping_actual;

          % --- returned to Swarmchestrate ---
          var 1..sys_node_count_max: sys_node_count_next :: add_to_output;
          array[1..sys_pod_count_max] of var 0..sys_node_count_max:
              sys_mapping_next :: add_to_output;

          var 0..sys_pod_count_max: sys_pod_count_next =
              sum(p in 1..sys_pod_count_max)(sys_mapping_next[p] > 0);
          int: sys_pod_count_actual =
              sum(p in 1..sys_pod_count_max)(sys_mapping_actual[p] > 0);

          % --- declared above, under constants ---
          float: threshold_max_node_load;

          % --- collected by monitoring ---
          array[1..sys_node_count_max] of float: node_load; % (6)!

          % leave the number of nodes alone
          constraint sys_node_count_next = sys_node_count_actual;

          % keep at least one pod running
          constraint sys_pod_count_next >= 1;

          % at most one pod per node
          constraint forall(i, j in 1..sys_pod_count_max where i < j)(
              sys_mapping_next[i] = 0 \/ sys_mapping_next[j] = 0 \/
              sys_mapping_next[i] != sys_mapping_next[j]
          );

          % add a pod while any node is overloaded and there is room
          constraint (
              exists(n in 1..sys_node_count_max)(
                  node_load[n] > threshold_max_node_load)
              /\ sys_pod_count_actual < sys_pod_count_max
          ) -> sys_pod_count_next > sys_pod_count_actual;

          % of the arrangements that satisfy the above, prefer the one that
          % moves the fewest pods
          var int: loss = sum(p in 1..sys_pod_count_max)(
              bool2int(sys_mapping_next[p] != sys_mapping_actual[p]));

          solve minimize loss; % (7)!
      targets: # (8)!
      - stressng
```

1. Continuation of the `policies` key above (not a new key).
2. Name each policy. The name identifies it in logs and in the Sardou library.
3. How often SLOs are checked, how often the rule is solved, and how long to wait after acting before acting again.
4. Values you name yourself, quoted, and declared in the rule below.
5. The rule is a block string, so indentation inside it is preserved.
6. `node_load` is a composite metric declared by this microservice, grouped `per_instance`.
7. Several arrangements usually satisfy the constraints. The loss function chooses between them.
8. The microservices this policy reconfigures.

Colocated microservices are reconfigured together, so Sardou rejects a SAT
that splits a colocation group across two Reconfiguration policies.

## Defining Forecasts

A Forecast policy asks Swarmchestrate to predict the future values of metrics
your microservices already collect, so that decisions can be taken before a
threshold is reached. Each metric you name is declared in the `metrics`
capability of one of the microservices the policy targets.

Periods are given in seconds. `resolution` sets how finely values are averaged
before being predicted, and `forecast_duration` how far ahead predictions are
needed. The optional periods cover how much recent history each prediction
considers, how much data is kept for training, and how often the model is
retrained.

All the metrics in one policy are predicted by a single model, so metrics that
need different periods belong in separate policies.

```yaml
  # (1)!

  policies:
  - load_forecast: # (2)!
      type: swch:Forecast
      properties:
        metrics: # (3)!
        - node_load
        - node_temp
        resolution: 30 # (4)!
        forecast_duration: 2880 # (5)!
        lookback_duration: 8640 # (6)!
        retrain_interval: 1800
        coverage: 0.95 # (7)!
      targets: # (8)!
      - audio_class
```

1. Continuation of the `policies` key above (not a new key).
2. Name each policy. The name identifies it in logs and in the Sardou library.
3. The metrics to predict. These are the composite metrics the reconfiguration rule above consumes.
4. Values are averaged into 30 second intervals, matching how often they are collected.
5. Predictions are needed 48 minutes ahead.
6. Each prediction considers the last 144 minutes.
7. 95% of actual values should fall inside the predicted interval. Higher values widen it.
8. The microservices this policy forecasts for.

[Forecast parameters](forecasting.md) records how these periods reach the
forecasting library.
