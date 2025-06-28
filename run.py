import os
import platform
import subprocess

def main():
    config_file = "my-config.json"

    if not os.path.exists(config_file):
        print(f"❌ Config file '{config_file}' not found.")
        return

    # Choose python executable
    python_cmd = "python" if platform.system() == "Windows" else "python3"

    try:
        subprocess.run([python_cmd, "api_task_runer.py", "-c", config_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Task execution failed: {e}")
    else:
        print("✅ Task completed successfully.")

if __name__ == "__main__":
    main()