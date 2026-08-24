---
name: System Diagnostics & Maintenance
description: Checking system health, disk space, active processes, IP configuration, and network diagnostics.
triggers: system, disk, memory, ip, network, ping, process, diagnostic, clean, status
---

# System Diagnostics & Maintenance Skill

When the user asks you to check PC health, network status, or system performance:

## Recommended Fast Workflow:
1. **Network Diagnostics**:
   - Run `run_command` with `Get-NetIPAddress` or `ipconfig` to inspect IP.
   - Run `Test-Connection -Count 2 google.com` or `ping -n 2 8.8.8.8` to test connectivity.
2. **Resource & Disk Inspection**:
   - Run `Get-PSDrive C | Select-Object Used,Free` or `wmic logicaldisk get size,freespace,caption`.
   - Run `Get-Process | Sort-Object CPU -Descending | Select-Object -First 5` to identify high-CPU processes.
3. **Summary**: Provide an easy-to-read summary of system stats to the user.
