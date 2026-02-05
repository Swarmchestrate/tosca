from jinja2 import Environment, FileSystemLoader
from sardou import Sardou
env = Environment(
    loader=FileSystemLoader('.'),
    extensions=['jinja2.ext.do']
)
template = env.get_template('manifest.yaml.j2')
tosca = Sardou('templates/BookInfo.yaml')
node_templates = tosca.raw._to_dict()['service_template']['node_templates']

output = template.render(
    node_templates=node_templates,
    image_pull_secret='my-registry-secret'
)
with open("manifest-out.yaml", 'w+') as f:
    f.write(output)