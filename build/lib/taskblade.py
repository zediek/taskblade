# taskblade.py

import os
import sys
import platform
import subprocess

def main():
    args = sys.argv[1:]

    if not args:
        return show_help()

    cmd = args[0]
    arg1 = " ".join(str(args[1]) for i in range(1, len(args)) )

    if cmd == "serve":
        subprocess.run([sys.executable, "server.py"])

    elif cmd == "-c":
        if not arg1:
            print("❌ Please provide a config file: taskblade -c your-config.json")
            return
        
        subprocess.run([sys.executable, "api_task_runer.py", "-c", arg1])

    elif cmd == "scan":
        subprocess.run([sys.executable, "port_scanner.py", " ".join([args[i] for i in range(len(args)) if i != 0 ])])

    elif cmd == "check_update":
        self_update()

    elif cmd == "--debug":
        print("🧪 Python executable:", sys.executable)
        print("Platform:", platform.system())

    else:
        print(f"❌ Unknown command: {cmd}")
        show_help()

def show_help():
    print("🗡 TASKBLADE - Multi-user API Task Runner")
    print("Usage:")
    print("  taskblade serve              # Run the web server")
    print("  taskblade -c config.json     # Run tasks via config file")
    print("  taskblade scan 80            # Scan local network via port/s (optional)")
    print("  taskblade check_update       # Pull latest changes and update packages")
    print("  taskblade --debug            # Show current Python executable")
    print("  taskblade                    # Show this help menu")

def self_update():
    print("🔄 Checking for updates...")

    if not os.path.isdir(".git"):
        print("⚠️  Not a Git repository. Skipping update.")
        return

    try:
        subprocess.run(["git", "pull"], check=True)
        print("✅ Repository updated.")
    except Exception as e:
        print(f"❌ Git pull failed: {e}")
        return

    print("📦 Updating .venv packages...")

    pip_path = ".venv\\Scripts\\pip.exe" if platform.system() == "Windows" else ".venv/bin/pip"

    if not os.path.exists(pip_path):
        print(f"❌ Pip not found at: {pip_path}")
        return

    try:
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✅ .venv packages updated.")
    except Exception as e:
        print(f"❌ Package update failed: {e}")
