"""
A salt cloud provider that lets you use virtualbox on your machine
and act as a cloud.

For now this will only clone existing VMs. It's best to create a template
from which we will clone.

Followed
https://docs.saltstack.com/en/latest/topics/cloud/cloud.html#non-libcloud-based-modules
to create this.

Dicts provided by salt:
    __opts__ : contains the options used to run Salt Cloud,
        as well as a set of configuration and environment variables
"""

# Import python libs
import logging

# Import salt libs
import salt.config as config
import salt.utils.cloud

log = logging.getLogger(__name__)

# Import virtualbox libs
HAS_LIBS = False
try:
    # This code assumes vboxapi.py from VirtualBox distribution
    # being in PYTHONPATH, or installed system-wide
    from vboxapi import VirtualBoxManager

    HAS_LIBS = True

except ImportError:
    VirtualBoxManager = None
    log.error("Couldn't import VirtualBox API")

"""
The name salt will identify the lib by
"""
__virtualname__ = 'virtualbox'
_virtualboxManager = None


def __virtual__():
    """
    This function determines whether or not
    to make this cloud module available upon execution.
    Most often, it uses get_configured_provider() to determine
     if the necessary configuration has been set up.
    It may also check for necessary imports decide whether to load the module.
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
    """
    Return the first configured instance.
    """
    configured = config.is_provider_configured(
        __opts__,
        __active_provider_name__ or __virtualname__,
        ()  # keys we need from the provider configuration
    )
    log.debug("First virtualbox configuration %s" % configured)
    return configured


def create(vm_info):
    """
    Creates a virtual machine from the given VM information.
    This is what is used to request a virtual machine to be created by the
    cloud provider, wait for it to become available,
    and then (optionally) log in and install Salt on it.

    Fires:
        "starting create" : This event is tagged salt/cloud/<vm name>/creating.
        The payload contains the names of the VM, profile and provider.

    @param vm_info {dict}
            {
                name: <str>
                profile: <dict>
                provider: <provider>
                clone_from: <vm_name>
            }
    @return dict of resulting vm. !!!Passwords can and should be included!!!
    """
    log.debug("Creating virtualbox with %s" % vm_info)
    try:
        # Check for required profile parameters before sending any API calls.
        # TODO should this be a call to config.is_provider_configured ?
        if vm_info['profile'] and config.is_profile_configured(
                __opts__,
                __active_provider_name__ or 'virtualbox',
                vm_info['profile']
        ) is False:
            return False
    except AttributeError:
        pass

    # For now we can only clone
    if 'clone_from' not in vm_info:
        log.error('"clone_from" not in profile configuration!')
        return False

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

    # TODO Calculate kwargs with parameters required by virtualbox
    # to create the virtual machine.
    request_kwargs = {
        'name': vm_info['name'],
        'clone_from': vm_info['clone_from']
    }

    salt.utils.cloud.fire_event(
        'event',
        'requesting instance',
        'salt/cloud/{0}/requesting'.format(vm_info['name']),
        request_kwargs,
        transport=__opts__['transport']
    )
    # TODO request a new VM!
    vm_result = vb_clone_vm(**request_kwargs)

    # TODO Prepare deployment of salt on the vm
    # Any private data, including passwords and keys (including public keys)
    # should be stripped from the deploy kwargs before the event is fired.
    deploy_kwargs = {
    }

    salt.utils.cloud.fire_event(
        'event',
        'deploying salt',
        'salt/cloud/{0}/deploying'.format(vm_info['name']),
        deploy_kwargs,
        transport=__opts__['transport']
    )

    deploy_kwargs.update({
        # TODO Add private data
    })

    # TODO wait for target machine to become available
    # TODO deploy!
    # Do we have to call this?
    salt.utils.cloud.deploy_script(None, **deploy_kwargs)

    salt.utils.cloud.fire_event(
        'event',
        'created machine',
        'salt/cloud/{0}/created'.format(vm_info['name']),
        vm_result,
        transport=__opts__['transport']
    )

    # Passwords should be included in this object!!
    return vm_result


# -----------------------------
# Virtualbox methods
# -----------------------------

def vb_get_manager():
    # This code initializes VirtualBox manager with default style
    # and parameters
    global _virtualboxManager
    if _virtualboxManager is None:
        _virtualboxManager = VirtualBoxManager(None, None)
    vbox = _virtualboxManager.vbox
    return vbox


def vb_create_machine(name=None):
    vbox = vb_get_manager()
    log.info("Create virtualbox machine %s " % (name,))
    groups = None
    os_type_id = "Other"
    new_machine = vbox.createMachine(
        None,  # Settings file
        name,
        groups,
        os_type_id,
        None  # flags
    )
    vbox.registerMachine(new_machine)
    log.info("Finished creating %s" % name)


def vb_clone_vm(
        name=None,
        clone_from=None,
        timeout=10000):
    """
    Tells virtualbox to create a VM

    @return dict of resulting VM
    """
    vbox = vb_get_manager()
    log.info("Clone virtualbox machine %s from %s" % (name, clone_from))

    source_machine = vbox.findMachine(clone_from)

    groups = None
    osTypeId = "Other"
    new_machine = vbox.createMachine(
        None,  # Settings file
        name,
        groups,
        osTypeId,
        None  # flags
    )

    progress = source_machine.cloneTo(
        new_machine,
        0,  # CloneMode
        None  # CloneOptions : None = Full?
    )

    progress.waitForCompletion(timeout)
    log.info("Finished cloning %s from %s" % (name, clone_from))

    vbox.registerMachine(new_machine)

    # TODO return a struct/class that describes a virtual machine


def vb_start_vm(**kwargs):
    """
    Tells Virtualbox to start up a VM.
    Blocking function!

    @return dict of started VM, contains IP addresses and what not
    """
    pass


def vb_destroy_machine(name=None, timeout=10000):
    """

    @param timeout int timeout in milliseconds
    """
    vbox = vb_get_manager()
    log.info("Destroying machine %s" % name)
    machine = vbox.findMachine(name)
    files = machine.unregister(2)
    progress = machine.deleteConfig(files)
    progress.waitForCompletion(timeout)
    log.info("Finished destroying machine %s" % name)
