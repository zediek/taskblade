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
          "name": "Task Name",
          "loop": 1,
          "steps": [
            {
              "name": "Step Name",
              "port": "80",
              "method": "GET",
              "headers": {
                "Content-Type": "application/json",
              },
              "path": "something",
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
- `{{ num_to_words() }}` — convert number to words  
- `{{ gen_img() }}` — generate image data for file uploads  
- `{{ x }}` — dynamic value set from previous steps
- `{{ y }}` — value extracted from previous responses

---

## 🔧 Step Configuration – Explained

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
