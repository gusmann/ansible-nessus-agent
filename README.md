# Ansible Nessus Agent module

This module, which is really just [a script in the library folder](./library/tenable_product.py), grabs and parses data from [Tenable's downloads page](https://www.tenable.com/downloads) to find the latest Nessus Agent package based on host machine info. The idea is that admins shouldn't need to manually download packages locally from Tenable's Downloads page and transfer them, but can instead rely on Ansible facts to automatically install/configure software across their hosts.

It's only been tested on Ubuntu, RHEL, and Amazon hosts, but should work for all of the Linux distributions that Tenable has Nessus Agents packages for. See [./run.yml](./run.yml) for an idempotent example which downloads, installs, and configures Nessus Agents on a given [inventory](./inventory/all.yml). Note, for this playbook you'd want to provide a value to `nessus_key` somewhere, like in the appropriate [group_vars](./inventory/group_vars/all.yml) file, and assumes you don't want to force uninstall/install an existing working nessus agent to the latest version.

Feel free to copy/modify and use the script.