# Ansible Nessus Agent module

This module, which is really just [a script in the library folder](./library/tenable_product.py), grabs and parses data from [Tenable's downloads page](https://www.tenable.com/downloads) to find the latest Nessus Agent package based on host machine info. The idea is that admins shouldn't need to manually download packages locally from Tenable's Downloads page and transfer them, but can instead rely on Ansible facts to automatically install/configure software across their hosts.

It's only been tested on Ubuntu, RHEL, and Amazon hosts, but should work for all of the Linux distributions that Tenable has Nessus Agents packages for. See [./run.yml](./run.yml) for an idempotent example which downloads, installs, and configures Nessus Agents on a given [inventory](./inventory/all.yml). Note, for this playbook you'd want to provide a value to `nessus_key` somewhere, like in the appropriate [group_vars](./inventory/group_vars/all.yml) file, and assumes you don't want to force uninstall/install an existing working nessus agent to the latest version.

## Example

Say you manage many hetereogenous hosts, all with different linux distributions and you want to configure some of them to use `key1`, under `group1`, and the rest to use `key2` under `group2`. Instead of determining which Tenable Nessus Agent package to download and manually installing it on each of them (yuck), you can change the [./inventory/all.yml](./inventory/all.yml) to [define the two groups](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/yaml_inventory.html) with the right config, like below, and just run `ansible-playbook run.yml` in this project's root directory to do all of that automatically. (We're assuming you've already made sure your SSH config and the ansible package is installed, of course.) If it's already installed/configured, no problem, this won't unenroll or disrupt your host's nessus service because it's been written to check if the agent's working already.

```yaml
all:
  vars:
    agent_host: cloud.tenable.com 
    agent_port: 443
    nessus_key: "supersecretkeygoeshere"
  children:
    nessus1:
    nessus2:
nessus1:
  vars:
    agent_group: "tenablegroup1"
    nessus_key: "key1"
  hosts:
    host11:
    # ...
    host1n:
nessus2:
  vars:
    agent_group: "tenablegroup2"
    nessus_key: "key2"
  hosts:
    host21:
    # ...
    host2n:
```

Feel free to copy/modify and use the script.
