import subprocess
import sys

# List of Python scripts to execute

print("\nRead the instructions.pdf file for information on how to run the bot\n")

print("Running bot.py...\n", flush=True)  # Ensure immediate output

with subprocess.Popen(["python", "-u", "bot.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1) as process:
# Print stdout line-by-line immediately
    for line in process.stdout:
        print(line, end="", flush=True)

            # Print stderr line-by-line immediately
    for line in process.stderr:
        print(f"ERROR: {line}", end="", flush=True)
        

if process.returncode != 0:
    print(f"\nbot.py failed with exit code {process.returncode}", flush=True)
    sys.exit(1)

print("----------------------------------------------------------------------------------------------------\n", flush=True)

print("Running generate_results.py...\n", flush=True)  # Ensure immediate output

with subprocess.Popen(["python", "-u", "generate_results.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1) as process:
# Print stdout line-by-line immediately
    for line in process.stdout:
        print(line, end="", flush=True)

            # Print stderr line-by-line immediately
    for line in process.stderr:
        print(f"ERROR: {line}", end="", flush=True)
        

if process.returncode != 0:
    print(f"\ngenerate_results.py failed with exit code {process.returncode}", flush=True)
    sys.exit(1)

print("----------------------------------------------------------------------------------------------------\n", flush=True)

print("\n✅ All scripts executed successfully!", flush=True)
