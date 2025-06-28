# taskblade.py
import os
import sys
import platform
import subprocess

def main():
    args = sys.argv[1:]

    if not args:
        return self_update()

    cmd = args[0]

    if cmd == "serve":
        subprocess.run([sys.executable, "server.py"])

    elif cmd == "-c" and len(args) > 1:
        subprocess.run([sys.executable, "api_task_runer.py", "-c", args[1]])

    elif cmd == "scan":
        subprocess.run([sys.executable, "port_scanner.py"])  # optional

    else:
        print(f"❌ Unknown command: {cmd}")
        return show_help()

def show_help():
    print("Usage:")
    print("  taskblade serve            # Run the web server")
    print("  taskblade -c config.json   # Run the task runner")
    print("  taskblade scan             # Run the port scanner")
    print("  taskblade                  # Check for updates and refresh packages")

def self_update():
    print("🔄 Checking for updates...")

    # Make sure git is available
    if not os.path.isdir(".git"):
        print("⚠️  This is not a git repository.")
        return

    try:
        subprocess.run(["git", "pull"], check=True)
    except Exception as e:
        print(f"❌ Git pull failed: {e}")
        return

    print("📦 Updating .venv packages...")

    pip_path = None
    if platform.system() == "Windows":
        pip_path = ".venv\\Scripts\\pip.exe"
    else:
        pip_path = ".venv/bin/pip"

    if not os.path.exists(pip_path):
        print(f"❌ Could not find pip in .venv: {pip_path}")
        return

    try:
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✅ .venv is now up to date.")
    except Exception as e:
        print(f"❌ Package update failed: {e}")
