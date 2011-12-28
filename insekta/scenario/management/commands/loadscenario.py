import os
import json

import libvirt
from django.core.management.base import BaseCommand, CommandError

from insekta.scenario.models import Scenario

_REQUIRED_KEYS = ['name', 'title', 'memory', 'secrets']

class Command(BaseCommand):
    args = '<scenario_path>'
    help = 'Loads a scenario into the database and storage pool'
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('The only arg is the scenario directory')
        
        scenario_dir = args[0]
        
        try:
            with open(os.path.join(scenario_dir, 'metadata.json')) as f_meta:
                metadata = json.load(f_meta)
                if not isinstance(metadata, dict):
                    raise ValueError('Metadata must be a dictionary')
        except IOError, e:
            raise CommandError('Could not load metadata: {}'.format(e))
        except ValueError, e:
            raise CommandError('Could not parse metadata: {}'.format(e))

        for required_key in _REQUIRED_KEYS:
            if required_key not in metadata:
                raise CommandError('Metadata requires the key{}'.format(
                        required_key))
        
        secrets = metadata['secrets']
        if (not isinstance(secrets, list) or not all(isinstance(x, basestring)
                for x in secrets)):
            raise CommandError('Secrets must be a list of strings')

        description_file = os.path.join(scenario_dir, 'description.creole')
        try:
            with open(description_file) as f_description:
                description = f_description.read()
        except IOError, e:
            raise CommandError('Could not read description: {}'.format(e))

        scenario_img = os.path.join(scenario_dir, 'scenario.img')
        if not os.path.exists(scenario_img):
            raise CommandError('File scenario.img is missing')
        if not os.path.isfile(scenario_img):
            raise CommandError('scenario.img is not a file')

        self._create_scenario(metadata, description, scenario_img)

    def _create_scenario(self, metadata, description, scenario_img):
        scenario, created = Scenario.objects.get(name=metadata['name'])
        was_enabled = scenario.enabled
        scenario.title = metadata['title']
        scenario.memory = metadata['memory']
        scenario.description = description
        scenario.enabled = False
        scenario.save()

        img_stat = os.stat(scenario_img)
        scenario_size = img_stat.st_size

        for node in scenario.get_nodes():
            try:
                volume = scenario.get_volume(node)
                volume.delete()
            except libvirt.libvirtError:
                pass
            
            pool = scenario.get_pool(node)
            xml_desc = """
            <volume>
              <name>{}</name>
              <capacity>{}</capacity>
            </volume>
            """.format(scenario.name, scenario_size)
            volume = pool.createXML(xml_desc, flags=0)
            stream = libvirt.virStream()
            stream.upload(volume, offset=0, length=scenario_size, flags=0)
            with open(scenario_img) as f_scenario:
                while True:
                    data = f_scenario.read(4096)
                    if not data:
                        stream.finish()
                        break
                    stream.send(data, len(data))

        if not created:
            scenario.enabled = was_enabled
            scenario.save()
