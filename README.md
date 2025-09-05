<p align="center">
  <img src="./assets/taskblade-banner.png" alt="TASKBLADE Logo" width="400"/>
</p>

> **Slice through tasks with surgical precision.**  
> A multi-threaded, multi-user API task runner with a powerful web interface.

---

## 📌 Overview

**TASKBLADE** is a precision-built tool for running and monitoring automated API tasks across multiple user profiles.  
It supports structured task definitions with templating, parallel execution per user, and a responsive web interface for viewing logs, testing APIs, and scanning local networks.

---

## 🚀 Features

- 🧠 **Multi-user parallel execution** via threads  
- 🛠 **Dynamic task scripting** with Jinja2 templating  
- 📂 **CSV input viewer** for profile inspection  
- 📋 **Live log viewer** with response tracking  
- 🌐 **Playground** for manual API/GraphQL testing  
- 🛰 **Port Scanner** to detect open ports and devices on your local network  
- 🕵️ **Structured JSON-based configuration** for users and task flows  

---

## 🗂 Folder Structure

```
TASKBLADE/
├── taskblade.py            # Main CLI entry point (called by `taskblade` command)
├── server.py               # Flask web interface
├── api_task_runer.py       # CLI task runner (used internally)
├── port_scanner.py         # Scan local network via port/s
├── setup.cfg               # Package metadata and entry point config
├── pyproject.toml          # Optional modern Python packaging support
├── [anyname]-config.json   # User + Task + Step definitions
├── csv/                    # Request/response data in CSV per user
├── logs/                   # Execution logs per user
├── store/                  # stores data
├── LICENSE                 # MIT License
├── README.md               # Project documentation
└── .venv/                  # (Optional) Virtual environment folder
```

---

## ⚙️ Configuration

Define your users and tasks in a single `config.json` file:

```json
{
  "base_url": "https://example.com",
  "users": [
    {
      "profiles": ["Player1:player1@pw1", "Player2:player2@pw2"],
      "globals": {},
      "store_data": "players",
      "tasks": [
        {
          "name": "Task Name",
          "loop": 1,
          "steps": [
            {
              "name": "Step Name",
              "port": "80",
              "method": "GET",
              "headers": {
                "Content-Type": "application/json"
              },
              "path": "something",
              "json": {
                "num": "{{ gen_num() }}|int",
                "key": "{{ gen_key() }}",
                "add_increase": "{{ rinc([1,2,3],'+') }}",
                "date_today": "{{ rdate() }}",
                "set_date": "{{ rdate(2025-07-30) }}",
                "random_choice": "{{ rpick([1,2,3,4,5]) }}",
                "text": "{{ num_to_words(1) }}"
                
              },
              "data": {},
              "files": {
                "image": "{{ gen_img() }}",
                "image_text": "{{ gen_img('Testing') }}"
              },
              "extract": {
                "y": "json.data.variable"
              },
              "sets": {
                "x": 1
              },
              "assert": {
                "y": "{{ x }}|int"
              },
              "block": {
                "if": {
                  "y": null
                },
                "reason": ""
              }
            }
          ]
        }
      ]
    }
  ]
}
```

You can use the following in your templates:
- `{{ profile.name }}`, `{{ profile.username }}`, `{{ profile.password }}` — per-profile values  
- `{{ gen_num() }}` — generate a number  
- `{{ gen_key() }}` — generate a random key or string
- `{{ gen_img() }}` or `{{ gen_img('Testing') }}` — generate image data with text for file uploads  
- `{{ rinc([1,2,3],'+') }}` or `{{ rinc([{"val":1},{"val":2},{"val":3}],'+',"val") }}` — set list, symbol(+ or *) or key(dictionary key) to resolve increase calculation
- `{{ rdate() }}` or `{{ rdate(2025-07-30) }}` — set date or get today's date
- `{{ rpick([1,2,3,4,5]) }}` — randomly pick data inside list
- `{{ num_to_words(1) }}` — converts a numeric value to its word form (e.g., 42 → "forty-two") 
- `{{ x }}` — dynamic key variable value set from previous or current steps
- `{{ y }}` — dynamic key variable value extracted from previous or current responses

---

## 🔧 Users Configuration – Explained

Each user defines list of users, assign global variables or tasks.
Below is the breakdown of what each field does how it works.

---

### 👥 `profiles`

A list of users of combination of name, username, password.

```json
"profiles": ["Player1:player1@pw1"]
```

---

### 🌐 `globals`

Are user-scoped key–value pairs, accessible to all tasks and steps within the same user, not shared across users, and act like constants that cannot be changed or overwritten.

---

### 💾 `store_data`

A per-user persistence mechanism that saves and reloads data into a <username>.store file inside the specified folder.

- Scope: Defined under a user.
- Stored Data: Only the user’s globals, and values updated through extract and set under steps.
- Updates: When steps run, changes from extract and set are automatically written to the .store file.
- Reloading: On the next run, the user’s globals are automatically loaded back from their .store file.
- Isolation: Each user has their own .store file, not shared with others.

```json
"store_data": "players"
```
File structure example inside folder store:
```
store/
└── players/
    ├── Player1.store
    └── Player2.store
```

---

### 📝 `tasks`

Are user-scoped collections of steps that define a sequence of actions to be executed.

---

## 🔧 Tasks Configuration – Explained

Each tasks defines number of loop, wait to execute steps under current task.
Below is the breakdown of what each field does how it works.

---

### 🏷️ `name`

A label for the task. This is useful for identifying what the task does.

```json
"name": "First Task"
```

---

### 🔄 `loop`

A control structure that repeatedly executes group of sets of instructions until a certain condition is met or for a specified number of times.

```json
"loop": 1
```

---

### ⏳ `wait`

A pause in a process for a set time or until something happens.

```json
"wait": 0
```

---

### ⎘ `steps`

Are the individual actions or instructions that make up a task in your system.

---

## 🔧 Steps Configuration – Explained

Each step defines one HTTP request or logic block in your workflow.
Below is a breakdown of what each field does and how it works.

---

### 🏷️ `name`

A label for the step. This is useful for identifying what the step does, especially when reading logs or debugging.

```json
"name": "Login Step"
```

---

### 🌐 `port`

The port number used to send the request.

- Use `80` for HTTP  
- `443` for HTTPS  
- `8080` for custom services or proxies

```json
"port": "443"
```

---

### 📬 `method`

The HTTP method to use for the request (GET, POST, PUT, DELETE, etc.).

```json
"method": "POST"
```

---

### 🧾 `headers`

Optional HTTP headers to include with the request.  
Supports dynamic values using template syntax (e.g., tokens, content types).

```json
"headers": {
  "Content-Type": "application/json",
  "Authorization": "Bearer {{ token }}"
}
```

---

### 🛣️ `path`

The relative URL path of the request, appended to the base URL.

```json
"path": "api/login"
```

---

### 📦 `json`

Defines the JSON body of the request.  
You can use template expressions to dynamically fill in values.

```json
"json": {
  "username": "{{ profile.username }}",
  "password": "{{ profile.password }}"
}
```

---

### 📋 `data`

Use this for `application/x-www-form-urlencoded` POST bodies.  
It's an alternative to `json`.

```json
"data": {
  "email": "user@example.com",
  "code": "123456"
}
```

---

### 🖼️ `files`

Used to upload files (e.g., images or documents).  
You can auto-generate file data using `{{ gen_img() }}`.

```json
"files": {
  "avatar": "{{ gen_img() }}"
}
```

---

### 🧪 `extract`

Allows you to capture part of the response and store it in a variable.

```json
"extract": {
  "token": "json.data.token"
}
```

---

### 🧰 `sets`

Lets you manually assign variables for later use in the task.

```json
"sets": {
  "x": 1
}
```

---

### ✅ `assert`

Asserts that a variable or result matches the expected value.  
If the check fails, the step fails.

```json
"assert": {
  "x": 1
}
```

---

### 🚫 `block`

Conditionally skips the step based on a logic rule.  
Useful when previous steps fail or return unexpected results.

```json
"block": {
  "if": {
    "token": null
  },
  "reason": "Missing token in login response"
}
```

---

## 🖥 Web Interface

Access TASKBLADE through a sleek Flask-based UI with the following tools:

- **CSV Viewer** – Inspect input profiles and request/response pairs  
- **Log Viewer** – Monitor task results with timestamps and status counts  
- **Playground** – Manually test GraphQL or REST endpoints  
- **Port Scanner** – Scan your local network, view open ports, and export as CSV/JSON  

---

## 📦 Installation

### Clone the repository:

```bash
git clone https://github.com/yourname/taskblade.git
cd taskblade
```

### ⚙️ Command Line Setup
Once installed (via .venv or globally), you can use the taskblade command directly from your terminal.
### ✅ How to Install
Make sure you're inside your virtual environment:

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install --force-reinstall .
```
This will register the taskblade command.

---

## 🖥️ CLI Commands
After installation, you can run:

### ▶️ Start the Web Interface

```bash
taskblade serve
```
Launches the Flask-based UI.

### 🚀 Run Tasks from Config

```bash
taskblade -c your-config.json
```
Executes all tasks as defined in your JSON configuration.

#### 🔧 Options

- `-c` — Path to your TASKBLADE config file (required)

This will:
- Run all defined tasks across user profiles
- Store API execution logs in the `logs/` folder
- Save request/response CSV data per profile in the `csv/` folder

### 🧪 Debug
To check which Python environment is being used:

```bash
taskblade --debug
```
(To implement this, just add a --debug flag in your CLI and print sys.executable.)

---

## 🛡 License

**TASKBLADE** is released under the [MIT License](./LICENSE) by Zediek.  
You are free to use, modify, and distribute it — just keep the original credit.

This is open-source software, provided *as-is* with no warranties.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 💬 Acknowledgments

- Built with Flask, Bootstrap, and pure threading magic  
- Inspired by the need for efficient, customizable testing across real-world accounts  

---

## 🙌 Why I Shared This

This project was built out of necessity — I had limited tools but wanted a better workflow for testing APIs across multiple users.

I’m sharing it for free, with no donation links, no paid versions — just as a contribution to the community.

If it helps you, feel free to use or improve it. That’s enough thanks.
