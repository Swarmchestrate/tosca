#!/usr/bin/env python3
"""
extract-resource-requirements
Extracts nodes with node_filter keys from TOSCA YAML files and generates ask.yaml format
"""

import yaml
import sys
from datetime import datetime
from pathlib import Path


def extract_property_info(property_ref):
    """
    Extract capability type and property name from $get_property reference
    
    Args:
        property_ref: Property reference (usually $get_property)
        
    Returns:
        tuple: (capability_type, property_name)
    """
    if isinstance(property_ref, dict) and '$get_property' in property_ref:
        path_parts = property_ref['$get_property']
        if len(path_parts) >= 5:
            capability_type = path_parts[3]  
            property_name = path_parts[4]   
            return capability_type, property_name
    
    return None, None


def map_constraint_to_ask_format(constraint_func, args):
    """
    Map TOSCA constraint function to ask.yaml format
    
    Args:
        constraint_func: TOSCA function name (e.g., '$equal', '$greater_than')
        args: Function arguments
        
    Returns:
        Constraint value in ask.yaml format
    """
    if len(args) < 2:
        return None
    
    # The second argument is typically the constraint value
    constraint_value = args[1]
    
    # Only handle $equal as direct value
    if constraint_func == '$equal':
        return constraint_value
    else:
        # For any other function, preserve it as-is
        return {constraint_func: constraint_value}


def convert_node_filter_to_capabilities(node_filter):
    """
    Convert node_filter structure to ask.yaml capabilities format
    Assumes node_filter is always $and at the top level
    
    Args:
        node_filter (dict): Node filter data
        
    Returns:
        dict: Capabilities structure for ask.yaml
    """
    capabilities = {}
    
    # Since node_filter is always $and, extract the conditions
    if '$and' in node_filter:
        conditions = node_filter['$and']
        
        for condition in conditions:
            # Each condition should be a constraint function
            for constraint_func, constraint_args in condition.items():
                if len(constraint_args) >= 2:
                    # Extract property information from first argument
                    capability_type, property_name = extract_property_info(constraint_args[0])
                    
                    if capability_type and property_name:
                        # Initialize capability if not exists
                        if capability_type not in capabilities:
                            capabilities[capability_type] = {'properties': {}}
                        
                        # Map the constraint to ask.yaml format
                        constraint_value = map_constraint_to_ask_format(constraint_func, constraint_args)
                        if constraint_value is not None:
                            capabilities[capability_type]['properties'][property_name] = constraint_value
    
    return capabilities


def extract_nodes_with_filter(yaml_data):
    """
    Extract nodes that have node_filter key from node_templates section
    
    Args:
        yaml_data (dict): Parsed YAML data
        
    Returns:
        dict: Dictionary of nodes with node_filter keys
    """
    nodes_with_filter = {}
    
    # Navigate to node_templates section
    if 'service_template' in yaml_data and 'node_templates' in yaml_data['service_template']:
        node_templates = yaml_data['service_template']['node_templates']
        
        for node_name, node_data in node_templates.items():
            if 'node_filter' in node_data:
                nodes_with_filter[node_name] = node_data
                
    return nodes_with_filter


def generate_ask_yaml(nodes_with_filter, output_file):
    """
    Generate ask.yaml file from nodes with node_filter
    
    Args:
        nodes_with_filter (dict): Nodes that have node_filter
        output_file (str): Output file path
    """
    ask_data = {}
    
    for node_name, node_data in nodes_with_filter.items():
        # Create basic structure for each node
        ask_entry = {
            'metadata': {
                'created_by': 'extract-reqs@script.com',
                'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'description': f'Generated from node {node_name}',
                'version': '1.0'
            }
        }
        
        # Convert node_filter to capabilities
        if 'node_filter' in node_data:
            capabilities = convert_node_filter_to_capabilities(node_data['node_filter'])
            if capabilities:
                ask_entry['capabilities'] = capabilities
                
        ask_data[node_name] = ask_entry
    
    # Write to YAML file
    with open(output_file, 'w') as f:
        yaml.dump(ask_data, f, default_flow_style=False, sort_keys=False, indent=2)


def main():
    """Main function"""
    if len(sys.argv) != 3:
        print("extract-resource-requirements - TOSCA node_filter to ask.yaml converter")
        print("")
        print("Usage: python3 extract-resource-requirements.py <input_yaml_file> <output_yaml_file>")
        print("Example: python3 extract-resource-requirements.py stressng.yaml ask.yaml")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Check if input file exists
    if not Path(input_file).exists():
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    try:
        # Load input YAML
        with open(input_file, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        # Extract nodes with node_filter
        nodes_with_filter = extract_nodes_with_filter(yaml_data)
        
        if not nodes_with_filter:
            print("No nodes with node_filter found in the input file")
            sys.exit(1)
        
        print(f"Found {len(nodes_with_filter)} node(s) with node_filter:")
        for node_name in nodes_with_filter.keys():
            print(f"  - {node_name}")
        
        # Generate ask.yaml
        generate_ask_yaml(nodes_with_filter, output_file)
        
        print(f"Successfully generated '{output_file}'")

        
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

