# Utility Scripts

This folder contains utility scripts for maintenance and advanced use cases.

## Contents

### `RESTART_UNIFIED_CONSOLE.sh`
Quick restart script for the unified console only (no full system restart).

**Usage:**
```bash
./scripts/RESTART_UNIFIED_CONSOLE.sh
```

**When to use:**
- After editing `templates/control_panel.html`
- After changing backend configuration
- When unified console becomes unresponsive

**Not needed for:**
- Regular startup (use `START_ALL.command` instead)
- Full system restart (use `STOP_ALL.command` + `START_ALL.command`)

---

### `START_BRIDGE.command`
Manually starts the TEP Bridge (connects FORTRAN simulation to backend).

**Usage:**
```bash
./scripts/START_BRIDGE.command
```

**When to use:**
- **Rarely needed!** Unified console already handles data streaming
- Only for debugging or manual testing of bridge functionality
- If you want to send data directly without unified console

**Normal operation:**
The bridge is **not required** for regular operation. The unified console handles all data flow.

---

## For Regular Users

**You don't need these scripts!** Use the main commands instead:

| Task | Use This |
|------|----------|
| Start system | `START_ALL.command` |
| Stop system | `STOP_ALL.command` |
| First-time setup | `SETUP_FIRST_TIME.command` |
| New laptop setup | `SETUP_NEW_LAPTOP.sh` |

---

## Advanced Users Only

These scripts are for:
- Developers debugging the system
- Advanced users who understand the architecture
- Testing specific components in isolation
