"""
A salt cloud provider that lets you control virtualbox on your machine and act as a cloud.

Followed https://docs.saltstack.com/en/latest/topics/cloud/cloud.html#non-libcloud-based-modules
to create this.

Dicts provided by salt:
    __opts__ : contains the options used to run Salt Cloud, as well as a set of configuration and environment variables
"""

# Import python libs
import copy
import logging
import pprint
import time
import yaml

# Import salt libs
import salt.config as config
from salt.exceptions import SaltCloudSystemExit
import salt.utils.cloud

# Import virtualbox libs
HAS_LIBS = False
try:
    # This code assumes vboxapi.py from VirtualBox distribution
    # being in PYTHONPATH, or installed system-wide
    from vboxapi import VirtualBoxManager

    HAS_LIBS = True

except ImportError:
    pass


log = logging.getLogger(__name__)

def __virtual__():
    """
    This function determines whether or not to make this cloud module available upon execution.
    Most often, it uses get_configured_provider() to determine
     if the necessary configuration has been set up.
    It may also check for necessary imports, to decide whether to load the module.
    In most cases, it will return a True or False value.
    If the name of the driver used does not match the filename,
     then that name should be returned instead of True.

    @return True|False|str
    """

    if not HAS_LIBS:
        return False

    if get_configured_provider() is False:
        return False

    # If the name of the driver used does not match the filename,
    #  then that name should be returned instead of True.
    # return __virtualname__
    return True

def get_configured_provider():
    '''
    Return the first configured instance.
    '''
    return config.is_provider_configured(
        __opts__,
        __active_provider_name__ or __virtualname__,
        ('subscription_id', 'certificate_path')
    )

def create(vm_info):
    """
    Creates a virtual machine from the given VM information.
    This is what is used to request a virtual machine to be created by the cloud provider, wait for it to become available, and then (optionally) log in and install Salt on it.

    Fires:
        "starting create" : This event is tagged salt/cloud/<vm name>/creating. The payload contains the names of the VM, profile and provider.

    @param vm_info {dict}
            {
                name: <str>
                profile: <dict>
                provider: <provider>
            }
    """
    salt.utils.cloud.fire_event(
        'event',
        'starting create',
        'salt/cloud/{0}/creating'.format(vm_info['name']),
        {
            'name': vm_info['name'],
            'profile': vm_info['profile'],
            'provider': vm_info['provider'],
        },
        transport=__opts__['transport']
    )