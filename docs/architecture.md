# HPE Server Automation – Architecture

This repository models a typical enterprise automation layout for HPE servers.

- **Automation Layer**: Ansible controller + Python tools + CI/CD
- **Management Network**: Out-of-band iLO network (Redfish over HTTPS)
- **Datacenter Layer**: HPE ProLiant servers with iLO 5 controllers
- **Source of Truth**: NetBox CMDB

See `docs/bios_profile_example.yml` and `docs/firmware_matrix_example.yml` for
example baselines.
