import importlib
import os
import glob
import logging
from os.path import join, dirname, basename, isfile

from config.shared import Shared
from src.utils.credentials import get_credentials

# Configure logging
logger = logging.getLogger(__name__)

env = os.getenv('ENVIRONMENT', 'development')

modules = glob.glob(join(dirname(__file__), "*.py"))
supported_env = [basename(f)[:-3] for f in modules if
                 isfile(f) and not f.endswith('__init__.py') and 'shared' not in f]

assert env in supported_env, f"Not supported env: {env}"

env_conf = importlib.import_module("." + env, 'config')


def convert_class_to_json(obj):
    return {name: getattr(obj, name) for name in dir(obj) if not name.startswith('__')}


def convert_str_to_org_type(env_variable):
    if env_variable.isdigit():
        return int(env_variable)
    elif env_variable in ['True', 'true', 'False', 'false']:
        return env_variable in ['True', 'true']
    return env_variable


class GenericConf:
    def __init__(self, confs_list):
        for config in confs_list:
            props_dct = config if isinstance(config, dict) else convert_class_to_json(config)
            for k, v in props_dct.items():
                setattr(self, k, v)


shared_config = Shared()
env_conf = env_conf.Conf()
os_env = dict((k.lower(), v) if not v.isdigit() and v not in ['True', 'true', 'False', 'false'] else
              (k.lower(), convert_str_to_org_type(v)) for k, v in dict(os.environ).items())

try:
    if os.environ.get('TOKEN'):
        logger.info(f"TOKEN found, attempting to load config from vault using key: {env_conf.vault_config_key}")
        global_config = get_credentials(env_conf.vault_config_key)
        cfg = GenericConf([global_config, shared_config, env_conf, os_env])
        logger.info("Configuration loaded with vault credentials")
    else:
        logger.warning("No TOKEN provided, using local configuration only")
        cfg = GenericConf([shared_config, env_conf, os_env])
except Exception as e:
    logger.error(f"Error loading configuration: {str(e)}")
    logger.warning("Falling back to local configuration")
    cfg = GenericConf([shared_config, env_conf, os_env])

logger.info(f"Configuration loaded for environment: {env}")
print(cfg)
