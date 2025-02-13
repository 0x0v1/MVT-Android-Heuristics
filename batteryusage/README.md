# Battery Stats Parser Script Summary

## Overview

This script analyzes the output from the `adb shell dumpsys batterystats --checkin` command. It aggregates per-app battery usage, counts wakeups and wakelocks, and flags apps that exhibit suspicious battery drain characteristics. The tool then calculates a heuristic score to help prioritize further investigation. The output is formatted into a color-coded, sorted table that highlights both the per-app battery usage and the suspicious apps—especially noting those apps that are **POSSIBLY SYSTEM PROCESS (needs verification)**.

## What the Script Does

1. **File Reading and Parsing**  
   - **Encoding Support:**  
     The script attempts to read the input file using multiple encodings (e.g., `utf-8-sig` and `utf-16`) to correctly parse the checkin output.
   - **Line Types:**  
     - **UID Lines:**  
       These lines (e.g., `9,0,i,uid,1000,com.example.package`) map a UID to a package name. The mapping is stored for later distribution of battery usage.
     - **PWI Lines:**  
       These lines (e.g., `9,1000,l,pwi,uid,382,1,0,0`) provide per-app battery usage details. The script extracts total usage and foreground (FG) usage for each app.
     - **WR/KWL Lines:**  
       These lines indicate counts for wakeups (`wr`) and wakelocks (`kwl`) and are used to factor into the overall heuristic score.

2. **Aggregating Battery Usage**  
   - The script sums up battery usage per app based on the `pwi` lines.
   - For entries that use a UID key (formatted as `uid_<uid>`), the script distributes the usage evenly among any associated third‑party apps (those with package names starting with `"com."`).

3. **Output Formatting and Coloring**  
   - The final output displays a sorted table of per-app battery usage in descending order (only including apps with nonzero usage).
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
   - Suspicious apps are listed in order from most to least suspicious. Next to each app, the output explains why it was flagged (e.g., high battery usage with low foreground activity).
   - If an app is also flagged as a possible system process, it is indicated with the label **POSSIBLY SYSTEM PROCESS (needs verification)**.
   - The suspicious apps list is also color-coded to differentiate system-like apps (displayed in yellow) from non-system apps (displayed in red).

6. **Exclusion of UID Mapping Section**  
   - The final output omits the UID-to-package mapping section to keep the focus on battery usage and suspicious app analysis.

## Understanding the `adb shell dumpsys batterystats --checkin` Output

The checkin output from the `adb shell dumpsys batterystats --checkin` command is a CSV-like report that includes several types of lines:

- **UID Lines:**  
  - **Format:**  
    ```
    9,0,i,uid,1000,com.samsung.android.app.dressroom
    ```
  - **Purpose:**  
    They map a UID (User ID) to a package name, enabling the script to link battery usage entries (from UID-based lines) with the correct app.

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
