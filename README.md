# MVT-Android-Heuristics
Repo with PoCs for android heuristic detections  

# Android Forensics & Spyware Detection - Heuristic Development Checklist

This checklist tracks the development of heuristics to analyze structured ADB logs and dumpsys outputs as used.

---

## Battery Usage

- [x] Battery Drain Heuristic (`batterystats`)
  - Use Case: Detect apps with excessive battery usage and minimal foreground activity.
  - Logic:
    - Flag apps with high total usage but low FG/usage ratio.
    - Factor in system wakeups and wakelocks.
    - Compute heuristic score.

---

## Package & App Metadata

- [ ] Installed Package Heuristic (`dumpsys_packages.py`, `packages.py`)
  - Use Case: Identify cloaked, duplicate, or recently-installed spyware apps.
  - Logic:
    - Flag duplicate package names.
    - Detect apps installed recently.
    - Cross-check apps not from official stores.

- [ ] Uninstalled/Residual Apps (`__init__.py`)
  - Use Case: Track apps that were uninstalled but left traces.
  - Logic:
    - Parse uninstalled apps from dumpsys.
    - Flag those with known suspicious behavior or mismatched metadata.

---

## Permissions & Access

- [ ] AppOps Abuse Heuristic (`dumpsys_appops.py`)
  - Use Case: Find apps accessing location, camera, mic, etc. without being in foreground.
  - Logic:
    - Compare granted permissions with actual usage.
    - Flag sensitive permission usage out of expected context.

- [ ] Accessibility Abuse Detection (`dumpsys_accessibility.py`)
  - Use Case: Detect misuse of Accessibility Service APIs.
  - Logic:
    - Flag third-party apps with Accessibility enabled.
    - Prioritize those not needing accessibility for core function.

---

## Process & Activity Monitoring

- [ ] Active Activity Heuristic (`dumpsys_activities.py`)
  - Use Case: Identify apps that remain active in background or hijack task stack.
  - Logic:
    - Flag apps with abnormal activity durations.
    - Detect unexpected tasks in foreground.

- [ ] Suspicious Background Processes (`processes.py`)
  - Use Case: Detect persistent background services or hidden processes.
  - Logic:
    - Compare background processes against whitelist.
    - Flag services with no visible UI or user interaction.

---

## Communication & Wake Events

- [ ] Wakeup/Wakelock Abuse (`dumpsys_battery_history.py`, `dumpsys_battery_daily.py`)
  - Use Case: Identify apps keeping the device awake unnecessarily.
  - Logic:
    - Flag apps with high wakelock/wakeup count.
    - Combine with low foreground usage.

- [ ] SMS Abuse Heuristic (`sms.py`)
  - Use Case: Detect apps sending or receiving hidden SMS commands.
  - Logic:
    - Check for SMS activity tied to unknown or silent apps.
    - Cross-reference timestamps with wake events or usage spikes.

---

## System Settings & Configurations

- [ ] Suspicious Settings Modifications (`settings.py`)
  - Use Case: Identify risky configuration changes.
  - Logic:
    - Detect install-from-unknown-sources enabled.
    - USB debugging or dev settings turned on unexpectedly.

- [ ] getprop Anomalies (`getprop.py`)
  - Use Case: Detect rooted devices, test builds, or non-standard firmware.
  - Logic:
    - Flag test-keys, root presence, or unofficial builds.

---

## App Behavior & Events

- [ ] Broadcast Receiver Overuse (`dumpsys_receivers.py`)
  - Use Case: Find apps listening for sensitive or excessive system broadcasts.
  - Logic:
    - Flag apps registering for BOOT_COMPLETED, SMS_RECEIVED, etc.

- [ ] Platform Compatibility Overrides (`dumpsys_platform_compat.py`)
  - Use Case: Catch apps bypassing modern Android restrictions.
  - Logic:
    - Flag apps requesting compatibility overrides.

- [ ] DB Abuse Heuristic (`dumpsys_dbinfo.py`)
  - Use Case: Spot abnormal database usage patterns.
  - Logic:
    - Large DBs or excessive writes by non-database-centric apps.

---

## File Forensics

- [ ] Suspicious File Timestamp Activity (`files.py`, `logfile_timestamps.py`)
  - Use Case: Detect suspicious file modification timelines.
  - Logic:
    - Look for app-related files created/modified outside normal install flow.
    - Correlate file activity with install times or app usage.

