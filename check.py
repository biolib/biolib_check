"""
Standalone script to validate a .biolib/config.yml file using the same validation
logic as in the BioLib CI/CD pipeline.
"""

import argparse
import os
import sys
import yaml
from typing import Dict, Any, Optional

class ValidationError(Exception):
    def __init__(self, detail=None):
        self.detail = detail
        super().__init__(detail)

class ObjectDoesNotExist(Exception):
    pass

class NotFound(Exception):
    pass

class Serializer:
    class ValidationError(Exception):
        def __init__(self, detail=None):
            self.detail = detail
            super().__init__(detail)

class EnvironmentsEnum:
    BIOLIB_APP = "biolib-app"
    BIOLIB_CUSTOM = "biolib-custom"
    APP_DATA = "app-data"

class AllowedYAMLEnvironments:
    BIOLIB_APP = "biolib-app"
    DOCKERHUB = "dockerhub"
    LOCAL_DOCKER = "local-docker"
    APP_DATA = "app-data"

    @classmethod
    def values(cls):
        return [cls.BIOLIB_APP, cls.DOCKERHUB, cls.LOCAL_DOCKER, cls.APP_DATA]

class ModuleGpuPreference:
    DISABLED = "disabled"
    REQUIRED = "required"
    PREFERRED = "preferred"

    @classmethod
    def values(cls):
        return [cls.DISABLED, cls.REQUIRED, cls.PREFERRED]

class ResourceType:
    LFS = "lfs"

class GpuType:
    AWS_G4 = "aws-g4"

class Action:
    READ = "read"

custom_executors = {
    "python": {"versions": ["3.7", "3.8", "3.9", "3.10"], "latest": "3.10"},
    "r": {"versions": ["4.0", "4.1", "4.2"], "latest": "4.2"},
    "node": {"versions": ["14", "16", "18"], "latest": "18"},
}

old_to_new_executors_map = {
    "python": "python",
    "r": "r",
    "node": "node",
}

biolib_machine_type_to_resource_requirements = {
    "cpu.micro": {"cpu_in_nano_shares": 1000000000, "memory_in_bytes": 1000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.small": {"cpu_in_nano_shares": 1000000000, "memory_in_bytes": 4000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.medium": {"cpu_in_nano_shares": 2000000000, "memory_in_bytes": 8000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.large": {"cpu_in_nano_shares": 4000000000, "memory_in_bytes": 16000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.xlarge": {"cpu_in_nano_shares": 8000000000, "memory_in_bytes": 32000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.2xlarge": {"cpu_in_nano_shares": 16000000000, "memory_in_bytes": 64000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.4xlarge": {"cpu_in_nano_shares": 32000000000, "memory_in_bytes": 128000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.8xlarge": {"cpu_in_nano_shares": 64000000000, "memory_in_bytes": 256000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.16xlarge": {"cpu_in_nano_shares": 128000000000, "memory_in_bytes": 512000000000, "gpu_count": 0, "gpu_type": None},
    "cpu.24xlarge": {"cpu_in_nano_shares": 192000000000, "memory_in_bytes": 768000000000, "gpu_count": 0, "gpu_type": None},
    
    "memory.2xlarge": {"cpu_in_nano_shares": 16000000000, "memory_in_bytes": 128000000000, "gpu_count": 0, "gpu_type": None},
    
    "gpu.small": {"cpu_in_nano_shares": 4000000000, "memory_in_bytes": 16000000000, "gpu_count": 1, "gpu_type": GpuType},
    "gpu.medium": {"cpu_in_nano_shares": 4000000000, "memory_in_bytes": 16000000000, "gpu_count": 1, "gpu_type": GpuType},
    "gpu.large": {"cpu_in_nano_shares": 8000000000, "memory_in_bytes": 32000000000, "gpu_count": 1, "gpu_type": GpuType},
    "gpu.xlarge": {"cpu_in_nano_shares": 16000000000, "memory_in_bytes": 64000000000, "gpu_count": 1, "gpu_type": GpuType},
    "gpu.2xlarge": {"cpu_in_nano_shares": 32000000000, "memory_in_bytes": 128000000000, "gpu_count": 1, "gpu_type": GpuType},
    
    "aws-g5.12xlarge": {"cpu_in_nano_shares": 48000000000, "memory_in_bytes": 192000000000, "gpu_count": 4, "gpu_type": GpuType},
    "aws-g5.48xlarge": {"cpu_in_nano_shares": 192000000000, "memory_in_bytes": 768000000000, "gpu_count": 8, "gpu_type": GpuType},
    "aws-g6e.xlarge": {"cpu_in_nano_shares": 4000000000, "memory_in_bytes": 32000000000, "gpu_count": 1, "gpu_type": GpuType},
    "aws-g6e.2xlarge": {"cpu_in_nano_shares": 8000000000, "memory_in_bytes": 64000000000, "gpu_count": 1, "gpu_type": GpuType},
    "aws-g6e.4xlarge": {"cpu_in_nano_shares": 16000000000, "memory_in_bytes": 128000000000, "gpu_count": 1, "gpu_type": GpuType},
    "aws-g6e.8xlarge": {"cpu_in_nano_shares": 32000000000, "memory_in_bytes": 256000000000, "gpu_count": 1, "gpu_type": GpuType},
    "aws-g6e.16xlarge": {"cpu_in_nano_shares": 64000000000, "memory_in_bytes": 512000000000, "gpu_count": 1, "gpu_type": GpuType},
    "aws-r6a.32xlarge": {"cpu_in_nano_shares": 128000000000, "memory_in_bytes": 1024000000000, "gpu_count": 0, "gpu_type": None},
    
    "small": {"cpu_in_nano_shares": 1000000000, "memory_in_bytes": 2000000000, "gpu_count": 0, "gpu_type": None},
    "medium": {"cpu_in_nano_shares": 2000000000, "memory_in_bytes": 4000000000, "gpu_count": 0, "gpu_type": None},
    "large": {"cpu_in_nano_shares": 4000000000, "memory_in_bytes": 8000000000, "gpu_count": 0, "gpu_type": None},
    "gpu-small": {"cpu_in_nano_shares": 2000000000, "memory_in_bytes": 4000000000, "gpu_count": 1, "gpu_type": GpuType},
}

stdout_render_types = [
    ("text", "Text"),
    ("markdown", "Markdown"),
    ("html", "HTML"),
]

render_types = [
    ("drag-and-drop-file", "Drag and Drop File"),
    ("drag-and-drop-files", "Drag and Drop Files"),
    ("dropdown", "Dropdown"),
    ("file", "File"),
    ("group", "Group"),
    ("hidden", "Hidden"),
    ("multifile", "Multifile"),
    ("multiselect", "Multiselect"),
    ("number", "Number"),
    ("radio", "Radio"),
    ("sequence", "Sequence"),
    ("sequence-beta", "Sequence Beta"),
    ("text", "Text"),
    ("text-file", "Text File"),
    ("textarea", "Textarea"),
    ("toggle", "Toggle"),
]

def validate_app_version(yaml_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate app version configuration."""
    error_dict = {}
    validate_unsupported_root_level_fields(yaml_data, error_dict)
    validate_reserved_machines(yaml_data, error_dict)
    validate_output_type(yaml_data, error_dict)
    validate_main_output_file_path(yaml_data, error_dict)
    validate_consumes_stdin(yaml_data, error_dict)
    validate_requires_user_identity(yaml_data, error_dict)
    validate_remote_hosts(yaml_data, error_dict)
    validate_citation(yaml_data, error_dict)
    validate_description_file(yaml_data, error_dict)
    validate_license_file(yaml_data, error_dict)
    return error_dict

def validate_unsupported_root_level_fields(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate that only supported root level fields are present."""
    supported_fields = [
        'arguments',
        'biolib_version',
        'citation',
        'consumes_stdin',
        'description_file',
        'license_file',
        'modules',
        'output_type',
        'remote_hosts',
        'requires_user_identity',
        'source_files_ignore',
        'main_output_file',
        'reserved_machines',
        'app_data',
        'auto_run_once_validation_passes',
    ]

    errors = []
    for field in yaml_data.keys():
        if field not in supported_fields:
            errors.append(f'The field {field} is not valid')

    if errors:
        error_dict['unsupported_fields'] = errors

def validate_reserved_machines(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate reserved_machines field."""
    reserved_machines_max = 25

    if 'reserved_machines' in yaml_data.keys():
        reserved_machines = yaml_data['reserved_machines']
        if not isinstance(reserved_machines, int) or reserved_machines < 1:
            error_dict['reserved_machines'] = ['reserved_machines must be a positive integer']
        elif reserved_machines > reserved_machines_max:
            error_dict['reserved_machines'] = [f'reserved_machines must be less than {reserved_machines_max}']

def validate_output_type(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate output_type field."""
    if 'output_type' in yaml_data.keys():
        if 'main_output_file' in yaml_data.keys():
            error_dict['output_type'] = [
                f'output_type and main_output_file can not be specified at the same time'
            ]
            return
        output_type = yaml_data['output_type']
        stdout_render_types_choices = [type_tuple[0] for type_tuple in stdout_render_types]
        if output_type not in stdout_render_types_choices:
            error_dict['output_type'] = [
                f'Invalid output_type specified for your app. output_type can be one of {stdout_render_types_choices}'
            ]

def validate_main_output_file_path(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate main_output_file field."""
    if 'main_output_file' in yaml_data.keys():
        main_output_file = yaml_data['main_output_file']
        if not isinstance(main_output_file, str):
            error_dict['main_output_file'] = [
                f'Invalid main_output_file specified for your app. main_output_file must be a string'
            ]
            return

        if not main_output_file.startswith('/'):
            error_dict['main_output_file'] = [
                f'Path to main_output_file must be absolute (start with "/")'
            ]

def validate_consumes_stdin(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate consumes_stdin field."""
    if 'consumes_stdin' in yaml_data.keys():
        consumes_stdin = yaml_data['consumes_stdin']
        if not isinstance(consumes_stdin, bool):
            error_dict['consumes_stdin'] = [
                f'Invalid consumes_stdin specified for your app. consumes_stdin can be true or false'
            ]

def validate_requires_user_identity(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate requires_user_identity field."""
    if 'requires_user_identity' in yaml_data.keys():
        if not isinstance(yaml_data['requires_user_identity'], bool):
            error_dict['requires_user_identity'] = [
                f'Invalid requires_user_identity specified for your app. requires_user_identity can be true or false'
            ]

def validate_remote_hosts(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate remote_hosts field."""
    if 'remote_hosts' in yaml_data.keys():
        remote_hosts = yaml_data['remote_hosts']
        if not isinstance(remote_hosts, list):
            error_dict['remote_hosts'] = [
                f'Invalid remote_hosts specified for your app. remote_hosts must be a list of hostnames'
            ]
            return
        
        for host in remote_hosts:
            if not isinstance(host, str):
                error_dict['remote_hosts'] = [
                    f'Invalid hostname in remote_hosts. All hostnames must be strings'
                ]
                return

def validate_citation(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate citation field."""
    if 'citation' in yaml_data.keys():
        citation = yaml_data['citation']
        if not isinstance(citation, dict):
            error_dict['citation'] = [
                f'Invalid citation specified for your app. citation must be a dictionary'
            ]
            return
        
        if 'entry_type' not in citation:
            error_dict['citation'] = [
                f'Missing entry_type in citation. entry_type is required'
            ]
            return
        
        required_fields = ['entry_type']
        
        if 'year' in citation and not isinstance(citation['year'], str):
            error_dict['citation'] = [
                f'Year in citation must be a string'
            ]

def validate_description_file(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate description_file field."""
    if 'description_file' in yaml_data.keys():
        description_file = yaml_data['description_file']
        if not isinstance(description_file, str):
            error_dict['description_file'] = [
                f'Invalid description_file specified for your app. description_file must be a string'
            ]

def validate_license_file(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate license_file field."""
    if 'license_file' in yaml_data.keys():
        license_file = yaml_data['license_file']
        if not isinstance(license_file, str):
            error_dict['license_file'] = [
                f'Invalid license_file specified for your app. license_file must be a string'
            ]

def validate_and_get_biolib_yaml_version(yaml_data: Dict[str, Any]) -> int:
    """Validate biolib_version field and return its value."""
    if 'biolib_version' not in yaml_data.keys():
        raise ValidationError({'config_yml': ['Your config file is missing the biolib_version field.']})
    else:
        biolib_version = yaml_data['biolib_version']

    if biolib_version != 2:
        raise ValidationError({'config_yml': [
            'BioLib version must be 2. Please update ".biolib/config.yml" to "biolib_version: 2"'
        ]})

    return biolib_version

def validate_task(name: str, task_data: Any, yaml_version: int) -> Dict[str, Any]:
    """Validate a task configuration."""
    error_dict = {}
    name = validate_name(name, error_dict)
    if not name:
        return error_dict
    
    error_dict[name] = {}
    task_error_dict = error_dict[name]
    
    if yaml_version == 1:
        if isinstance(task_data, str):
            pass
        else:
            validate_unsupported_task_fields(name, task_data, task_error_dict, yaml_version)
            validate_executor(name, task_data, task_error_dict)
    else:
        validate_unsupported_task_fields(name, task_data, task_error_dict, yaml_version)
        validate_mappings(name, task_data, task_error_dict, mapping_type='input_files')
        validate_mappings(name, task_data, task_error_dict, mapping_type='output_files')
        validate_mappings(name, task_data, task_error_dict, mapping_type='source_files')
        validate_image(name, task_data, task_error_dict, yaml_version)
        validate_gpu(task_data, task_error_dict)
        validate_default_machine(task_data, task_error_dict)
        validate_disable_default_machine_override(task_data, task_error_dict)

    validate_working_directory(name, task_data, task_error_dict)

    if error_dict[name]:
        return error_dict
    else:
        return {}

def validate_name(name: str, error_dict: Dict[str, Any]) -> Optional[str]:
    """Validate a task name."""
    import re
    
    if not re.match("^[A-Za-z0-9_-]+$", name):
        error_dict[name] = [f'The module name {name} is invalid, it can only contain alphanumeric characters.']
        return None

    if re.search("(--)|(__)|(-_)|(_-)", name):
        error_dict[name] = [f'The module name {name} is invalid, it can not contain consecutive dashes or underscores']
        return None

    if re.match("^(-|_)[A-Za-z0-9_-]+$", name):
        error_dict[name] = [f'The module name {name} is invalid, it can not start with dashes or underscores']
        return None

    if re.match("^[A-Za-z0-9_-]+(-|_)$", name):
        error_dict[name] = [f'The module name {name} is invalid, it can not end with dashes or underscores']
        return None

    return name

def validate_working_directory(name: str, task_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate working_directory field."""
    if 'working_directory' in task_data:
        if not task_data['working_directory'].startswith('/'):
            error_dict['working_directory'] = [
                f'Wrong path format on working_directory for {name}. Directory path must be an absolute path'
            ]
            return

        if not task_data['working_directory'].endswith('/'):
            error_dict['working_directory'] = [
                f'Wrong path format on working_directory for {name}. Directories must end in a slash: "/dir/sub_dir/"'
            ]
            return

        if '//' in task_data['working_directory']:
            error_dict['working_directory'] = [
                f'Wrong path format on working_directory for {name}. Directories can not have consecutive slashes"'
            ]

def validate_executor(name: str, task_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate executor field."""
    if 'executor' not in task_data.keys():
        error_dict['executor'] = [
            'You must define an executor in your module definition; '
            'Make sure you follow the format executor_name:version'
        ]
        return

    if task_data['executor'].count(':') != 1:
        error_dict['executor'] = [
            f'Executor {task_data["executor"]} on module {name} is invalid. Please only use ":" to separate to and from paths i.e. "from:to".'
        ]
        return

    executor, version = task_data['executor'].split(':')
    if executor not in old_to_new_executors_map.keys():
        error_dict['executor'] = [
            f'You provided an invalid executor in module {name}; '
            'Make sure you follow the format executor_name:version'
        ]

    new_executor_name = old_to_new_executors_map[executor]
    supported_versions = custom_executors[new_executor_name]['versions'] + ['*']
    if version not in supported_versions:
        error_dict['image'] = [
            f'Invalid version for executor {executor} on module {name}. The supported versions for {executor} are {supported_versions}'
        ]
        return

def validate_mappings(name: str, task_data: Dict[str, Any], error_dict: Dict[str, Any], mapping_type: str) -> None:
    """Validate file mappings."""
    import re
    
    if mapping_type not in task_data:
        if not mapping_type == "source_files" and not task_data.get('image', '').startswith(f'{AllowedYAMLEnvironments.APP_DATA}://'):
            error_dict[mapping_type] = [
                f'{mapping_type} field on module {name} is required. Please specify your {mapping_type}.'
            ]
        return

    if not isinstance(task_data[mapping_type], list):
        error_dict[mapping_type] = [
            f'{mapping_type} field on module {name} is invalid. Please format the field as a yaml array.'
        ]
        return

    for mapping in task_data.get(mapping_type):
        mapping_parts = mapping.split(' ')
        if len(mapping_parts) != 3:
            error_dict[mapping_type] = [
                f'{mapping_type} item {mapping} on module {name} is invalid. Please use the format "COPY from_path to_path" i.e. "COPY / /home/biolib/"'
            ]
            return

        if mapping_parts[0] != 'COPY':
            error_dict[mapping_type] = [
                f'{mapping_type} item {mapping} on module {name} is missing the COPY command. Please use the format "COPY from_path to_path" i.e. "COPY / /home/biolib/"'
            ]
            return

        from_path = mapping_parts[1]
        to_path = mapping_parts[2]

        if '$' in re.sub(r"\$[1-9][0-9]*", "", from_path):
            error_dict[mapping_type] = [
                f'{mapping_type} item {mapping} on module {name} in path "{from_path}" is using an invalid variable. '
                'Please only use variables referring to an argument number, where "$1" refers to the first argument '
                'i.e. "COPY $1 /home/biolib/$1"'
            ]
            return

        if '$' in re.sub(r"\$[1-9][0-9]*", "", to_path):
            error_dict[mapping_type] = [
                f'{mapping_type} item {mapping} on module {name} in path "{to_path}" is using an invalid variable. '
                'Please only use variables referring to an argument number, where "$1" refers to the first argument '
                'i.e. "COPY $1 /home/biolib/$1"'
            ]
            return

        to_path_with_vars_replaced_with_dollar = re.sub("\$[0-9]+", "$", to_path)
        if from_path.endswith('/') and (not to_path.endswith('/') and
                                        not to_path_with_vars_replaced_with_dollar.endswith('$')):
            error_dict[mapping_type] = [
                f'{mapping_type} item {mapping} on module {name} is invalid. Directories can only map to other directories'
            ]
            return

        if not to_path.startswith('/') and not to_path.startswith('$'):
            error_dict[mapping_type] = [
                f'{mapping_type} item {mapping} on module {name} on path "{to_path}" is invalid. Only absolute paths allowed'
            ]
            return

        if not from_path.startswith('/') and not from_path.startswith('$'):
            error_dict[mapping_type] = [
                f'{mapping_type} item {mapping} on module {name} on path "{from_path}" is invalid. Only absolute paths allowed'
            ]
            return

        if '//' in from_path or '//' in to_path:
            error_dict[mapping_type] = [
                f'{mapping_type} item {mapping} on module {name} is invalid. Directories can not have consecutive slashes'
            ]

def validate_image(name: str, task_data: Dict[str, Any], error_dict: Dict[str, Any], yaml_version: int) -> None:
    """Validate image field."""
    if 'image' not in task_data:
        error_dict['image'] = [
            f'You must define an image to use for module {name}.'
        ]
        return

    image = task_data['image']
    if '://' not in image:
        error_dict['image'] = [
            f'Wrong image format on module {name}. You must define an image using the following format "environment://image_name:version"'
        ]
        return

    environment = image.split('://')[0]
    if environment not in AllowedYAMLEnvironments.values():
        error_dict['image'] = [
            f'Wrong environment on image of module {name}. The environment should be specified before "://" and can be only be one of {AllowedYAMLEnvironments.values()}'
        ]

    if image.startswith(f'{AllowedYAMLEnvironments.BIOLIB_APP}://biolib/'):
        uri = image.replace(f'{AllowedYAMLEnvironments.BIOLIB_APP}://biolib/', '', 1)
        if uri.count(':') != 1:
            error_dict['image'] = [
                f'Missing version on the image of module {name}. A version must be specified at the end of the image like so: "environment://image_name:version"'
            ]
            return

        executor, version = uri.split(':')
        if executor not in custom_executors.keys():
            error_dict['image'] = [
                f'Invalid image name biolib/{executor} for biolib executor on module {name}. The supported biolib executors are {["biolib/" + executor for executor in custom_executors.keys()]}'
            ]
            return

        supported_versions = custom_executors[executor]['versions'] + ['*']
        if version not in supported_versions:
            error_dict['image'] = [
                f'Invalid version for biolib executor {executor} on module {name}. The supported versions for {executor} are {supported_versions}'
            ]
            return

def validate_gpu(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate gpu field."""
    if 'gpu' in yaml_data.keys():
        if yaml_data['gpu'] not in ModuleGpuPreference.values():
            error_dict['gpu'] = [
                f'Invalid value for "gpu". You can specify one of {ModuleGpuPreference.values()}'
            ]

def validate_default_machine(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate default_machine field."""
    if 'default_machine' in yaml_data:
        if yaml_data['default_machine'] not in biolib_machine_type_to_resource_requirements:
            error_dict['default_machine'] = ['Invalid machine type']

        if 'gpu' in yaml_data:
            error_dict['default_machine'] = ['Cannot be specified with the "gpu" option']

def validate_disable_default_machine_override(yaml_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate disable_default_machine_override field."""
    if 'disable_default_machine_override' in yaml_data:
        if not isinstance(yaml_data['disable_default_machine_override'], bool):
            error_dict['disable_default_machine_override'] = ['Must be boolean']

def validate_unsupported_task_fields(name: str, task_data: Dict[str, Any], error_dict: Dict[str, Any], yaml_version: int) -> None:
    """Validate that only supported task fields are present."""
    if not isinstance(task_data, dict):
        error_dict['unsupported_fields'] = [
            f'Module {name} is the wrong type. Modules can only be a YAML dict in version {yaml_version}'
        ]
        return

    supported_task_fields_base = [
        'working_directory',
    ]

    supported_task_fields_v1 = [
        'executor',
        'path'
    ]

    supported_task_fields_v2 = [
        'image',
        'input_files',
        'output_files',
        'source_files',
        'large_file_systems',
        'data_records',
        'command',
        'gpu',
        'secrets',
        'default_machine',
        'disable_default_machine_override',
    ]

    if yaml_version == 1:
        supported_fields = supported_task_fields_base + supported_task_fields_v1
    else:
        supported_fields = supported_task_fields_base + supported_task_fields_v2

    errors = []
    for field in task_data.keys():
        if field not in supported_fields:
            if field in ('required_cpu_in_nano_shares', 'required_memory_in_bytes'):
                errors.append(f'The field "{field}" has been deprecated please use "default_machine" instead')
            else:
                errors.append(f'The field "{field}" on module "{name}" is invalid for "biolib_version: {yaml_version}"')

    if errors:
        error_dict['unsupported_fields'] = errors

def validate_argument(argument_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an argument configuration."""
    error_dict = {}
    key = validate_key(argument_data, error_dict)
    if key is None:
        return error_dict

    error_dict[key] = {}
    argument_error_dict = error_dict[key]

    validate_unsupported_argument_fields(key, argument_data, argument_error_dict)

    sub_arguments = argument_data.get('sub_arguments', {})
    group_arguments = argument_data.get('group_arguments', [])

    if sub_arguments and group_arguments:
        argument_error_dict['sub_arguments'] = ['Only one of `sub_arguments` or `group_arguments` can be specified']

    validate_required(key, argument_data, argument_error_dict)
    type_value = validate_type(key, argument_data, argument_error_dict)

    if not type_value:
        return error_dict

    validate_description(key, argument_data, type_value, argument_error_dict)

    if error_dict[key]:
        return error_dict
    else:
        return {}

def validate_key(argument_data: Dict[str, Any], error_dict: Dict[str, Any]) -> Optional[str]:
    """Validate argument key."""
    if 'key' not in argument_data.keys():
        error_dict['required'] = [
            f'One of your arguments is missing a key. Please specify a key for each of your arguments'
        ]
        return None
    else:
        return argument_data['key']

def validate_required(key: str, argument_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate required field."""
    if 'required' in argument_data.keys():
        if not isinstance(argument_data['required'], bool):
            error_dict['required'] = [
                f'Invalid value in required specified on {key} argument. required can be true or false'
            ]

def validate_type(key: str, argument_data: Dict[str, Any], error_dict: Dict[str, Any]) -> Optional[str]:
    """Validate type field."""
    if 'type' in argument_data.keys():
        render_types_choices = [type_tuple[0] for type_tuple in render_types]
        type_value = argument_data['type']
        if type_value not in render_types_choices:
            error_dict['type'] = [
                f'Invalid value {type_value} in type specified on {key} argument '
                f'type can be one of {render_types_choices}'
            ]
            return ''

        if type_value == 'toggle':
            if 'options' not in argument_data:
                error_dict['type'] = [
                    f'There must be exactly 2 options ("on" and "off") on arguments of type toggle'
                ]
                return ''

            number_of_options = len(argument_data['options'].keys())

            if number_of_options != 2:
                error_dict['type'] = [
                    f'There must be exactly 2 options ("on" and "off") on arguments of type toggle. Received '
                    f'{number_of_options} options'
                ]
                return ''

            option_names = list(argument_data['options'].keys())

            if option_names not in (['on', 'off'], ['off', 'on']):
                error_dict['type'] = [
                    f'The two options on arguments of type toggle must be named "on" and "off". Received '
                    f'{", ".join(option_names)}'
                ]
                return ''

        return type_value
    return None

def validate_description(key: str, argument_data: Dict[str, Any], type_value: str, error_dict: Dict[str, Any]) -> None:
    """Validate description field."""
    if 'description' not in argument_data.keys() and type_value != 'hidden':
        error_dict['argument_description'] = [
            f'Could not find a description for argument {key}. Please provide a description for {key}'
        ]

def validate_unsupported_argument_fields(key: str, argument_data: Dict[str, Any], error_dict: Dict[str, Any]) -> None:
    """Validate that only supported argument fields are present."""
    supported_argument_fields = [
        'default_value',
        'description',
        'do_not_pass_if_value_empty',
        'exclude_value',
        'key',
        'key_value_separator',
        'options',
        'required',
        'sub_arguments',
        'type',
        'group_arguments',
        'group_separator',
        'group_argument_separator',
    ]

    for field in argument_data.keys():
        if field not in supported_argument_fields:
            error_dict['unsupported_field'] = [
                f'The argument field {field} on {key} is not valid'
            ]

def validate_tasks(yaml_data: Dict[str, Any], yaml_version: int) -> Dict[str, Any]:
    """Validate tasks in the YAML configuration."""
    error_dict = {'modules': {}}
    if 'modules' in yaml_data:
        for name, task_data in yaml_data['modules'].items():
            task_errors = validate_task(
                name=name,
                task_data=task_data,
                yaml_version=yaml_version,
            )
            if task_errors:
                error_dict['modules'].update(task_errors)

    if error_dict['modules']:
        return error_dict
    else:
        return {}

def validate_arguments(yaml_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate arguments in the YAML configuration."""
    error_dict = {'arguments': {}}
    if 'arguments' in yaml_data:
        for argument in yaml_data['arguments']:
            argument_errors = validate_argument(argument)
            if argument_errors:
                error_dict['arguments'].update(argument_errors)

    if error_dict['arguments']:
        return error_dict
    else:
        return {}

def validate_yaml_config(yaml_data: Dict[str, Any], yaml_version: int) -> None:
    """Validate the YAML configuration."""
    error_dict = {'config_yml': {}}
    
    app_version_errors = validate_app_version(yaml_data)
    if app_version_errors:
        error_dict['config_yml'].update(app_version_errors)
    
    task_errors = validate_tasks(yaml_data, yaml_version)
    if task_errors:
        error_dict['config_yml'].update(task_errors)
    
    argument_errors = validate_arguments(yaml_data)
    if argument_errors:
        error_dict['config_yml'].update(argument_errors)
    
    if error_dict['config_yml']:
        raise ValidationError(error_dict)

def print_validation_errors(error: ValidationError) -> None:
    """Print validation errors in a user-friendly format."""
    print("Validation errors:")
    
    if isinstance(error.detail, dict):
        for section, section_errors in error.detail.items():
            print(f"\n[{section}]")
            
            if isinstance(section_errors, dict):
                for field, field_errors in section_errors.items():
                    print(f"  {field}:")
                    if isinstance(field_errors, list):
                        for err in field_errors:
                            if isinstance(err, str):
                                print(f"    - {err}")
                            elif isinstance(err, dict):
                                for sub_field, sub_errors in err.items():
                                    print(f"    - {sub_field}: {', '.join(sub_errors)}")
                    else:
                        print(f"    - {field_errors}")
            elif isinstance(section_errors, list):
                for err in section_errors:
                    print(f"  - {err}")
            else:
                print(f"  {section_errors}")
    else:
        print(error.detail)

def main():
    """Main function to validate a config.yml file."""
    parser = argparse.ArgumentParser(description='Validate a .biolib/config.yml file.')
    parser.add_argument('config_file', help='Path to the config.yml file')
    args = parser.parse_args()
    
    config_file = args.config_file
    
    if not os.path.exists(config_file):
        print(f"Error: File '{config_file}' does not exist.")
        sys.exit(1)
    
    try:
        with open(config_file, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        if yaml_data is None:
            print("Error: Empty YAML file.")
            sys.exit(1)
        
        yaml_version = validate_and_get_biolib_yaml_version(yaml_data)
        
        validate_yaml_config(yaml_data, yaml_version)
        
        print(f"Validation successful: '{config_file}' is valid.")
        sys.exit(0)
        
    except yaml.YAMLError as e:
        print(f"Error: Malformed YAML: {e}")
        sys.exit(1)
    except ValidationError as e:
        print_validation_errors(e)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()