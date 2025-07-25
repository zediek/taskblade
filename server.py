import copy
import difflib
import glob
import json
import os
from flask import Flask, Response, jsonify, request, render_template_string, send_file
import pandas as pd
import numpy as np
import io
import re
from datetime import timedelta
import base64
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import requests
import csv
import os
import random
from string import Template
from queue import Queue
from jinja2 import Environment, StrictUndefined, Template as JinjaTemplate
from datetime import datetime, timezone, timedelta
import uuid
from PIL import Image
import io
from num2words import num2words
import socket
import ipaddress
import subprocess




















class GenIMG:
  def run(self):
    def gen():
      img = Image.new("RGB", (1024, 720), color=(
          random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
      img_byte_arr = io.BytesIO()
      img.save(img_byte_arr, format="JPEG")
      img_byte_arr.seek(0)
      return img_byte_arr

    image_data = gen()
    encoded_data = base64.b64encode(image_data.getvalue()).decode("utf-8")

    return json.dumps({
      "filename": "test.jpg",
      "mime_type": "image/jpeg",
      "image_data": encoded_data
    })  # Note: returns JSON string


class Step:
  def __init__(self, config, globals: dict, context: dict, extract_keys: list, set_keys: list, logger: list, base_url, response_list, is_success, is_block_error):
    self.name = config.get("name", "Unnamed Step")
    
    port = config.get("port",'')
    path = config.get("path", '')

    self.url = base_url
    if port != '':
        self.url += f":{port}"
    
    if path != '':
        self.url += f"/{path}"

    self.method = config.get("method", "GET").upper()
    self.headers = config.get("headers", {})
    self.json_data = json.loads(json.dumps(config.get("json", {})))
    self.data = config.get("data", {})
    self.files = config.get("files", {})
    self.globals = globals
    self.extract = config.get("extract", {})
    self.sets = config.get("sets", {})
    self.assertions = config.get("assert", {})
    self.block_rule = config.get("block", {})
    self.context = context
    self.logger = logger

    self.gen_img = GenIMG()


    self.extract_keys = extract_keys

    self.set_keys = set_keys

    self.response_list = response_list

    self.is_success = is_success
    self.is_block_error = is_block_error

    self.jinja_env = Environment(undefined=StrictUndefined)

    if self.globals != {}:
      self.global_values()


  def interpolate(self, raw):
        if isinstance(raw, dict):
            return {k: self.interpolate(v) for k, v in raw.items()}
        elif isinstance(raw, list):
            return [self.interpolate(v) for v in raw]
        elif isinstance(raw, str):
            if "|" in raw:
                raw_part, sep, data_type = raw.partition("|")
                raw_part = raw_part.strip()
                data_type = data_type.strip().lower()

                try:
                    rendered = self.jinja_env.from_string(raw_part).render(self.context)

                    if data_type == "float":
                        return float(rendered)
                    elif data_type == "int":
                        try:
                            return int(rendered)
                        except ValueError:
                            return int(float(rendered))
                    else:
                        return rendered
                except Exception as err:
                    msg = str(err)
                    print(f"[ERROR] Failed to render '{raw_part}' as {data_type}: {msg}")

                    # Try to extract undefined variable name from error message
                    if "' is undefined" in msg:
                        var_name = msg.split("'")[1]
                        candidates = difflib.get_close_matches(var_name, self.context.keys(), n=1, cutoff=0.6)
                        if candidates:
                            try:
                                yn = input(f"[SUGGESTION] Did you mean: '{candidates[0]}' instead of '{var_name}'? [y/n] ")
                                if yn.lower() in ("y", "yes"):
                                    final_change = raw_part.replace(var_name, candidates[0])
                                    return self.interpolate(f"{final_change}|{data_type}")
                            except EOFError:
                                print("[WARNING] Cannot prompt in non-interactive mode.")
                        else:
                            print(f"[SUGGESTION] No close match found for '{var_name}'")

                    return None
                

            else:
                context = self.context.copy()

                if "gen_key()" in raw:
                    context["gen_key"] = lambda: uuid.uuid4().hex
                elif "gen_num()" in raw:
                    context["gen_num"] = lambda: random.randint(0, 9)
                elif "gen_img()" in raw:
                    context["gen_img"] = lambda: self.gen_img.run()
                elif "rpick" in raw:
                    def rpick(l:list):
                        try:
                            return random.choices(population=l, k=1)
                        except:
                            return None
                    context["rpick"] = rpick
                elif "num_to_words" in raw:
                    def num_to_words(n):
                        try:
                            n = int(n)
                            return ' '.join(w.capitalize() for w in num2words(n).split())
                        except Exception:
                            return None
                    context["num_to_words"] = num_to_words

                try:
                    rendered = self.jinja_env.from_string(raw).render(context)

                    if "gen_img()" in raw:
                        try:
                            result = json.loads(rendered.replace("'", '"'))
                            filename = result["filename"]
                            mime_type = result["mime_type"]
                            image_data = base64.b64decode(result["image_data"])
                            return (filename, io.BytesIO(image_data), mime_type)
                        except Exception as e:
                            print("Failed to parse gen_img result:", e)
                            return None
                    else:
                        return rendered
                except Exception as e:
                    print(f"[ERROR] Failed to render '{raw}': {e}")
                    return None
        else:
            return raw

  def global_values(self):
          for key, val in self.globals.items():
              fin_val = self.interpolate(val)
              self.context[key] = fin_val

  def set_values(self):
    sets = {}
    for key, var in self.sets.items():
        sets[key] = var
        if key not in self.set_keys:
            self.set_keys.append(key)


    for key, val in sets.items():
        fin_val = self.interpolate(val)
        print(f"[DEBUG] Set variable {key} → {fin_val}")
        self.context[key] = fin_val

  def extract_values(self, response):
      def get_nested(data, path):
          _json_ = {}
          keys = path.split(".")
          for key in keys:
              if isinstance(data, dict):
                  data = data.get(key)
              elif isinstance(data, list):
                  try:
                      key = int(key)
                      data = data[key]
                  except (ValueError, IndexError):
                      return None
              else:
                  return None
          return data

      try:
          if "application/json" in response.headers.get("Content-Type", ""):
              json_data = response.json()
          else:
              json_data = {}
      except Exception as e:
          self.logger.append(f"[ERROR] Failed to parse JSON: {e}")
          json_data = {}

      for var, path in self.extract.items():
          if path.startswith("json."):
              key_path = path[5:]
              extracted = get_nested(json_data, key_path)

              # If the extracted data is a string that seems to be JSON, try to parse it
              if isinstance(extracted, str):
                  try:
                      extracted = json.loads(extracted)  # Attempt to load as JSON
                  except json.JSONDecodeError:
                      pass  # If it's not valid JSON, leave it as a string

                  
              self.logger.append(f"[DEBUG] Extracting {var} from path '{key_path}' → {extracted}")

              

              self.context[var] = extracted
              if var not in self.extract_keys:
                  self.extract_keys.append(var)

  def run_assertions(self):
      results = []
      for key, assertion_list in self.assertions.items():
          if isinstance(assertion_list, (str, int, float)):
              # Convert shorthand form to standard format
              assertion_list = [{"expected": assertion_list}]
          elif isinstance(assertion_list, dict):
              # Single assertion
              assertion_list = [assertion_list]
          elif not isinstance(assertion_list, list):
              continue  # Ignore invalid formats

          for assertion in assertion_list:
              if not isinstance(assertion, dict):
                  continue  # Skip malformed entries

              expected = self.interpolate(assertion.get("expected"))
              condition = assertion.get("if")
              reason = assertion.get("reason", "")
              actual = self.context.get(key)

              if condition:
                  try:
                      if not eval(condition, {}, self.context):
                          continue  # Condition is false → skip
                  except Exception as e:
                      results.append({
                          "key": key,
                          "expected": expected,
                          "actual": actual,
                          "passed": False,
                          "error": f"[Condition Eval Error] '{condition}': {e}"
                      })
                      continue

              passed = actual == expected
              results.append({
                  "key": key,
                  "expected": expected,
                  "actual": actual,
                  "passed": passed,
                  "error": "" if passed else f"Assertion failed: expected {expected}, got {actual}. Reason: {reason}"
              })

      return results

  def run(self):
      timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
      start = time.perf_counter()
      url = self.interpolate(self.url)
      headers = self.interpolate(self.headers)
      json_data = self.interpolate(self.json_data)
      data = self.interpolate(self.data)
      files = self.interpolate(self.files)
      
      try:
          start_datetime = datetime.now()
          response = requests.request(
              method=self.method,
              url=url,
              headers=headers or None,
              json=json_data or None,
              data=data or None,
              files=files or None,
          )
          end_datetime = datetime.now()

          end = time.perf_counter()

          self.response_list.append(response)

          self.extract_values(response)

          

          self.logger.append(f"[Step: {self.name}]")
          self.logger.append(f"Start Request {start_datetime}")
          self.logger.append(f"End Request {end_datetime}")
          self.logger.append(f"→ Timestamp: {timestamp} (UTC)")
          self.logger.append(f"→ {self.method} {url}")
          self.logger.append(f"→ Status Code: {response.status_code}")
          self.logger.append(f"→ Request Headers: {headers}")


          if self.block_rule:
            condition = self.block_rule.get("if", {})
            reason = self.interpolate(self.block_rule.get("reason", "Blocked by condition"))

            if isinstance(condition, dict):
                match = all(
                    (self.context.get(k) in v if isinstance(v, list) else self.context.get(k) == v)
                    for k, v in condition.items()
                )
                if match:
                    print(f"[BLOCKED] {reason} (matched: {condition} | json: {json_data} | data: {data} | files: {files})")
                    raise Exception(f"Step blocked: {reason}")


          
          self.set_values()
          
          
          assertions = self.run_assertions()
          assertions_message = ""

          for result in assertions:
              if result["passed"]:
                  assertions_message += f"[ASSERT PASS] {result['key']} == {result['expected']}, "
              else:
                  assertions_message += f"[ASSERT FAIL] {result['error']}"

          

          if json_data:
              self.logger.append(f"→ Request JSON: {json_data}")
          elif data:
              self.logger.append(f"→ Request Data: {data}")

          self.logger.append(f"→ Request Files: {files}")

          self.logger.append(f"→ Response Headers: {response.headers}")

          content_type = response.headers.get("Content-Type", "")
          if "application/json" in content_type:
              try:
                  json_resp = response.json()
                  self.logger.append(f"→ Response JSON: {json.dumps(json_resp, indent=2)}")

              except Exception as e:
                  self.logger.append(f"→ Failed to parse JSON: {e}")
          else:
              text = response.text[:1000]
              self.logger.append(f"→ Response Text: {text}")

          self.logger.append(f"→ Assertions: {assertions_message}")

          elapsed_seconds  = end - start

          elapsed_time = timedelta(seconds=elapsed_seconds)

          # Format nicely
          days = elapsed_time.days
          hours, remainder = divmod(elapsed_time.seconds, 3600)
          minutes, seconds = divmod(remainder, 60)
          milliseconds = elapsed_time.microseconds // 1000

          self.logger.append(f"→ Elapse Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms")


          self.logger.append("\n===========================\n")

          self.is_success.append(True)
          
          

      except Exception as e:
        end = time.perf_counter()
        self.logger.append(f"→ Error: {e}")

        elapsed_seconds  = end - start

        elapsed_time = timedelta(seconds=elapsed_seconds)

        # Format nicely
        days = elapsed_time.days
        hours, remainder = divmod(elapsed_time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = elapsed_time.microseconds // 1000

        self.logger.append(f"→ Elapse Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms")

        self.logger.append("\n===========================\n")

        self.is_block_error.append(True)


class Task:
    def __init__(self, config, user_name, base_url, globals: dict, context: dict, extract_keys: list, set_keys: list, logger: list, user_podium_list: list):
      self.name = config.get("name", "Unnamed Task")
      self.globals = globals
      self.loop = config.get("loop", 1)
      self.wait = config.get("wait", 0)
      self.steps_config = config.get("steps", [])
      self.user_name = user_name
      self.base_url = base_url

      self.context = context
      self.extract_keys = extract_keys
      self.set_keys = set_keys
      self.user_podium_list = user_podium_list
      self.response_list = []
      self.is_success = []
      self.is_block_error = []
      self.logger = logger

    def run_steps(self):

      user_podium_dict = {
          "name": self.user_name,
          "task": self.name,
          "start": time.perf_counter(),
          "end": None,
          "num_of_response": None,
          "num_of_success": None,
          "num_of_blocked_error": None
      }

      for _ in range(self.loop):
          time.sleep(self.wait)
          for step_conf in self.steps_config:
              step = Step(step_conf, self.globals, self.context, self.extract_keys, self.set_keys, self.logger, self.base_url, self.response_list, self.is_success, self.is_block_error)
              step.run()

      user_podium_dict["end"] = time.perf_counter()
      user_podium_dict["num_of_response"] = len(self.response_list)
      user_podium_dict["num_of_success"] = len(self.is_success)
      user_podium_dict["num_of_blocked_error"] = len(self.is_block_error)
      self.user_podium_list.append(user_podium_dict)

    def run(self):
      self.logger.append(f"[Task] User {self.user_name} is starting task: {self.name}")
      self.run_steps()


class UserRunner:
    def __init__(self, json_data, logger):
      self.json_data = json_data
      self.users = []
      self.base_url = None
      self.user_podium_list = []
      self.logger = logger

    def parse_profiles(self, profile_string):
        name, rest = profile_string.split(":", 1)
        username, password = rest.split("@", 1)
        return {
            "name": name,
            "username": username,
            "password": password
        }
    
    def substitute_placeholders( self, data, profile):
        json_str = json.dumps(data)
        for key, val in profile.items():
            json_str = json_str.replace(f"{{{{ profile.{key} }}}}", val)
        return json.loads(json_str)
    
    def expand_users(self, config):
        all_users = []
        for user_entry in config["users"]:
            profiles = [self.parse_profiles(p) for p in user_entry.get("profiles", [])]
            for profile in profiles:
                user_copy = copy.deepcopy(user_entry)
                user_copy["name"] = profile["name"]
                globals = user_entry.get("globals",{})
                user_copy["globals"] = self.substitute_placeholders(globals, profile)
                user_copy.pop("profiles", None)  # Remove original profile string list
                user_copy["tasks"] = [
                    self.substitute_placeholders(task, profile)
                    for task in user_copy["tasks"]
                ]
                all_users.append(user_copy)
        return all_users

    def load_config(self):
      try:
          config = json.loads(self.json_data)
          self.base_url = config.get("base_url", "")
          self.users = self.expand_users(config)

          for user_conf in self.users:
              user_name = user_conf["name"]
              globals = user_conf["globals"]
              task_list = []
              context = {}
              extract_keys = []
              set_keys = []
              for task_conf in user_conf.get("tasks", []):
                  task = Task(task_conf, user_name, self.base_url, globals, context, extract_keys, set_keys, self.logger, self.user_podium_list)
                  task_list.append(task)

              user_conf["tasks"] = task_list

      except Exception as err:
        print(err)

    def run_all(self):
      with ThreadPoolExecutor(max_workers=len(self.users)) as executor:
          futures = []
          
          for user in self.users:
            user_name = user["name"]
            tasks = user["tasks"]
            future = executor.submit(self.run_user_tasks, user_name, tasks)
            futures.append(future)

          for future in as_completed(futures):
            future.result()  # Wait for all users to finish


          self.logger.append("")
          self.logger.append("")
          self.logger.append("Who is the fastest podium?")
          for podium, user in enumerate(self.user_podium_list):
            elapsed_seconds  = user["end"] - user["start"]

            elapsed_time = timedelta(seconds=elapsed_seconds)

            # Format nicely
            days = elapsed_time.days
            hours, remainder = divmod(elapsed_time.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = elapsed_time.microseconds // 1000

            self.logger.append(f"[{user['name']} {user['task']} ({str(podium+1)} place)] Elapsed time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms | Number of response: {user['num_of_response']} | Number of success: {user['num_of_success']} | Number of blocked/error {user['num_of_blocked_error']}")

    def run_user_tasks(self, user_name, tasks):
      self.logger.append(f"[UserRunner] Starting user {user_name} with {len(tasks)} tasks")
      for task in tasks:
          task.run()
      self.logger.append(f"[UserRunner] Finished user {user_name}")
  







































app = Flask(__name__)



STYLE_CSS = """

@import url('https://fonts.googleapis.com/css2?family=Anton&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&display=swap');

body {
  background-color: black;
  margin: 0;
  font-family: 'Anton', Impact, sans-serif;
  overflow: hidden;
}

.p5-container {
  padding: 60px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 20px;
}

.menu-button {
  position: relative;
  font-size: 32px;
  color: white;
  background-color: red;
  border: none;
  padding: 20px 50px;
  clip-path: polygon(0% 0%, 95% 0%, 100% 100%, 5% 100%);
  box-shadow: 5px 5px 0 white;
  cursor: pointer;
  transition: transform 0.1s ease-in-out;
}

.menu-button:hover {
  transform: translateX(10px) rotate(-1deg);
  background-color: yellow;
  color: black;
}

.menu-button::before {
  content: '▶';
  position: absolute;
  left: -40px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 28px;
  color: red;
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
}

.menu-button:hover::before {
  opacity: 1;
}

/* Subtle Persona 5 Navbar */
.navbar {
  background-color: black;
  padding: 12px 24px;
  display: flex;
  gap: 16px;
  align-items: center;
  box-shadow: 0 4px 0 red;
}

.nav-link {
  position: relative;
  display: inline-block;
  font-family: 'Anton', Impact, sans-serif;
  font-size: 16px;
  color: white;
  background-color: red;
  padding: 10px 20px;
  clip-path: polygon(0 0, 95% 0, 100% 100%, 5% 100%);
  box-shadow: 2px 2px 0 white;
  border: none;
  text-decoration: none;
  transition: transform 0.15s ease-in-out, background-color 0.2s;
}

.nav-link:hover {
  transform: translateX(4px) rotate(-1deg);
  background-color: yellow;
  color: black;
}

.nav-link::before {
  content: '▶';
  position: absolute;
  left: -16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  color: red;
  opacity: 0;
  transition: opacity 0.2s;
}

.nav-link:hover::before {
  opacity: 1;
}

.p5-card {
    font-family: 'Archivo Black', sans-serif;
    background: linear-gradient(145deg, #d40000, #9c0000);
    color: white;
    border: 4px solid #000;
    border-radius: 12px;
    box-shadow:
      6px 6px 0 #000,
      0 0 10px rgba(0, 0, 0, 0.5);
    padding: 0;
    /*max-width: 320px;*/
    margin: 2rem auto;
    transform: rotate(-1.5deg);
    overflow: hidden;
  }

  .p5-card-header {
    background: white;
    padding: 10px 15px;
    border-bottom: 3px solid black;
    transform: rotate(-2deg);
  }

  .p5-title {
    margin: 0;
    font-size: 1.6rem;
    color: black;
    text-shadow: 2px 2px #d40000;
  }

  .p5-card-body {
    padding: 15px;
    font-size: 1rem;
    line-height: 1.4;
    background: #9c0000;
  }

  .p5-btn {
    margin-top: 10px;
    background: black;
    color: #fff;
    border: 2px solid white;
    padding: 10px 16px;
    font-weight: bold;
    cursor: pointer;
    text-transform: uppercase;
    box-shadow: 3px 3px 0 #fff;
    transition: 0.1s transform ease;
  }

  .p5-btn:hover {
    transform: scale(1.05);
    background: #fff;
    color: #000;
    box-shadow: 3px 3px 0 #000;
  }

  .p5-label {
  display: block;
  font-size: 0.9rem;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.p5-input {
  width: 100%;
  padding: 10px;
  font-family: 'Archivo Black', sans-serif;
  border: 2px solid white;
  border-radius: 4px;
  background: black;
  color: white;
  font-size: 1rem;
  box-shadow: inset 2px 2px 0 #d40000, 2px 2px 0 #000;
  margin-bottom: 12px;
  outline: none;
  transition: border 0.2s ease, box-shadow 0.2s ease;
}

.p5-input::placeholder {
  color: #ccc;
  font-style: italic;
}

.p5-input:focus {
  border-color: yellow;
  box-shadow: inset 2px 2px 0 yellow, 2px 2px 0 #000;
}

.p5-table-wrapper {
  background-color: black;
  border: 4px solid red;
  box-shadow: 6px 6px 0 white;
  padding: 16px;
  margin: 30px auto;
  max-width: 90%;
  max-height: 450px;
  overflow: auto;
  font-family: 'Anton', Impact, sans-serif;
}

/* Style the actual DataFrame table */
.p5-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 600px;
}

.p5-table th,
.p5-table td {
  border: 2px solid white;
  padding: 10px;
  text-align: center;
  background-color: #111;
  color: white;
}

.p5-table th {
  background-color: red;
  color: black;
  text-transform: uppercase;
}

.p5-outlined-text {
  color: white; /* inner fill */
  font-weight: bold;
  -webkit-text-stroke: 1.5px black; /* outer stroke */
  text-shadow:
    -1px -1px 0 black,
     1px -1px 0 black,
    -1px  1px 0 black,
     1px  1px 0 black;
}


"""



HTML_INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Welcome to Universal Test App</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="{{ url_for('style_css') }}">
</head>
<body class="bg-dark text-light">
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">
        <h5 style="font-family: 'Courier New', monospace; font-weight: bold; font-size: 2rem; letter-spacing: 2px;">
        🗡 <span style="color: #dc3545;">TASK</span><span style="color: #0d6efd;">BLADE</span> 🗡
        </h5>
      </a>
      <div class="navbar-collapse">
        <ul class="navbar-nav">
          <li class="nav-item"><a class="nav-link" href="/port-scan">Advance Port Scanner</a></li>
          <li class="nav-item"><a class="nav-link" href="/csvs">CSV Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/logs">Logs Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/playground">Playground</a></li>
        </ul>
      </div>
    </div>
  </nav>

  <div class="p5-card d-flex flex-column justify-content-center align-items-center flex-grow-1 text-center p-5 mt-5">

    <!-- Logo Section -->
    <div class="p5-card-header my-4">
      <h1 style="font-family: 'Courier New', monospace; font-weight: bold; font-size: 3rem; letter-spacing: 2px;" class="p5-title">
        🗡 <span style="color: #dc3545;">TASK</span><span style="color: #0d6efd;">BLADE</span> 🗡
      </h1>
      <p class="lead" style="font-style: italic; color: #adb5bd;">
        Slice through tasks with surgical precision
      </p>
    </div>

    <!-- Welcome + Description -->
    <div class="p5-card-body">
      <h2 class="mb-3 text-light">Welcome to TASKBLADE</h2>
      <p class="lead mb-4 text-light">
        TASKBLADE is a precision-built tool for running and monitoring automated API tasks across multiple user profiles.  
        Use the CSV Viewer to inspect your input sets, explore detailed execution logs, test endpoints live in the Playground,  
        or scan your local network with the Port Scanner to detect open ports and connected devices.
      </p>

      <!-- CTA Button -->
      <a href="/playground" class="btn menu-button btn-lg">Get Started</a>
    </div>
  </div>

</body>
</html>



"""



PORT_SCAN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Advanced Port Scanner</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

   <link rel="stylesheet" href="{{ url_for('style_css') }}">
</head>
<body class="bg-dark text-light">
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">
        <h5 style="font-family: 'Courier New', monospace; font-weight: bold; font-size: 2rem; letter-spacing: 2px;">
        🗡 <span style="color: #dc3545;">TASK</span><span style="color: #0d6efd;">BLADE</span> 🗡
        </h5>
      </a>
      <div class="navbar-collapse">
        <ul class="navbar-nav">
          <li class="nav-item"><a class="nav-link" href="/port-scan">Advance Port Scanner</a></li>
          <li class="nav-item"><a class="nav-link" href="/csvs">CSV Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/logs">Logs Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/playground">Playground</a></li>
        </ul>
      </div>
    </div>
  </nav>

<div class="container-fluid py-4">
  <div class="p5-card">
    <div class="p5-card-header">
      <h1 class="p5-title">🔍 Advanced Port Scanner</h1>
    </div>
    <div class="p5-card-body">
      <form method="post" class="p-4 shadow-sm">
          <div class="mb-3">
              <label class="p5-label">Host Range:</label>
              <input type="text" class="p5-input" name="host_range" placeholder="e.g. 192.168.1.1-192.168.1.10 or host1.local-host5.local or 192.168.1.0/24" required>
          </div>
          <div class="mb-3">
              <label class="p5-label">Ports:</label>
              <input type="text" class="p5-input" name="ports" placeholder="e.g. 80,443,8080" required>
          </div>
          <button type="submit" class="p5-btn">Scan</button>
      </form>

      {% if results %}
              <h2 class="mb-3 p5-title">📊 Scan Results</h2>
              <ul class="list-group">
                  {% for host, data in results.items() %}
                      <li class="list-group-item">
                          {% set ip = host.split('(')[-1].rstrip(')') %}
                          <strong>{{ ip }}</strong>
                          {% if data.hostname %} ({{ data.hostname }}){% endif %}
                          {% if data.mac %} [MAC: {{ data.mac }}]{% endif %}
                          {% if data.ports %}
                              → Open ports: <span class="text-success">{{ data.ports }}</span>
                          {% endif %}
                      </li>
                  {% endfor %}
              </ul>

          <div class="mt-4">
              <h5>⬇️ Download Results</h5>
              <a href="/port-scan/download/json" class="btn p5-btn btn-sm me-2">Download JSON</a>
              <a href="/port-scan/download/csv" class="btn p5-btn btn-sm">Download CSV</a>
          </div>
      {% endif %}
    </div>
</div>
</body>
</html>
"""




HTML_READER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CSV Viewer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <link rel="stylesheet" href="{{ url_for('style_css') }}">
    <style>
        .my-table th, .my-table td {
          border: 1px solid #ddd;
            padding: 8px;
            max-width: 300px;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-wrap: break-word;
            vertical-align: top;
        }
        .my-table th {
            text-align: left;
        }
    </style>
</head>
<body class="bg-dark text-light">
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">
        <h5 style="font-family: 'Courier New', monospace; font-weight: bold; font-size: 2rem; letter-spacing: 2px;">
        🗡 <span style="color: #dc3545;">TASK</span><span style="color: #0d6efd;">BLADE</span> 🗡
        </h5>
      </a>
      <div class="navbar-collapse">
        <ul class="navbar-nav">
          <li class="nav-item"><a class="nav-link" href="/port-scan">Advance Port Scanner</a></li>
          <li class="nav-item"><a class="nav-link" href="/csvs">CSV Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/logs">Logs Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/playground">Playground</a></li>
        </ul>
      </div>
    </div>
  </nav>

  <div class="container-fluid">
    <div class="p5-card">
      <div class="p5-card-header">
        <h2 class="p5-title">Uploaded Report for: {{ name }}</h2>
      </div>
      <div class="p5-card-body mt-5">
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" class="p5-input" accept=".csv">
            <input type="hidden" name="filter_asserts" id="filter_asserts" class="p5-input" value="{ '1' if filter_asserts else '0' }">
            <button type="submit" class="p5-btn">Upload</button>
            <button type="button" class="p5-btn" onclick="toggleFilter() ">Upload (Assert Filter)</button>
        </form>
      </div>
    <hr>
    <div class="p5-table-wrapper">
      {{ table|safe }}
    </div>
  </div>
    
    <script>
        function toggleFilter() {
            const input = document.getElementById("filter_asserts");
            input.value = input.value === "1" ? "0" : "1";
            input.form.submit();
        }
    </script>
</body>
</html>
"""






HTML_LOGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Logs Viewer</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
   <link rel="stylesheet" href="{{ url_for('style_css') }}">
  <style>
    pre {
      background-color: #1e1e1e;
      color: #f8f9fa;
      padding: 15px;
      border-radius: 0.5rem;
      /* max-height: 70vh; */
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }
    #elapsedTimeDisplay, #overAll {
      white-space: pre-wrap;
      font-family: monospace;
      background-color: #2c2c2c;
      border-radius: 0.5rem;
      padding: 15px;
      /* margin-top: 1rem; */
      /* max-height: 70vh; */
      overflow-y: auto;
    }
  </style>
</head>
<body class="bg-dark text-light">
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">
        <h5 style="font-family: 'Courier New', monospace; font-weight: bold; font-size: 2rem; letter-spacing: 2px;">
        🗡 <span style="color: #dc3545;">TASK</span><span style="color: #0d6efd;">BLADE</span> 🗡
        </h5>
      </a>
      <div class="navbar-collapse">
        <ul class="navbar-nav">
          <li class="nav-item"><a class="nav-link" href="/port-scan">Advance Port Scanner</a></li>
          <li class="nav-item"><a class="nav-link" href="/csvs">CSV Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/logs">Logs Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/playground">Playground</a></li>
        </ul>
      </div>
    </div>
  </nav>

  <div class="container-fluid">
    <h1 class="mb-1">Logs Viewer</h1>

    
    <div class="p5-card bg-dark p-0">
      <div class="p5-card-header">
        <h5 class="p5-title">Log Dir Viewer</h5>
      </div>
      <div class="p5-card-body mt-3">

        <div class="row">
          <div class="col-md-6 p-1">
            <label for="logSelect" class="p5-label">Select Log File:</label>
            <select class="p5-input" id="logSelect"></select>
          </div>
          <div class="col-md-2 d-flex align-items-end p-1">
            <button class="btn p5-btn w-100" onclick="loadLog()">View Logs</button>
          </div>
        </div>

        <div class="row h-100">
          <div class="col-lg-8 col-md-12 col-sm-12 p-1" style="height: 35vh;">
            <pre id="logContent" class="h-100">Select a log dir to view files its contents...</pre>
          </div>
          <div class="col-lg-4 col-md-12 col-sm-12 p-1" style="height: 35vh;">
            <div id="elapsedTimeDisplay" class="text-light h-100"></div>
          </div>
          <div class="col-lg-12 col-md-12 col-sm-12 p-1" style="height: 25vh;">
            <div id="overAll" class="text-light h-100"></div>
          </div>
        </div>

      </div>










      

    </div>















  </div>

  <script>
    async function loadLogList() {
      const res = await fetch('/list-dirs');
      const dirs = await res.json();
      const select = document.getElementById('logSelect');
      select.innerHTML = '';
      dirs.forEach(dir => {
        const option = document.createElement('option');
        option.value = dir;
        option.textContent = dir;
        select.appendChild(option);
      });
    }

    async function loadLog() {
      const dir = document.getElementById('logSelect').value;
      const res = await fetch(`/view-log?dir=${encodeURIComponent(dir)}`);
      if (res.ok) {
        const data = await res.json();
        let output = '';
        for (const [k, l] of  Object.entries(data)) {
          output += `${k}\\n`;
          output += l;
          output += "\\n##############################\\n\\n";
        }
        document.getElementById('logContent').textContent = output;
        showElapsedTime();
      } else {
        document.getElementById('logContent').textContent = 'Failed to load log file.';
      }
    }

    async function showElapsedTime() {
      const dir = document.getElementById('logSelect').value;
      const res = await fetch(`/elapsed-time?dir=${encodeURIComponent(dir)}`);
      const data = await res.json();
      const el = document.getElementById('elapsedTimeDisplay');
      const ov = document.getElementById('overAll');

      if (!data || Object.keys(data).length === 0) {
        el.textContent = 'No step-based elapsed time found.';
        return;
      }

      let output = '';
      
      if (data && typeof data.users === 'object' && data.users !== null) {
        for (const [user, info] of Object.entries(data.users)) {
          output += `${user}\n`;
          for (const [step, info2] of Object.entries(info)) {
            output += `\t[Step: ${step}]\n\tStart From First Req: ${info2.start_from_first_request}\n\tEnd From Last Req: ${info2.end_from_last_request}\n\t${info2.elapsed_time}\n\t${info2.average_success_time}\n\tSuccessful Responses: ${info2.success_count}\n\tFailed/Error Responses: ${info2.fail_count}\n\n`;
          }
        }
      }

      el.textContent = output.trim();


      output = '';
      if (data && typeof data.total_of_users === 'number' && data.total_of_users !== null) {
        output += `Total of Users: ${data.total_of_users}\n\n`
      }
      if  (data && typeof data.longest_elapse === 'object' && data.longest_elapse !== null) {
        output += `[Longest]\nUser: ${data.longest_elapse.user}\nStep: ${data.longest_elapse.step}\nStart From First Req: ${data.longest_elapse.start_from_first_request}\nEnd From Last Req: ${data.longest_elapse.end_from_last_request}\n${data.longest_elapse.elapsed_time}\n\n`
      }
      if (data && typeof data.over_all === 'object' && data.over_all !== null) {
        for (const [step, info] of Object.entries(data.over_all)) {
          output += `[Step: ${step}]\n${info.total_elapsed_time}\n${info.total_average_success_time}\nTotal Successful Responses: ${info.total_success_count}\nTotal Failed/Error Responses: ${info.total_fail_count}\n\n`
        }
      }

      ov.textContent = output.trim();

      
    }

    loadLogList();
  </script>
</body>
</html>


"""





HTML_PLAYGROUND_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Playground</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://unpkg.com/blockly/blockly.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.23.1/ace.js"></script>
  <link rel="stylesheet" href="{{ url_for('style_css') }}">
  <style>
    body { margin: 0; display: flex; flex-direction: column; height: 100vh; font-family: monospace; }
    #topBar {
      background: #222; color: white; padding: 10px;
      display: flex; align-items: center; gap: 10px;
    }
    #blocklyEditor { display: flex; flex: 1; }
    #blocklyDiv { width: 70%; height: 100%; }
    #editorDiv {
      width: 30%; height: 100%;
      background: #1e1e1e; color: #dcdcdc;
      position: relative;
    }
    #jsonOutputLabel {
      position: absolute;
      top: 5px; left: 10px;
      color: #ccc;
      font-size: 12px;
      z-index: 10;
    }
    #aceEditor {
      position: absolute;
      top: 30px; bottom: 0; left: 0; right: 0;
    }
    button {
      background: #444; color: white; border: none; padding: 5px 10px;
      cursor: pointer; border-radius: 4px;
    }
    .log-label {
      top: 5px; left: 10px;
      color: #ccc;
      font-size: 12px;
      z-index: 10;
    }
    .log-content {
      background-color: #1e1e1e;
      color: #f8f9fa;
      width: 101.2%;
    }
    pre {
      background-color: #272822;
      
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
      width:100%;
      height: 15vh;
      font-size: 8pt !important;
    }

    .blocklyText {
      font-size: 8pt !important; /* Adjust size as needed */
    }
  </style>
</head>
<body class="bg-dark text-light">
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">
        <h5 style="font-family: 'Courier New', monospace; font-weight: bold; font-size: 2rem; letter-spacing: 2px;">
        🗡 <span style="color: #dc3545;">TASK</span><span style="color: #0d6efd;">BLADE</span> 🗡
        </h5>
      </a>
      <div class="navbar-collapse">
        <ul class="navbar-nav">
          <li class="nav-item"><a class="nav-link" href="/port-scan">Advance Port Scanner</a></li>
          <li class="nav-item"><a class="nav-link" href="/csvs">CSV Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/logs">Logs Viewer</a></li>
          <li class="nav-item"><a class="nav-link" href="/playground">Playground</a></li>
        </ul>
      </div>
    </div>
  </nav>

  <div class="container-fluid" id="topBar">
    <button onclick="downloadJSON()" class="p5-btn">Download JSON</button>
    <input type="file" id="fileInput" class="p5-input" onchange="uploadJSON()" accept=".json" />
    <button class="p5-btn" onclick="runJSON()">Run</button>
  </div>

  <div id="blocklyEditor">
    <div id="blocklyDiv" class="p5-card p-1"></div>
    <div id="editorDiv" class="p5-card mt-1">
      <div id="p5-title">Edit JSON here (syncs to blocks):</div>
      <div id="aceEditor"></div>
    </div>
  </div>

  <div class="container-fluid">
  <div class="p5-card">
    <div class="p5-card-header">
        <h5 class="p5-title mt-0">Logs:</h5>
      </div>
    <div class="p5-card-body h-100">
        <pre id="logContent" class="mt-4"></pre>

    </div>
    </div>
  </div>


  <xml id="toolbox" style="display: none">
    <block type="base_block"></block>
    <block type="user_block"></block>
    <block type="task_block"></block>
    <block type="step_block"></block>
    <block type="key_value"></block>
    <block type="profile_block"></block>
    <block type="global_block"></block>
  </xml>

  <script>
    // Block Definitions
    Blockly.Blocks['base_block'] = {
      init: function() {
        this.appendDummyInput()
            .appendField("Base URL")
            .appendField(new Blockly.FieldTextInput("127.0.0.1:5000"), "BASE_URL");
        this.appendStatementInput("USERS")
            .setCheck("user_block")
            .appendField("Users");
        this.setColour(20);
      }
    };

    Blockly.Blocks['user_block'] = {
      init: function() {
        this.appendStatementInput("PROFILES")
          .setCheck("profile_block")
          .appendField("Profiles");
        this.appendStatementInput("GLOBALS")
        .setCheck("global_block")
        .appendField("Globals");
        this.appendStatementInput("TASKS")
            .setCheck("task_block")
            .appendField("Tasks");
        this.setColour(230);
        this.setPreviousStatement(true, "user_block");
        this.setNextStatement(true, "user_block");
      }
    };

    Blockly.Blocks['profile_block'] = {
      init: function() {
        this.appendDummyInput()
            .appendField("Profile credentials")
            .appendField(new Blockly.FieldTextInput(""), "CREDENTIALS");
        this.setColour(50);
        this.setPreviousStatement(true, "profile_block");
        this.setNextStatement(true, "profile_block");
      }
    };

    Blockly.Blocks['global_block'] = {
      init: function() {
        this.appendStatementInput("GLOBALS")
            .setCheck("key_value")
            .appendField("Globals");
        this.setColour(120);
        this.setPreviousStatement(true, "global_block");
        this.setNextStatement(true, "global_block");
      }
    };

    Blockly.Blocks['task_block'] = {
      init: function() {
        this.appendDummyInput()
            .appendField("Task name")
            .appendField(new Blockly.FieldTextInput(""), "NAME");
        this.appendDummyInput()
            .appendField("Task loop")
            .appendField(new Blockly.FieldNumber(1), "LOOP");
        this.appendDummyInput()
            .appendField("Task wait")
            .appendField(new Blockly.FieldNumber(0), "WAIT");
        this.appendStatementInput("STEPS")
            .setCheck("step_block")
            .appendField("Steps");
        this.setColour(160);
        this.setPreviousStatement(true, "task_block");
        this.setNextStatement(true, "task_block");
      }
    };

    Blockly.Blocks['step_block'] = {
      init: function() {
        this.appendDummyInput().appendField("Step name").appendField(new Blockly.FieldTextInput(""), "NAME");
        this.appendDummyInput().appendField("Port").appendField(new Blockly.FieldTextInput("80"), "PORT");
        this.appendDummyInput().appendField("Path").appendField(new Blockly.FieldTextInput("/api/path"), "PATH");
        this.appendDummyInput().appendField("Method").appendField(new Blockly.FieldDropdown([
          ["GET", "GET"], ["POST", "POST"], ["PUT", "PUT"], ["DELETE", "DELETE"]
        ]), "METHOD");
        ["HEADERS", "JSON", "DATA", "FILES", "EXTRACT", "SETS", "ASSERT", "BLOCK"].forEach(label => {
          this.appendStatementInput(label).setCheck("key_value").appendField(label.charAt(0) + label.slice(1).toLowerCase());
        });
        this.setColour(90);
        this.setPreviousStatement(true, "step_block");
        this.setNextStatement(true, "step_block");
      }
    };

    Blockly.Blocks['key_value'] = {
      init: function() {
        this.appendDummyInput()
            .appendField("Key")
            .appendField(new Blockly.FieldTextInput("key"), "KEY")
            .appendField("Value")
            .appendField(new Blockly.FieldTextInput("value"), "VALUE");
        this.setPreviousStatement(true, "key_value");
        this.setNextStatement(true, "key_value");
        this.setColour(200);
      }
    };

    const workspace = Blockly.inject('blocklyDiv', {
      toolbox: document.getElementById('toolbox'),
      scrollbars: true,
      trashcan: true
    });

    function profilecredentials(block) {
      const values = [];
      while (block) {
        const value = block.getFieldValue("CREDENTIALS");
        if (value !== null) {
          values.push(value);
        }
        block = block.getNextBlock();
      }
      return values;
    }

    function collectKeyValuePairs(block) {
      const obj = {};
      while (block) {
        const key = block.getFieldValue("KEY");
        let value = block.getFieldValue("VALUE");
        try {
          value = JSON.parse(value);
        } catch {
          // Keep as string if not parseable JSON
        }
        obj[key] = value;
        block = block.getNextBlock();
      }
      return obj;
    }

    function generateJSONFromBlock(block) {
      if (!block) return null;
      switch (block.type) {
        case "base_block":
          return {
            base_url: block.getFieldValue("BASE_URL"),
            users: generateStatementJSON(block, "USERS")
          };
        case "user_block":
          return {
            profiles: profilecredentials(block.getInputTargetBlock("PROFILES")),
            globals: generateGlobalsFromBlock(block.getInputTargetBlock("GLOBALS")),
            tasks: generateStatementJSON(block, "TASKS")
          };
        case "global_block":
          return collectKeyValuePairs(block.getInputTargetBlock("GLOBALS"));
        case "task_block":
          return {
            name: block.getFieldValue("NAME"),
            loop: block.getFieldValue("LOOP"),
            wait: block.getFieldValue("WAIT"),
            steps: generateStatementJSON(block, "STEPS")
          };
        case "step_block":
          return {
            name: block.getFieldValue("NAME"),
            port: block.getFieldValue("PORT"),
            path: block.getFieldValue("PATH"),
            method: block.getFieldValue("METHOD"),
            headers: collectKeyValuePairs(block.getInputTargetBlock("HEADERS")),
            json: collectKeyValuePairs(block.getInputTargetBlock("JSON")),
            data: collectKeyValuePairs(block.getInputTargetBlock("DATA")),
            files: collectKeyValuePairs(block.getInputTargetBlock("FILES")),
            extract: collectKeyValuePairs(block.getInputTargetBlock("EXTRACT")),
            sets: collectKeyValuePairs(block.getInputTargetBlock("SETS")),
            assert: collectKeyValuePairs(block.getInputTargetBlock("ASSERT")),
            block: collectKeyValuePairs(block.getInputTargetBlock("BLOCK")),
          };
        default:
          return null;
      }
    }

    function generateGlobalsFromBlock(globalBlock) {
      if (!globalBlock) return {};
      return generateJSONFromBlock(globalBlock); // global_block returns key-value object
    }

    function generateStatementJSON(block, inputName) {
      const arr = [];
      let child = block.getInputTargetBlock(inputName);
      while (child) {
        const obj = generateJSONFromBlock(child);
        if (obj) arr.push(obj);
        child = child.getNextBlock();
      }
      return arr;
    }

    function generateJSON() {
      const baseBlock = workspace.getTopBlocks(true).find(b => b.type === 'base_block');
      if (!baseBlock) return "";
      return JSON.stringify(generateJSONFromBlock(baseBlock), null, 2);
    }

    const editor = ace.edit("aceEditor");
    editor.setTheme("ace/theme/monokai");
    editor.session.setMode("ace/mode/json");
    editor.setOptions({ fontSize: "8pt", showPrintMargin: false });
    editor.setReadOnly(true);

    workspace.addChangeListener(() => {
      try {
        const jsonStr = generateJSON();
        if (editor.getValue() !== jsonStr) {
          editor.setValue(jsonStr, -1);
        }
      } catch (e) {}
    });

    // Default block on load
    window.addEventListener('load', () => {
      //const base = workspace.newBlock('base_block');
      //base.initSvg(); base.render();
      //base.moveBy(20, 20);

      const defaultContent = {
      "base_url": "http://127.0.0.1",
      "users": [
        {
          "profiles": [
            "Admin:admin@password"
          ],
          "globals": {},
          "tasks": [
            {
              "name": "Admin Task",
              "loop": 1,
              "wait": 0,
              "steps": [
                {
                  "name": "Login",
                  "port": "5000",
                  "path": "login",
                  "method": "POST",
                  "headers": {
                    "Content-Type": "application/json"
                  },
                  "json": {
                    "username": "\\{\\{ profile.username \\}\\}",
                    "password": "\\{\\{ profile.password \\}\\}"
                  },
                  "extract": {
                    "success": "json.success",
                    "message": "json.message",
                  },
                  "sets": {
                    
                  },
                  "assert": {
                  
                  },
                  "block": {
                    "if": {
                      "success": false,
                    },
                    "reason": "\\{\\{ message \\}\\}"
                  }
                }
              ]
            }
          ]
        }
      ]
    };

    loadJsonToBlockly(defaultContent);

    });

    // File operations
    function downloadJSON() {
      const json = generateJSON();
      const blob = new Blob([json], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "blockly_output.json";
      a.click();
    }

    function uploadJSON() {
      const file = document.getElementById("fileInput").files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const json = JSON.parse(e.target.result);
          loadJsonToBlockly(json);
          editor.setValue(JSON.stringify(json, null, 2), -1);
        } catch (err) {
          alert("Invalid JSON file.");
        }
      };
      reader.readAsText(file);
    }

    function connectBlocksChain(blocks, input) {
      if (!blocks.length) return;
      input.connection.connect(blocks[0].previousConnection);
      for (let i = 0; i < blocks.length - 1; i++) {
        blocks[i].nextConnection.connect(blocks[i + 1].previousConnection);
      }
    }

    function createKeyValueBlocks(data) {
      const blocks = [];
      for (const key in data) {
        const value = data[key];
        const block = workspace.newBlock("key_value");
        block.setFieldValue(key, "KEY");
        // stringify object or array, else keep as string
        if (typeof value === "string") {
          block.setFieldValue(value, "VALUE");
        } else {
          block.setFieldValue(JSON.stringify(value, null, 2), "VALUE");
        }
        block.initSvg();
        block.render();
        blocks.push(block);
      }
      return blocks;
    }

    function createStepBlock(data) {
      const step = workspace.newBlock("step_block");
      step.setFieldValue(data.name || "", "NAME");
      step.setFieldValue(data.port || "", "PORT");
      step.setFieldValue(data.path || "", "PATH");
      step.setFieldValue(data.method || "GET", "METHOD");

      ["headers", "json", "data", "files", "extract", "sets", "assert", "block"].forEach(key => {
        const blocks = createKeyValueBlocks(data[key] || {});
        connectBlocksChain(blocks, step.getInput(key.toUpperCase()));
      });

      step.initSvg();
      step.render();
      return step;
    }

    function createTaskBlock(data) {
    console.log(data)
      const task = workspace.newBlock("task_block");
      task.setFieldValue(data.name || "", "NAME");
      
      // Validate and set LOOP value (must be a number between 1 and 999)
      let loopValue = Number(data.loop);
      if (!Number.isInteger(loopValue) || loopValue < 1 || loopValue > 999) {
        loopValue = 1; // default fallback
      }
      task.setFieldValue(loopValue, "LOOP");

      let waitValue = Number(data.wait);
      if (!Number.isFinite(waitValue) || waitValue < 0 || waitValue > 86400) {
        waitValue = 0;
      }

      task.setFieldValue(waitValue, "WAIT");

      const stepBlocks = (data.steps || []).map(createStepBlock);
      connectBlocksChain(stepBlocks, task.getInput("STEPS"));

      task.initSvg();
      task.render();
      return task;
    }

    function createProfileBlock(credential) {
      if (typeof credential !== "string") return null;

      const profileBlock = Blockly.getMainWorkspace().newBlock("profile_block");
      profileBlock.setFieldValue(credential, "CREDENTIALS");
      profileBlock.initSvg();
      profileBlock.render();

      return profileBlock;
    }

    function createUserBlock(data) {
      const user = workspace.newBlock("user_block");
      const profileBlock = (data.profiles || []).map(createProfileBlock);
      
      connectBlocksChain(profileBlock, user.getInput("PROFILES"));

      const taskBlocks = (data.tasks || []).map(createTaskBlock);
      connectBlocksChain(taskBlocks, user.getInput("TASKS"));

      const globalWrapper = workspace.newBlock("global_block");
      const globalKV = createKeyValueBlocks(data.globals || {});
      connectBlocksChain(globalKV, globalWrapper.getInput("GLOBALS"));
      globalWrapper.initSvg(); globalWrapper.render();
      user.getInput("GLOBALS").connection.connect(globalWrapper.previousConnection);

      user.initSvg();
      user.render();
      return user;
    }

    

    function createBaseBlock(data) {
      const base = workspace.newBlock("base_block");
      base.setFieldValue(data.base_url || "", "BASE_URL");

      const userBlocks = (data.users || []).map(createUserBlock);
      connectBlocksChain(userBlocks, base.getInput("USERS"));

      base.initSvg();
      base.render();
      base.moveBy(20, 20);
      return base;
    }

    function loadJsonToBlockly(data) {
      workspace.clear();
      if (!data) return;
      const baseBlock = createBaseBlock(data);
      baseBlock.select();
      Blockly.svgResize(workspace);
      workspace.render();
    }

    async function runJSON() {
      try {
        const json = generateJSON(); // Your function that generates the JSON
        const res = await fetch('/run_json', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ json }) // Same as { json: json }
        });

        if (!res.ok) {
          document.getElementById('logContent').textContent = `Request failed with status ${res.status}`;
        }

        const data = await res.json();
        document.getElementById('logContent').textContent = data.logs;
        // Do something with `data`
      } catch (err) {
        document.getElementById('logContent').textContent = 'Error in runJSON:';
      }
    }

  </script>
</body>
</html>



"""





LOG_FOLDER = './logs'  # Update with your logs directory path


@app.route('/')
def index():
    return render_template_string(HTML_INDEX_TEMPLATE)





last_scan_results = {}


def is_local_ip(ip):
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False

def get_hostname(ip):
    if not is_local_ip(ip):
        return None
    try:
        res = socket.gethostbyaddr(ip)
        # print("hostname",res[0])
        return res[0]
    except socket.herror:
        return None

def get_mac(ip):
    if not is_local_ip(ip):
        return None
    try:
        subprocess.run(['ping', '-n', '1', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = subprocess.run(['arp', '-a', ip], capture_output=True, text=True, timeout=2)
        for line in result.stdout.splitlines():
            if ip in line:
                parts = line.split()
                for p in parts:
                    if '-' in p or ':' in p:
                        # print("mac",p)
                        return p
    except Exception as e:
        print(f"MAC error for {ip}: {e}")
    return None

def scan_host(ip, port):
    try:
        with socket.create_connection((ip, port), timeout=0.5):
            return port
    except:
        return None

def generate_dns_range(start, end):
    match1 = re.match(r'([a-zA-Z\-]+?)(\d+)\.(.+)', start)
    match2 = re.match(r'([a-zA-Z\-]+?)(\d+)\.(.+)', end)
    if not match1 or not match2:
        raise ValueError("Invalid DNS hostname range format.")
    prefix1, num1, domain1 = match1.groups()
    prefix2, num2, domain2 = match2.groups()
    if prefix1 != prefix2 or domain1 != domain2:
        raise ValueError("Start and end hostnames must share prefix and domain.")
    num1, num2 = int(num1), int(num2)
    return [f"{prefix1}{i}.{domain1}" for i in range(num1, num2 + 1)]

def resolve_to_ip(hostname):
    try:
        return socket.gethostbyname(hostname)
    except socket.error:
        return None

def expand_targets(host_input):
    host_input = host_input.strip()
    targets = []
    if '/' in host_input:
        net = ipaddress.ip_network(host_input, strict=False)
        targets = [str(ip) for ip in net.hosts()]
    elif '-' in host_input:
        parts = host_input.split('-')
        try:
            start = ipaddress.IPv4Address(parts[0].strip())
            end = ipaddress.IPv4Address(parts[1].strip())
            for ip_block in ipaddress.summarize_address_range(start, end):
                targets.extend(str(ip) for ip in ip_block)
        except:
            targets = generate_dns_range(parts[0].strip(), parts[1].strip())
    else:
        targets = [host_input]
    return targets



from flask import Response

@app.route("/style.css")
def style_css():
    return Response(STYLE_CSS, mimetype="text/css")


@app.route('/port-scan', methods=['GET', 'POST'])
def port_scanner():
    global last_scan_results
    results = {}
    if request.method == 'POST':
        host_input = request.form.get('host_range')
        port_input = request.form.get('ports')
        ports = [int(p.strip()) for p in port_input.split(',') if p.strip().isdigit()]
        try:
            hostnames = expand_targets(host_input)
            resolved_targets = [(h, resolve_to_ip(h)) for h in hostnames]
            resolved_targets = [(h, ip) for h, ip in resolved_targets if ip]

            with ThreadPoolExecutor(max_workers=100) as executor:
                futures = {}
                for host, ip in resolved_targets:
                    for port in ports:
                        future = executor.submit(scan_host, ip, port)
                        futures[(host, port, ip)] = future

                for (host, port, ip), future in futures.items():
                    if future.result():
                        key = f"{host} ({ip})"
                        results.setdefault(key, {"hostname": None, "mac": None, "ports": []})
                        results[key]["ports"].append(port)

            # enrich results with MAC and hostname for local IPs
            for key in results:
                ip = key.split('(')[-1].rstrip(')')
                if is_local_ip(ip):
                    hostname = get_hostname(ip) or ip
                    results[key]["hostname"] = hostname
                    results[key]["mac"] = get_mac(ip)

            if not results:
                results = {"No responsive hosts found.": {"ports": [], "hostname": None, "mac": None}}

        except Exception as e:
            results = {f"Error: {str(e)}": {"ports": [], "hostname": None, "mac": None}}

    last_scan_results = results
    return render_template_string(PORT_SCAN_TEMPLATE, results=results,STYLE_CSS=STYLE_CSS)

@app.route('/port-scan/download/json')
def download_json():
    json_data = json.dumps(last_scan_results, indent=2)
    return Response(
        json_data,
        mimetype='application/json',
        headers={
            "Content-Disposition": "attachment; filename=port_scan_results.json"
        }
    )

@app.route('/port-scan/download/csv')
def download_csv():
    import io
    si = io.StringIO()
    cw = csv.writer(si)

    cw.writerow(['Host', 'Hostname', 'MAC Address', 'Open Ports'])
    for host, data in last_scan_results.items():
        cw.writerow([
            host,
            data.get('hostname') or '',
            data.get('mac') or '',
            ', '.join(map(str, data.get('ports', [])))
        ])

    output = si.getvalue()
    return Response(output, mimetype='text/csv',
                    headers={"Content-Disposition": "attachment; filename=port_scan_results.csv"})





@app.route('/csvs', methods=['GET', 'POST'])
def csvs():
  table_html = "<p>No file uploaded yet.</p>"
  name = ""
  filter_asserts = True

  if request.method == 'POST':
      uploaded_file = request.files.get('file')
      filter_asserts = request.form.get("filter_asserts", "1") == "1"

      if uploaded_file and uploaded_file.filename.endswith('.csv'):
          name = uploaded_file.filename.split('-')[0]
          try:
              content = uploaded_file.read().decode("utf-8")
              df = pd.read_csv(io.StringIO(content))
              df = df.replace(np.nan, "")

              if filter_asserts and 'assertions' in df.columns:
                  df = df[df['assertions'].str.contains(r'\[ASSERT (PASS|FAIL)\]', na=False)]

              table_html = df.to_html(classes='my-table', index=False, escape=False)
          except Exception as e:
              table_html = f"<p>Error reading file: {e}</p>"

  return render_template_string(HTML_READER_TEMPLATE, table=table_html, name=name, filter_asserts=filter_asserts)

@app.route('/playground', methods=['GET', 'POST'])
def playground():  
  return render_template_string(HTML_PLAYGROUND_TEMPLATE)

@app.route('/run_json', methods=['GET', 'POST'])
def run_json():
  if request.method == 'POST':
      data = request.get_json()
      logger = []
      json_data = data["json"]
      runner = UserRunner(json_data, logger)
      runner.load_config()
      runner.run_all()

      logs = "\n".join(logger)

      return jsonify({"logs": logs})
  
  return jsonify({"message": ""})


@app.route('/logs')
def logs():
    return render_template_string(HTML_LOGS_TEMPLATE)

@app.route('/list-dirs')
def list_dirs():
    log_dirs = glob.glob(os.path.join(LOG_FOLDER, '*'))


    dir_paths = [os.path.basename(p) for p in log_dirs]

    return jsonify(dir_paths)


    # log_files = []
    # for log_dir in log_dirs:
    #   log_files += glob.glob(os.path.join(log_dir.replace("\\", "/"), "*.log"))

    # filenames = [os.path.basename(f) for f in log_files]
    # return jsonify(filenames)

@app.route('/view-log')
def view_log():
    log_dir = os.path.join(LOG_FOLDER, request.args.get('dir'))
    data = {}
    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        if os.path.isfile(file_path):
            try:
                # Read file content as UTF-8 text
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    data[str(filename).split("-")[0]] = content  # Add filename and content to result
            except Exception as e:
                return jsonify({'error': 'File not found'}), 404

    return jsonify(data)


@app.route('/elapsed-time')
def elapsed_time():
    log_dir = os.path.join(LOG_FOLDER, request.args.get('dir'))
    data = {}
    for filename in os.listdir(log_dir):
      file_path = os.path.join(log_dir, filename)
      if os.path.isfile(file_path):
          try:
              # Read file content as UTF-8 text
              with open(file_path, 'r', encoding='utf-8') as f:
                  content = f.read()
                  data[str(filename).split("-")[0]] = content  # Add filename and content to result
          except Exception as e:
              return jsonify({'error': 'File not found'}), 404
          

    def parse_elapse_time(line):
        match = re.search(r'Elapse Time:\s*(\d+)d\s+(\d+)h\s+(\d+)m\s+(\d+)s\s+(\d+)ms', line)
        if match:
            days, hours, minutes, seconds, milliseconds = map(int, match.groups())
            return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)
        return timedelta(0)
    
    def get_start_end_req(line):
      match = re.search(r"(?:Start Request|End Request) (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)", line)
      if not match:
          return None

      dt_str = match.group(1).strip()
      dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
      # millis = int(dt.microsecond / 1000)
      return dt.strftime(f"%a, %d %b %Y %H:%M:%S.%f")

    elapsed_by_step = {}
    current_step = None

    inside_json_block = False
    buffer = []
    brace_count = 0
    is_success = False

    start_requests = {}
    end_requests = {}

    for key in data:
        elapsed_by_step[key] = {}
        start_requests[key] = {}
        end_requests[key] = {}
        for line in data[key].splitlines():
            line = line.strip()
            

            # Step detection
            step_match = re.match(r'\[Step:\s*(.+?)\]', line)

            if step_match:
                current_step = step_match.group(1)
                if current_step not in elapsed_by_step[key]:
                    start_requests[key][current_step] = []
                    end_requests[key][current_step] = []
                    elapsed_by_step[key][current_step] = {
                        'elapsed_time': timedelta(),
                        'start_from_first_request': None,
                        'end_from_last_request': None,
                        'success_count': 0,
                        'average_success_time': timedelta(),
                        'fail_count': 0
                    }

            if current_step and 'Start Request' in line:
              start_requests[key][current_step].append(get_start_end_req(line))

              if len(start_requests[key][current_step]) == 1:
                elapsed_by_step[key][current_step]['start_from_first_request'] = start_requests[key][current_step][0]

            if current_step and 'End Request' in line:
              end_requests[key][current_step].append(get_start_end_req(line))

              if len(end_requests[key][current_step]) >= 1:
                elapsed_by_step[key][current_step]['end_from_last_request'] = end_requests[key][current_step][-1]

            # Elapsed time accumulation
            if current_step and 'Elapse Time:' in line:
              elapsed_by_step[key][current_step]['elapsed_time'] += parse_elapse_time(line)

            # JSON detection start
            if 'Response JSON:' in line:
                inside_json_block = True
                buffer = []
                brace_count = 0

                # Capture JSON on the same line (after 'Response JSON:')
                json_part = line.split('Response JSON:', 1)[1].strip()
                if json_part:
                    buffer.append(json_part)
                    brace_count += json_part.count('{') - json_part.count('}')
                continue

            # Continue capturing JSON block lines
            if inside_json_block == True:
                buffer.append(line)
                brace_count += line.count('{') - line.count('}')

                # JSON block ended
                if brace_count <= 0:
                    json_text = "\n".join(buffer)
                    try:
                        json_obj = json.loads(json_text)
                        if json_obj:
                            elapsed_by_step[key][current_step]['success_count'] += 1
                            is_success = True
                        else:
                            elapsed_by_step[key][current_step]['fail_count'] += 1
                            is_success = False
                    except Exception:
                        try:
                          elapsed_by_step[key][current_step]['fail_count'] += 1
                        except:
                            pass
                        is_success = False

                    inside_json_block = False
                    buffer = []

        
            if '→ Error:' in line:
                elapsed_by_step[key][current_step]['fail_count'] += 1
                is_success = False

            if current_step and 'Elapse Time:' in line and is_success == True:
              elapsed_by_step[key][current_step]['average_success_time'] += parse_elapse_time(line)
                    


    # Format response
    result = {}
    json_data = {}

    
    
    
    result["users"] = {}

    over_all_list = []
    over_all_dir = {}

    for user, data in elapsed_by_step.items():
      json_data[user] = data
      for step in json_data[user]:
        over_all_dir[step] = {
          "total_elapse_time": timedelta(),
          "total_average_success_time": timedelta(),
          "total_success_count": 0,
          "total_fail_count": 0
        }


    

    json_data = {}
    max_elapsed_ms = -1
    
    for user, data in elapsed_by_step.items():
        json_data[user] = data
        result["users"][user] = {}

        
        for step in json_data[user]:
          td = json_data[user][step]['elapsed_time']
          total_ms = int(td.total_seconds() * 1000)
          days, rem = divmod(total_ms, 86400000)
          hours, rem = divmod(rem, 3600000)
          minutes, rem = divmod(rem, 60000)
          seconds, milliseconds = divmod(rem, 1000)

          over_all_dir[step]["total_elapse_time"] += td
          

          over_all_dir[step]["total_success_count"] += json_data[user][step]['success_count']
          over_all_dir[step]["total_fail_count"] += json_data[user][step]['fail_count']

          if total_ms > max_elapsed_ms:
            max_elapsed_ms = total_ms
            result["longest_elapse"] = {
              "user": user,
              "step": step,
              "elapsed_time": f"Elapse Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms",
              'start_from_first_request': json_data[user][step]['start_from_first_request'],
              'end_from_last_request': json_data[user][step]['end_from_last_request'],
            }
            
          
          result["users"][user][step] = {
              'elapsed_time': f"Elapse Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms",
              'start_from_first_request': json_data[user][step]['start_from_first_request'],
              'end_from_last_request': json_data[user][step]['end_from_last_request'],
              'success_count': json_data[user][step]['success_count'],
              'average_success_time': None,
              'fail_count': json_data[user][step]['fail_count']
          }

          

          if int(json_data[user][step]['success_count']) > 0:
            average_seconds = json_data[user][step]['average_success_time'].total_seconds() / json_data[user][step]['success_count']
            average = timedelta(seconds=average_seconds)
            total_ms = int(average.total_seconds() * 1000)
            days, rem = divmod(total_ms, 86400000)
            hours, rem = divmod(rem, 3600000)
            minutes, rem = divmod(rem, 60000)
            seconds, milliseconds = divmod(rem, 1000)
            result["users"][user][step]["average_success_time"] = f"Average Success Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms"

            over_all_dir[step]["total_average_success_time"] += json_data[user][step]['average_success_time']
          else:
              result["users"][user][step]["average_success_time"] = "N/A"

    result["over_all"] = {}

    result["total_of_users"] = len(result["users"])

    json_data = {}
    for step, data in over_all_dir.items():
        json_data[step] = data

        ttd = json_data[step]['total_elapse_time']
        total_ms = int(ttd.total_seconds() * 1000)
        days, rem = divmod(total_ms, 86400000)
        hours, rem = divmod(rem, 3600000)
        minutes, rem = divmod(rem, 60000)
        seconds, milliseconds = divmod(rem, 1000)

        result["over_all"][step] = {
          "total_elapsed_time": f"Total Elapse Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms",
          "total_success_count": json_data[step]["total_success_count"],
          "total_average_success_time": None,
          "total_fail_count": json_data[step]["total_fail_count"]
        }

        

        if int(json_data[step]["total_success_count"]) > 0:
          total_average_seconds = json_data[step]['total_average_success_time'].total_seconds() / json_data[step]["total_success_count"]
          average = timedelta(seconds=total_average_seconds)
          total_ms = int(average.total_seconds() * 1000)
          days, rem = divmod(total_ms, 86400000)
          hours, rem = divmod(rem, 3600000)
          minutes, rem = divmod(rem, 60000)
          seconds, milliseconds = divmod(rem, 1000)

          result["over_all"][step]["total_average_success_time"] = f"Total Average Success Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms"
    
    return jsonify(result)




# Mock user
mock_users = [
    {'id': 1, 'username': 'admin', 'password': 'password'},
    {'id': 2, 'username': 'user1', 'password': 'password'}
]

mock_user_sessions = []

@app.route('/login', methods=['POST'])
def login():
  data = request.get_json()
  if not data:
    return jsonify({'success': False, 'message': 'Missing JSON body'}), 400

  username = data.get('username')
  password = data.get('password')

  for user in mock_users:
    if user['username'] == username and user['password'] == password:
      # Check if session already exists
      if any(s['user_id'] == user['id'] for s in mock_user_sessions):
        return jsonify({'success': False, 'message': 'User already logged in'}), 403

      # Create new session
      token = uuid.uuid4().hex
      mock_user_sessions.append({
        'id': len(mock_user_sessions) + 1,
        'user_id': user['id'],
        'token': token
      })
      return jsonify({'success': True, 'message': 'Login successful', 'token': token})

  return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/logout', methods=['GET'])
def logout():
  auth_token = request.headers.get('Authentication')  # safer than direct indexing

  
  for i, s in enumerate(mock_user_sessions):
    if auth_token and s['token'] == auth_token:
      mock_user_sessions.pop(i)

      return jsonify({"message": "Logout Success!"})

  return jsonify({"message": "Missing authentication header"}), 401
    


@app.route('/users', methods=['GET'])
def users():
  auth_token = request.headers.get('Authentication')  # safer than direct indexing

  if auth_token and any(s['token'] == auth_token for s in mock_user_sessions):
    return jsonify({"users": [{"id": user['id'],"username": user['username']} for user in mock_users]})
  else:
    return jsonify({"message": "Missing authentication header"}), 401







if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=5000)
