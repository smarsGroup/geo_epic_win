from ruamel.yaml import YAML
import os

class ConfigParser:

    def __init__(self, config_path):
        self.config_path = config_path
        self.dir = os.path.dirname(os.path.abspath(config_path))
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(sequence=4, offset=2)
        self.config_data = self.load()

    def _update_relative_paths(self, data):
        """Recursively update paths starting with './' in the data."""
        if isinstance(data, str) and data.startswith('./'):
            data = os.path.join(self.dir, data[2:])
            return data
        if isinstance(data, dict):
            data = data.copy()
            for key, value in data.items():
                    data[key] = self._update_relative_paths(value)
        return data

    def load(self):
        """Load data from the YAML file."""
        with open(self.config_path, 'r') as file:
            data = self.yaml.load(file)
        return data

    def save(self):
        """Save data to the YAML file."""
        with open(self.config_path, 'w') as file:
            self.yaml.dump(self.config_data, file)

    def _recursive_update(self, data, updates):
        """Recursively update dictionary values."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in data:
                data[key] = self._recursive_update(data[key].copy(), value)
            else:
                data[key] = value
        return data

    def update(self, updates):
        """Update the current config with new values."""
        self.config_data = self._recursive_update(self.config_data, updates)
        self.save()

    def get(self, key, default=None):
        """Retrieve a value from the configuration."""
        data = self.config_data.get(key, default)
        return self._update_relative_paths(data)
    
    def as_dict(self):
        data = self._update_relative_paths(self.config_data)
        return data
    
    def __getitem__(self, key):
        return self.get(key, None)

    def __repr__(self):
        return repr(self.config_data)
        
if __name__ == '__main__':
    # Example usage
    config = ConfigParser('config.yml')
    config.update({
        'soil': {
            'files_dir': './soil_files'
        },
        'Processed_Info': './processed_info.csv'
    })
    print(config.get('soil'))