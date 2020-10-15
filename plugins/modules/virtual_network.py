#!/usr/bin/python

# Copyright: (c) 2020, Tatsuya Naganawa <tatsuyan201101@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: virtual_network

short_description: create tungstenfabirc virtual-network

version_added: "2.10"

description:
    - "create / delete tungstenfabric virtual-network"

options:
    name:
        description:
            - virtual-network name
        required: true
    controller_ip:
        description:
            - tungstenfabric controller ip
        required: true
    subnet:
        description:
            - virtual-network subnet
        required: false
    subnet_prefix:
        description:
            - virtual-network subnet prefix
        required: false
    domain:
        description:
            - virtual-network subnet
        required: false
    project:
        description:
            - virtual-network subnet
        required: false

author:
    - Tatsuya Naganawa (@tnaganawa)
'''

EXAMPLES = '''
# Pass in a message
- name: create virtual-network
  tungstenfabric_virtual_network:
    name: vn1
    controller_ip: x.x.x.x
    state: present

- name: delete virtual-network
  tungstenfabric_virtual_network:
    name: vn1
    controller_ip: x.x.x.x
    state: absent

'''

RETURN = '''
message:
    description: The output message that this module generates
    type: str
    returned: always
'''

import json
import requests
from ansible.module_utils.basic import AnsibleModule

def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        controller_ip=dict(type='str', required=True),
        username=dict(type='str', required=False, default='admin'),
        password=dict(type='str', required=False, default='contrail123'),
        state=dict(type='str', required=False, default='present', choices=['absent', 'present']),
        domain=dict(type='str', required=False, default='default-domain'),
        project=dict(type='str', required=False, default='default-project'),
        subnet=dict(type='str', required=False),
        subnet_prefix=dict(type='int', required=False)
    )
    result = dict(
        changed=False,
        message=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    name = module.params.get("name")
    controller_ip = module.params.get("controller_ip")
    username = module.params.get("username")
    password = module.params.get("password")
    state = module.params.get("state")
    domain = module.params.get("domain")
    project = module.params.get("project")
    subnet = module.params.get("subnet")
    subnet_prefix = module.params.get("subnet_prefix")


    if module.check_mode:
        module.exit_json(**result)

    ## begin: virtual-network
    config_api_url = 'http://' + controller_ip + ':8082/'
    web_api_url = 'https://' + controller_ip + ':8143/'
    vnc_api_headers= {"Content-Type": "application/json", "charset": "UTF-8"}
    failed = False

    ## check if the fqname exists
    response = requests.post(config_api_url + 'fqname-to-id', data='{"type": "virtual_network", "fq_name": ["%s", "%s", "%s"]}' % (domain, project, name), headers=vnc_api_headers)
    if response.status_code == 200:
      update = True
      uuid = json.loads(response.text).get("uuid")
    else:
      update = False

    ## login to web API
    client = requests.session()
    response = client.post(web_api_url + 'authenticate', data=json.dumps({"username": username, "password": password}), headers=vnc_api_headers, verify=False)
    print (client.cookies)
    csrftoken=client.cookies['_csrf']
    vnc_api_headers["x-csrf-token"]=csrftoken

    ## create payload and call API
    js=json.loads (
    '''
    { "virtual-network":
      {
        "fq_name": ["%s", "%s", "%s"],
        "parent_type": "project"
      }
    }
    ''' % (domain, project, name)
    )

    if subnet:
      js ["virtual-network"]["network_ipam_refs"]=[
        {"to": ["default-domain", "default-project", "default-network-ipam"],
        "attr": {"ipam_subnets": [{"subnet": {"ip_prefix": subnet, "ip_prefix_len": subnet_prefix}}]}
        }
      ]


    if state == "present":
      if update:
        print ("update object")
        js["virtual-network"]["uuid"]=uuid
        response = client.post(web_api_url + 'api/tenants/config/update-config-object', data=json.dumps(js), headers=vnc_api_headers, verify=False)
      else:
        print ("create object")
        response = client.post(web_api_url + 'api/tenants/config/create-config-object', data=json.dumps(js), headers=vnc_api_headers, verify=False)
    elif (state == "absent"):
      if update:
        print ("delete object {}".format(uuid))
        response = client.post(web_api_url + 'api/tenants/config/delete', data=json.dumps([{"type": "virtual-network", "deleteIDs": ["{}".format(uuid)]}]), headers=vnc_api_headers, verify=False)
      else:
        failed = True
    message = response.text

    if response.status_code == 200:
      result['changed'] = True
    else:
      result['changed'] = False
      failed = True

    result['message'] = message

    ## end: virtual-network

    if failed:
        module.fail_json(msg='failure message', **result)

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()