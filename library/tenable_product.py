#!/usr/bin/python
from __future__ import (absolute_import, division, print_function)
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import re
import html.parser
import logging


import requests

TENABLE_DOWNLOAD_API_URI = "https://www.tenable.com/downloads/api/v1/public/pages/nessus-agents/downloads/{product_id}/download?i_agree_to_tenable_license_agreement=true"
logger = logging.getLogger(__name__)

def to_dict(obj):
    return json.loads(json.dumps(obj, default=lambda o: o.__dict__))

def is_equivalent_architecture(arch1, arch2):
  """Checks if two architectures are equivalent, considering common aliases.

  Supported architectures and their aliases:
    x86_64: amd64, x86-64
    armv7l: arm
    aarch64: arm64
  """
  arch1_lower = arch1.lower()
  arch2_lower = arch2.lower()

  equivalences = {
      "x86_64": ("amd64", "x86-64"),
      "armv7l": ("arm",),
      "aarch64": ("arm64",),
  }

  # Check if either architecture is an alias of the other
  for base_arch, aliases in equivalences.items():
    if arch1_lower == base_arch and arch2_lower in aliases:
      return True
    elif arch2_lower == base_arch and arch1_lower in aliases:
      return True

  # Check for exact match (case-sensitive)
  return arch1_lower == arch2_lower

def is_equivalent_distro(distro1, major_version, distro2):
  """Checks if two Linux distributions are equivalent based on a provided mapping.

  Args:
      distro1: First distribution string (case-insensitive).
      distro2: Second distribution string (case-insensitive).

  Returns:
      True if the distributions are considered equivalent, False otherwise.
  """
  distro1_lower = distro1.lower()
  distro2_lower = distro2.lower()

  equivalences = {
      "el": ["redhat", "rhel", "fedora", "centos", "scientific", "slc",
             "ascendos", "cloudlinux", "psbm", "oraclelinux", "ovs",
             "oel", "virtuozzo", "xenserver", "alibaba",
             "euleros", "openEuler", "almalinux", "rocky", "tencentos",
             "eurolinux", "kylin linux advanced server", "miracle", "el"],
      "amzn": ["amazon", "amzn",],
      "ubuntu": ["ubuntu", "raspbian", "neon", "kde neon",
                 "linux mint", "steamOS", "cumulus linux",
                 "pop!_os", "parrot", "pardus gnu/linux", "uos", "deepin", "osmc"],
      "debian": ["debian", "devuan", "kali",],
      "suse": ["suse", "sles", "sled", "opensuse", "opensuse tumbleweed",
               "sles_sap", "suse_linux", "opensuse leap", "alp-dolomite"],
  }

  # Check if both distributions belong to the same equivalence group
  for group, aliases in equivalences.items():
    if distro1_lower in aliases:
      if distro2_lower.startswith(group):
          if distro2_lower.startswith('el'):
            if major_version in distro2_lower:
              return True
            else:
              return False
          return True


  # Not equivalent if no match found
  return False

class TenableInfoMetadata:
    def __init__(self, 
                 os:str="",
                 md5:str="",
                 arch:str="",
                 sha256:str="",
                 os_type:str="",
                 product:str="",
                 version:str="",
                 product_type:str="",
                 release_date:str="",
                 product_notes:str="",
                 product_release_date:str="") -> None:
        self.os = os
        self.md5 = md5
        self.arch = arch
        self.sha256 = sha256
        self.os_type = os_type
        self.product = product
        self.version = version
        self.product_type = product_type
        self.release_date = release_date
        self.product_notes = product_notes
        self.product_release_date = product_release_date


class TenableDownloadInfo:
    def __init__(self,
                 id: int = None,
                 file: str = "",
                 name: str = "",
                 size: int = None,
                 description: str = "",
                 sort_order: str = "",
                 created_at: str = "",
                 updated_at: str = "",
                 page_id: int = None,
                 publish: bool = None,
                 required_auth: bool = None,
                 disabled: bool = None,
                 type: str = "",
                 meta_data: Optional[TenableInfoMetadata] = None) -> None:
        if meta_data is None:
            meta_data = {}
        self.id = id
        self.file = file
        self.name = name
        self.size = size
        self.description = description
        self.sort_order = sort_order
        self.created_at = created_at
        self.updated_at = updated_at
        self.page_id = page_id
        self.publish = publish
        self.required_auth = required_auth
        self.disabled = disabled
        self.type = type
        self.meta_data = meta_data
        self.download_uri = TENABLE_DOWNLOAD_API_URI.format(product_id = self.id)
        self.meta_data = TenableInfoMetadata(**self.meta_data)
        if self.name.endswith('dmg'):
            self.meta_data.os_type = "darwin"
            return
        elif self.name.endswith('tar.gz'):
            self.meta_data.os_type = "linux"
            return
        matches = re.search(r"(?P<version>\d+\.\d+\.\d+)-(?:(?P<os>[^-]+\d*))\.(?P<ext>[^.]+)$", self.name)
        if matches is None:
            return
        os_arch = re.split(r"(?<!\.)\.(?!\.)|(?<!_)_(?!_)", matches.group('os'), maxsplit=1)
        if self.meta_data.os is None:
            self.meta_data.os = os_arch[0]
        if self.meta_data.os_type is None:
            if self.meta_data.os.lower().startswith('win'):
                self.meta_data.os_type = "windows"
            else:
                self.meta_data.os_type = "linux"
        if self.meta_data.arch is None:
            if len(os_arch) > 1:
                self.meta_data.arch = os_arch[1]
    def is_match(self, os:str, major_version:str, arch:str, os_type:str)->bool:
        try:
            if os_type.lower() == 'darwin' and self.name.endswith('dmg'):
                return True
            return is_equivalent_distro(os, major_version, self.meta_data.os) and is_equivalent_architecture(arch, self.meta_data.arch)
        except:
            ...
        return False


class TenableProductInfo:
    def __init__(self,
                 product_name: str,
                 sort_order: str ,
                 downloads: List[TenableDownloadInfo],
                 release_notes: str = "",
                 version: str = "") -> None:
        self.product_name = product_name
        self.sort_order = sort_order
        self.downloads = downloads
        self.release_notes = release_notes
        self.version = version
        self.downloads = [TenableDownloadInfo(**d) for d in downloads]

    def get_download_for(self, os: str, major_version:str, arch:str, os_type:str)->TenableDownloadInfo:
        """Retrieves the first download w/ matching OS/Arch info. Note, the ordering is arbitrary and may cause unintended results.
        """
        for d in self.downloads:
            if d.is_match(os=os, major_version=major_version, arch=arch, os_type=os_type):
                return d
        raise ValueError(f"Unable to find a match for OS '{os}/{major_version}' w/ arch '{arch}' or '{os_type}'; options are {self.list_all_os_and_arch_options}")

    @property
    def list_all_os_and_arch_options(self):
        return [(d.meta_data.os, d.meta_data.arch) for d in self.downloads]

class TenablePageParser(html.parser.HTMLParser):
    def __init__(self, tag: str = "script", attrs: Optional[Tuple[str]] = None):
        super().__init__()
        if not attrs:
            attrs = ("id","__NEXT_DATA__")
        self.find_attrs = attrs
        self.find_tag = tag
        self.in_special_script = False
        self.json_data = ""
        self.decoded_json = None

    def handle_starttag(self, tag, attrs):
        if tag == self.find_tag and self.find_attrs in attrs:
            self.in_special_script = True

    def handle_data(self, data):
        if self.in_special_script:
            self.json_data += data

    def handle_endtag(self, tag):
        if tag == self.find_tag and self.in_special_script:
            self.in_special_script = False
            try:
                self.decoded_json = json.loads(self.json_data)
            except json.JSONDecodeError as e:
                return None  # Handle invalid JSON gracefully

    def get_product_info(self, text:str) -> Dict[str, TenableProductInfo]:
        if self.decoded_json is None:
            self.feed(text)
        products = self.decoded_json['props']['pageProps']['products']
        product_info = {}
        for product_name in products:
            product_info_dict = products[product_name]
            product_info[product_name] = TenableProductInfo(**product_info_dict)
        return product_info

class TenableProductDownloader:
    root_product_uri = "https://www.tenable.com/downloads"
    available_products = ["nessus-agents", "security-center"]
    
    def __init__(self) -> None:
        self.session = requests.Session()
        self.product_info: Dict[str, Dict[str, TenableProductInfo]] = {}
    
    def load_all_product_info(self) -> None:
        for product_name in self.available_products:
            parser = TenablePageParser()
            product_page_response = self.session.get(f"{self.root_product_uri}/{product_name}?loginAttempted=true")
            if product_page_response.status_code == 200:
                self.product_info[product_name] = parser.get_product_info(product_page_response.text)
            else:
                logger.error(f"Unable to retrieve product info for {product_name}: {product_page_response.status_code} HTTP response")

    @property
    def nessus_agent_info(self)-> Dict[str, TenableProductInfo]:
        if not self.product_info:
            self.load_all_product_info()
        return self.product_info['nessus-agents']

    @property
    def nessus_agent_installer_info(self)-> TenableProductInfo:
        for p in self.nessus_agent_info:
            if p.startswith('nessus-agents'):
                return self.nessus_agent_info[p]
    
    def get_nessus_agent_download_info(self, os:str, major_version:str, arch:str,os_type:str) -> TenableDownloadInfo:
        return self.nessus_agent_installer_info.get_download_for(os,major_version,arch,os_type)

    def download_to_path(self, info: TenableDownloadInfo, download_path: Path):
        download_path.mkdir(parents=True, exist_ok=True)
        response = self.session.get(info.download_uri)
        if response.status_code == 200:
            destination_path = download_path / info.name
            with destination_path.open('wb') as f:
                f.write(response.content)
            return destination_path
        else: 
            raise ValueError(f"Received unexpected server response (HTTP code {response.status_code}): {response.text}")

__metaclass__ = type

DOCUMENTATION = r'''
---
module: tenable_product

short_description: Module to facilitate grabbing tenable software products for installation

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This module downloads software from Tenable's downloads page automatically; currently defaults to just nessus using the host machine's platform/os info but the parser works to download any product from Tenable's website

options:
    state:
        description:
            - can be set to lookup_only; if lookup_only, will just grab the package info & download info from Tenable's page
        required: false
        type: string
    download_directory:
        description: An optional directory to use to download a Tenable product's package.
        required: false
        type: str
author:
    - Gustavo Argote (@)
'''

EXAMPLES = r'''
  - name: Lookup latest nessus agent product info for host system, store it in a variable
    tenable_product:
        state: lookup_only
    register: looked_up_info
  - name: Download latest nessus agent package for host machine to a specified directory
    tenable_product:
        download_directory: "/tmp/tenable_product_download"
    register: downloaded_product_info
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
changed:
    description: Whether changes were made on the target system. If lookup_only, will be false, if a package was downloaded, true.
    type: bool
    returned: always
    sample: False
product_info:
    description: Parsed product info from the Tenable Product page for the host machine
    type: dict
    returned: always
    sample: {
            "created_at": "2024-04-05T15:16:46.597Z",
            "description": "Ubuntu 14.04, 16.04, 18.04, 20.04, 22.04 (amd64)",
            "disabled": false,
            "download_uri": "https://www.tenable.com/downloads/api/v1/public/pages/nessus-agents/downloads/22712/download?i_agree_to_tenable_license_agreement=true",
            "file": "NessusAgent-10.6.1-ubuntu1404_amd64.deb",
            "id": 22712,
            "meta_data": {
                "arch": "amd64",
                "md5": "fe9b44c351bc026609158cca3e44f11c",
                "os": "ubuntu1404",
                "os_type": "linux",
                "product": "Nessus Agents - 10.6.1",
                "product_notes": null,
                "product_release_date": "2024-04-05T00:00:00.000Z",
                "product_type": "default",
                "release_date": "2024-04-04T00:00:00.000Z",
                "sha256": "0ea2f72a7d3a9e7dfcd59712388136fd15f61c310effb22d5b8d8de44314b141",
                "version": "10.6.1"
            },
            "name": "NessusAgent-10.6.1-ubuntu1404_amd64.deb",
            "page_id": 61,
            "publish": true,
            "required_auth": false,
            "size": 25513220,
            "sort_order": null,
            "type": "download",
            "updated_at": "2024-04-05T15:17:25.145Z"
        },
package_uri:
    description: The remote or local, if downloaded, URI to the latest Nessus Agent package
    type: str
    returned: always
    sample: https://www.tenable.com/downloads/api/v1/public/pages/nessus-agents/downloads/22712/download?i_agree_to_tenable_license_agreement=true
system_info:
    description: 
    type: dict
    returned: always
    sample: {"architecture": "x86_64",
            "distribution": "Ubuntu",
            "distribution_file_parsed": true,
            "distribution_file_path": "/etc/os-release",
            "distribution_file_variety": "Debian",
            "distribution_major_version": "18",
            "distribution_release": "bionic",
            "distribution_version": "18.04",
            "domain": "",
            "fqdn": "example",
            "hostname": "example",
            "kernel": "4.15.0-213-generic",
            "kernel_version": "#224-Ubuntu SMP Mon Jun 19 13:30:12 UTC 2023",
            "machine": "x86_64",
            "machine_id": "",
            "nodename": "example",
            "os_family": "Debian",
            "pkg_mgr": "apt",
            "python_version": "3.6.9",
            "system": "Linux",
            "userspace_architecture": "x86_64",
            "userspace_bits": "64"}
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.facts.system.platform import PlatformFactCollector
from ansible.module_utils.facts.system.distribution import DistributionFactCollector
from ansible.module_utils.facts.system.pkg_mgr import PkgMgrFactCollector

def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        download_directory=dict(type='str', required=False),
        state=dict(type='str', required=False), # download, lookup_only
        cleanup=dict(type='bool', required=False),
    )
    
    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        product_info='',
        package_uri='',
        system_info=''
    )
    
    # # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        add_file_common_args=True
    )
    
    distro_facts = DistributionFactCollector().collect(module=module)
    platform_facts = PlatformFactCollector().collect(module=module)
    pkg_mgr_facts = PkgMgrFactCollector().collect(module=module, collected_facts={"ansible_" + str(key): val for key, val in distro_facts.items()})
    result['system_info'] = {**distro_facts, **platform_facts, **pkg_mgr_facts}
    downloader = TenableProductDownloader()
    info = downloader.get_nessus_agent_download_info(
        os=distro_facts['distribution'], 
        major_version=distro_facts["distribution_major_version"], 
        arch=platform_facts['architecture'], os_type=distro_facts['os_family']
        )
    result['product_info'] = to_dict(info)
    result['package_uri'] = info.download_uri
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode or module.params['state'] == 'lookup_only':
        module.exit_json(**result)
    
    if module.params['download_directory']:
        dpath = Path(module.params['download_directory'])
        destination_path = downloader.download_to_path(info, download_path=dpath)
        result['package_uri'] = str(destination_path)
        result['changed'] = True
    # during the execution of the module, if there is an exception or a
    # conditional state that effectively causes a failure, run
    # AnsibleModule.fail_json() to pass in the message and the result
    # if module.params['name'] == 'fail me':
    #     module.fail_json(msg='You requested this to fail', **result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


if __name__ == '__main__':
    run_module()