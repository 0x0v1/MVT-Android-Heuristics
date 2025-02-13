import csv
import sys
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Global whitelist for known system components (non‑third‑party names).
SYSTEM_WHITELIST = {
    "scrn", "cpu", "blue", "camera", "video", "cell",
    "wifi", "memory", "phone", "ambi", "idle",
    "audio", "flashlight", "sensors", "???"
}

def is_system_app(package):
    """
    Returns True if the package name appears to be a system process.
    Checks if the package is in SYSTEM_WHITELIST or if it starts with common system prefixes.
    """
    if package in SYSTEM_WHITELIST:
        return True
    # Common system package prefixes (adjust as needed)
    system_prefixes = ("com.android.", "android.", "com.samsung.", "com.sec.")
    return package.startswith(system_prefixes)

def print_battery_usage_chart(battery_usage):
    """
    Prints a sorted table of battery usage for apps/packages.
    Only shows entries with usage > 0.0, sorted in descending order.
    Next to packages that appear to be system processes, prints a flag:
      "POSSIBLY SYSTEM PROCESS (needs verification)"
    Colors are added for readability.
    """
    # Filter out entries with zero usage
    filtered = {pkg: usage for pkg, usage in battery_usage.items() if usage > 0.0}
    # Sort by usage descending
    sorted_entries = sorted(filtered.items(), key=lambda item: item[1], reverse=True)
    
    header = "{:<10}  {:<50}  {}".format("Usage", "App/Package", "Flags")
    separator = "-" * len(header)
    print(Fore.CYAN + "\nPer-App Battery Usage (sorted by usage):")
    print(separator)
    print(header)
    print(separator)
    
    for pkg, usage in sorted_entries:
        flag = ""
        if is_system_app(pkg):
            flag = "POSSIBLY SYSTEM PROCESS (needs verification)"
            flag = Fore.YELLOW + flag + Style.RESET_ALL
        print("{:<10.2f}  {:<50}  {}".format(usage, pkg, flag))
    print()

def parse_batterystats(filename):
    """
    Reads the file using several encodings.
    Expected CSV format (without a header) where the 4th column (index 3)
    indicates the checkin type:
      - uid lines: e.g. 9,0,i,uid,1000,com.example.package
      - pwi lines: e.g. 9,1000,l,pwi,uid,382,1,0,0 or other app names in col5.
      - wr/kwl lines: e.g. 9,0,i,wr,<count> or 9,0,i,kwl,<count>
    """
    data = []
    encodings = ['utf-8-sig', 'utf-16']
    for encoding in encodings:
        try:
            with open(filename, 'r', newline='', encoding=encoding) as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if not row or len(row) < 4:
                        continue
                    line_type = row[3].strip().lower()
                    entry = {"line_type": line_type, "raw": row}
                    
                    if line_type == "uid":
                        # Expected format: [9,0,i,uid,1000,com.example.package,...]
                        if len(row) >= 6:
                            entry["uid"] = row[4].strip()  # the UID value (e.g., "1000")
                            entry["pkg"] = row[5].strip()  # the package name
                    elif line_type == "pwi":
                        # Expected format (e.g.): 9,1000,l,pwi,uid,382,1,0,0
                        if len(row) >= 7:
                            app_field = row[4].strip()
                            if app_field == "uid":
                                uid_val = row[1].strip()
                                entry["app"] = "uid_" + uid_val
                            else:
                                entry["app"] = app_field
                            entry["usage"] = row[5].strip()
                            entry["fg"] = row[6].strip()
                    elif line_type in ("wr", "kwl"):
                        if len(row) >= 5:
                            entry["count"] = row[4].strip()
                    data.append(entry)
            print(f"File read successfully with encoding: {encoding}")
            return data
        except UnicodeDecodeError as e:
            print(f"Failed to read with encoding {encoding}: {e}", file=sys.stderr)
    raise ValueError(f"Could not decode file {filename} with encodings: {encodings}")

def detect_patterns(data, debug=False, 
                    system_threshold_usage=50.0, 
                    tp_threshold_usage=20.0, 
                    threshold_ratio=0.1):
    """
    Processes the parsed data to:
      - Gather per‑app battery usage from "pwi" lines.
      - Count wakeups ("wr") and wakelocks ("kwl").
      - Build a UID‑to‑package mapping from "uid" lines.
      - For pwi entries with keys starting with "uid_", distribute the aggregated
        usage among all third‑party packages (names starting with "com.") that share that UID.
      - Identify suspicious apps based on battery usage and foreground activity.

    For each app, a suspicion score is computed as:
        (usage - current_threshold) * (threshold_ratio - (fg/usage))
    (only for apps that exceed the usage threshold and have a low foreground ratio).
    Returns the battery usage dictionary, wakeup/wakelock counts, and a sorted list
    of suspicious app details.
    """
    battery_usage = {}         # Aggregated usage keyed by app (or "uid_<uid>")
    app_fg_usage = {}          # Corresponding foreground usage
    wakeups_count = 0
    wakelocks_count = 0
    uid_to_pkg = {}

    # Process each parsed line.
    for row in data:
        line_type = row.get("line_type", "")
        if line_type == "pwi":
            app = row.get("app", "unknown")
            try:
                usage = float(row.get("usage", 0))
            except ValueError:
                usage = 0.0
            battery_usage[app] = battery_usage.get(app, 0) + usage
            try:
                fg = float(row.get("fg", 0))
            except ValueError:
                fg = 0.0
            app_fg_usage[app] = app_fg_usage.get(app, 0) + fg

        elif line_type == "wr":
            try:
                count = int(row.get("count", 1))
            except ValueError:
                count = 1
            wakeups_count += count

        elif line_type == "kwl":
            try:
                count = int(row.get("count", 1))
            except ValueError:
                count = 1
            wakelocks_count += count

        elif line_type == "uid":
            uid_val = row.get("uid", "")
            pkg = row.get("pkg", "unknown")
            uid_to_pkg[uid_val] = pkg

    # --- Distribute aggregated UID battery usage ---
    uid_keys = [key for key in battery_usage if key.startswith("uid_")]
    for uid_key in uid_keys:
        total_usage = battery_usage.pop(uid_key)
        uid_val = uid_key[len("uid_"):]
        # Find third‑party packages for this UID (names starting with "com.")
        packages = [pkg for (uid_map, pkg) in uid_to_pkg.items() if uid_map == uid_val and pkg.startswith("com.")]
        if packages:
            distributed = total_usage / len(packages)
            for pkg in packages:
                battery_usage[pkg] = battery_usage.get(pkg, 0) + distributed
                if pkg not in app_fg_usage:
                    app_fg_usage[pkg] = 0.0

    # --- Identify suspicious apps and compute suspicion scores ---
    suspicious_details = []
    for app, usage in battery_usage.items():
        fg = app_fg_usage.get(app, 0)
        ratio = (fg / usage) if usage > 0 else 0
        # Determine threshold based on app type.
        if app.startswith("com."):
            current_threshold = tp_threshold_usage
        else:
            if app in SYSTEM_WHITELIST:
                continue  # Skip known system components
            current_threshold = system_threshold_usage
        if usage > current_threshold and ratio < threshold_ratio:
            # Compute a simple suspicion score.
            suspicion_score = (usage - current_threshold) * (threshold_ratio - ratio)
            is_system = is_system_app(app)
            reason = (f"Battery usage {usage:.2f} exceeds threshold {current_threshold:.2f} by {usage - current_threshold:.2f}; "
                      f"foreground ratio {ratio:.2f} is below threshold {threshold_ratio:.2f}")
            if is_system:
                reason += " (possibly a system process)"
            suspicious_details.append({
                "app": app,
                "usage": usage,
                "fg": fg,
                "ratio": ratio,
                "threshold": current_threshold,
                "suspicion_score": suspicion_score,
                "reason": reason,
                "is_system": is_system
            })
    # Sort suspicious apps from most to least suspicious (by suspicion_score).
    suspicious_details = sorted(suspicious_details, key=lambda x: x["suspicion_score"], reverse=True)

    heuristic_score = len(suspicious_details) * 10 + (wakeups_count + wakelocks_count) / 100.0

    analysis = {
        'battery_usage': battery_usage,
        'wakeups': wakeups_count,
        'wakelocks': wakelocks_count,
        'suspicious_details': suspicious_details,
        'heuristic_score': heuristic_score
    }
    return analysis

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_batterystats.py <filename>")
        sys.exit(1)
    filename = sys.argv[1]
    try:
        data = parse_batterystats(filename)
        print("\n" + Fore.CYAN + "Detecting patterns..." + Style.RESET_ALL)
        analysis = detect_patterns(data, debug=False,
                                   system_threshold_usage=50.0,
                                   tp_threshold_usage=20.0,
                                   threshold_ratio=0.1)

        print("\n" + Fore.GREEN + "Analysis Results:" + Style.RESET_ALL)

        # Print the battery usage chart.
        print_battery_usage_chart(analysis['battery_usage'])

        print(Fore.MAGENTA + f"Total wakeups: {analysis['wakeups']}" + Style.RESET_ALL)
        print(Fore.MAGENTA + f"Total wakelocks: {analysis['wakelocks']}" + Style.RESET_ALL)

        if analysis['suspicious_details']:
            print("\n" + Fore.RED + "Suspicious apps detected:" + Style.RESET_ALL)
            for detail in analysis['suspicious_details']:
                app = detail["app"]
                reason = detail["reason"]
                # Color-code: system apps in yellow, others in red.
                if detail["is_system"]:
                    app_str = Fore.YELLOW + app + Style.RESET_ALL
                else:
                    app_str = Fore.RED + app + Style.RESET_ALL
                print(f"  {app_str}: {reason}")
        else:
            print("\nNo suspicious apps detected.")

        print("\n" + Fore.BLUE + f"Heuristic score: {analysis['heuristic_score']:.2f}" + Style.RESET_ALL)
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
