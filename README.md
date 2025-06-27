# 🗡 TASKBLADE

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
├── api_task_runer.py       # CLI execute with argparse -c/--config `config.json` file
├── server.py               # Flask web server
├── [anyname]-config.json   # User + Task + Step definitions
├── csv/                    # Request/response data in CSV per user
├── logs/                   # Execution logs per user
├── LICENSE                 # MIT License
└── README.md               # You're here
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
      "tasks": [
        {
          "name": "Login Flow",
          "loop": 1,
          "steps": [
            {
              "name": "Login",
              "port": "80",
              "method": "POST",
              "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer {{ token }}"
              },
              "path": "/auth/login",
              "json": {
                "num": "{{ gen_num() }}|int",
                "key": "{{ gen_key() }}",
                "text": "{{ num_to_words() }}"
              },
              "data": {},
              "files": {
                "image": "{{ gen_img() }}"
              },
              "extract": {
                "me": "json.data.variable"
              },
              "sets": {
                "x": 1
              },
              "assert": {
                "me": "{{ x }}|int"
              },
              "block": {
                "if": {
                  "me": null
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
- `{{ num_to_words() }}` — convert number to words  
- `{{ gen_img() }}` — generate image data for file uploads  
- `{{ token }}`, `{{ x }}` — dynamic values set from previous steps

The `port` field defines which backend port the request should target (e.g., `80`, `443`, `8080`), allowing flexibility per step.

---

## 🖥 Web Interface

Access TASKBLADE through a sleek Flask-based UI with the following tools:

- **CSV Viewer** – Inspect input profiles and request/response pairs  
- **Log Viewer** – Monitor task results with timestamps and status counts  
- **Playground** – Manually test GraphQL or REST endpoints  
- **Port Scanner** – Scan your local network, view open ports, and export as CSV/JSON  

---

## 📦 Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourname/taskblade.git
cd taskblade
pip install -r requirements.txt
```

Then start the web server:

```bash
python server.py
```

Visit the app in your browser:

```
http://localhost:5000
```

---

## 🧪 CLI Usage

You can execute TASKBLADE directly from the terminal using:

```bash
python api_task_runer.py -c your-config.json
```

### 🔧 Options

- `-c`, `--config` — Path to your TASKBLADE config file (required)

### 📝 Example

```bash
python api_task_runer.py -c player-tasks-config.json
```

This will:
- Run all defined tasks across user profiles
- Store API execution logs in the `logs/` folder
- Save request/response CSV data per profile in the `csv/` folder

---

## 🛡 License

TASKBLADE is released under the [MIT License](./LICENSE) by Zediek.  
You’re free to use, modify, and distribute with attribution.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 💬 Acknowledgments

- Built with Flask, Bootstrap, and pure threading magic  
- Inspired by the need for efficient, customizable testing across real-world accounts  
