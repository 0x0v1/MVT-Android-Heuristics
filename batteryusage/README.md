# Battery Drain Analysis for Spyware Detection

## Overview

This script is designed to analyze the structured output of the `adb shell dumpsys batterystats --checkin` command. By parsing this system-level battery usage report, the script systematically aggregates per-app battery consumption, tallies wakeups and wakelocks, and flags apps exhibiting suspicious battery drain characteristics. The goal is to identify anomalous background activity that could indicate spyware or stealthy malware.

To assist in prioritizing further investigation, the script calculates a heuristic score based on multiple factors, including excessive background power usage, wakeups, and wakelocks. The results are then presented in a color-coded, sorted table, highlighting apps with high battery consumption and those requiring verification as **POSSIBLY SYSTEM PROCESS (needs verification)**.

---

## How Battery Drain Characteristics Are Calculated

Battery consumption on Android devices is tracked and attributed to individual applications and system services. The `batterystats` report contains detailed logs on power usage, system wakeups, and background activities, which are critical indicators of app behavior. The script processes these indicators using the following approach:

### **1. Extracting Per-App Battery Usage from PWI Lines**
Battery usage data is primarily extracted from `pwi` (Power Usage Item) lines in the checkin report.

Example `pwi` entry:
9,1000,l,pwi,com.example.spyware,450,2,0,0
- **Column 5**: App identifier (`com.example.spyware`)
- **Column 6**: **Total battery usage** (e.g., `450` units)
- **Column 7**: **Foreground (FG) usage** (e.g., `2` units)
- **Column 8+**: Other system metrics

The script computes:
- **Foreground-to-Total Ratio (FG/Total)**:  
  This ratio is a critical metric. **A low ratio (e.g., below 0.1)** indicates that the app is consuming most of its power in the background, which is a characteristic behavior of spyware.
- **Threshold-Based Flagging**:  
  - If total battery usage exceeds a predefined threshold (e.g., `50` units for system apps, `20` for third-party apps) **and** the foreground ratio is low, the app is marked as **suspicious**.

### **2. System Wakeups and Wakelocks as Indicators of Background Activity**
Spyware often forces a device to stay awake to perform background operations, such as:
- **Transmitting data**
- **Recording audio/video**
- **Polling GPS or sensors**
- **Keeping network connections alive**

The script extracts wakeup and wakelock counts from:
- **WR (`wr`) Lines – System Wakeups**
9,0,i,wr,1275
- `1275` system-wide wakeups were recorded.
- Frequent wakeups can indicate excessive background processing by an app.

- **KWL (`kwl`) Lines – Wakelocks**
9,0,i,kwl,920
- `920` wakelocks were recorded.
- Apps abusing wakelocks prevent a device from sleeping, often linked to spyware behavior.

These values are added to the **heuristic score** to quantify the impact of background wake activity.

### **3. UID-Based Aggregation of Battery Usage**
Some apps share UIDs with system services, making it difficult to attribute battery drain accurately.  
Example:
9,1000,i,uid,1000,com.android.systemui

- The script **maps UIDs to package names**, ensuring that UID-based power consumption is properly assigned.
- If an app shares a UID with **third-party packages**, battery usage is **distributed proportionally** to those apps.

--
## **Why This Matters**
This approach provides a **behavior-based detection method** for spyware.  
Rather than relying on signature-based scanning (like antivirus software), it **identifies anomalies** in resource consumption. This is particularly useful for:
- **Detecting newly developed or undiscovered spyware.**
- **Analyzing enterprise security risks from background apps.**
- **Identifying data-harvesting apps disguised as legitimate software.**

____________________________________________________________

## What the Script Does

1. **File Reading and Parsing**  
   - **Encoding Support:**  
     The script attempts to read the input file using multiple encodings (e.g., `utf-8-sig` and `utf-16`) to correctly parse the checkin output.
   - **Line Types:**  
     - **UID Lines:**  
       These lines (e.g., `9,0,i,uid,1000,com.example.package`) map a UID to a package name. The mapping is stored for later distribution of battery usage.
     - **PWI Lines:**  
       These lines (e.g., `9,1000,l,pwi,uid,382,1,0,0`) provide per‑app battery usage details. The script extracts total usage and foreground (FG) usage for each app.
     - **WR/KWL Lines:**  
       These lines indicate counts for wakeups (`wr`) and wakelocks (`kwl`) and are used to factor into the overall heuristic score.

2. **Aggregating Battery Usage**  
   - The script sums up battery usage per app based on the `pwi` lines.
   - For entries that use a UID key (formatted as `uid_<uid>`), the script distributes the usage evenly among any associated third‑party apps (those with package names starting with `"com."`).

3. **Output Formatting and Coloring**  
   - The final output displays a sorted table of per‑app battery usage in descending order (only including apps with nonzero usage).  
   - Each entry in the table shows:
     - **Usage** (formatted to two decimals)
     - **App/Package Name**
     - **Flags** (if the app is likely a system process, it is flagged as **POSSIBLY SYSTEM PROCESS (needs verification)**)
   - ANSI colors are used to highlight key information for better readability.

4. **Suspicious App Detection and Heuristic Scoring**  
   - **Thresholds:**  
     - **Third‑Party Apps:** A lower battery usage threshold (e.g., 20.0 units) is applied.
     - **Other Apps:** A higher threshold (e.g., 50.0 units) is used.
   - **Foreground Ratio:**  
     The ratio of foreground usage to total usage is calculated. A low ratio (e.g., less than 0.1) suggests an app is consuming battery mainly in the background.
   - **Suspicion Score Calculation:**  
     For each app that exceeds its usage threshold and has a low foreground ratio, a suspicion score is computed based on:
     - **Excess Usage:** The amount by which the app’s usage exceeds the threshold.
     - **Foreground Deficit:** How low the foreground usage is relative to total usage.
   - **Overall Heuristic Score:**  
     The script computes an overall heuristic score as follows:
     ```
     heuristic_score = (number_of_suspicious_apps * 10) + ((wakeups + wakelocks) / 100)
     ```
     This score combines the number of suspicious apps with the impact of system wakeups and wakelocks.

5. **Ordered and Detailed Suspicious Apps List**  
   - Suspicious apps are listed in order from most to least likely to be malicious. Next to each app, the output explains why it was flagged (e.g., "high battery usage with low foreground activity" or "excessive background consumption relative to typical system processes").  
   - If an app is also flagged as a possible system process, it is indicated with the label **POSSIBLY SYSTEM PROCESS (needs verification)**.  
   - The list is color-coded to differentiate system-like apps (displayed in yellow) from non-system apps (displayed in red).

6. **Exclusion of UID Mapping Section**  
   - The final output omits the UID‑to‑package mapping section to maintain focus on battery usage and suspicious app analysis.

## Understanding the `adb shell dumpsys batterystats --checkin` Output

The checkin output from the `adb shell dumpsys batterystats --checkin` command is a CSV-like report that includes several types of lines:

- **UID Lines:**  
  - **Format:**  
    ```
    9,0,i,uid,1000,com.samsung.android.app.dressroom
    ```
  - **Purpose:**  
    These lines map a UID (User ID) to a package name, enabling the script to link battery usage entries (from UID-based lines) with the correct app.

- **PWI Lines:**  
  - **Format:**  
    ```
    9,1000,l,pwi,uid,382,1,0,0
    ```
  - **Purpose:**  
    These lines report the per‑app battery usage, where:
    - Column 5 indicates the app identifier (or `"uid"` for UID-based entries).
    - Column 6 provides the battery usage value.
    - Column 7 shows foreground (FG) usage, which is key for determining whether an app’s battery consumption is in the foreground or background.

- **WR/KWL Lines:**  
  - **Purpose:**  
    They record the counts for wakeups (`wr`) and wakelocks (`kwl`). These values contribute to the overall heuristic score, reflecting how frequently the device is being awakened by various processes.

## How to Use the Script

1. **Generate the Checkin File:**  
   On your Android device, run:
   ```bash
   adb shell dumpsys batterystats --checkin > batterystats.txt
