import argparse
import ast
import base64
import json
import math
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
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import re
import copy
from num2words import num2words
import difflib
from decimal import Decimal
from pyfiglet import Figlet
from colorama import Fore, Style, init, Back
from pathlib import Path


class StoreData:
    def __init__(self, filename=None, data:dict={}):
        self.filename = filename
        self.data = data.get("data",[])
        self.store_dir = Path("store")  # fixed /store directory

        # Make sure /store exists
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _get_store_path(self):
        if not self.filename:
            return None

        # Always save inside /store and ensure .store extension
        path = self.store_dir / self.filename
        if path.suffix != ".store":
            path = path.with_suffix(".store")
        return path

    def save_data(self):
        path = self._get_store_path()
        if path == None:
            return None
        try:
            with open(path, "w+", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_data(self):
        path = self._get_store_path()
        if path == None:
            return None
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return self.data
    
     # Context manager support
    def __enter__(self):
        """When entering 'with', load existing data (if file exists)."""
        try:
            self.load_data()
        except FileNotFoundError:
            self.data = {}
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """When exiting 'with', save the data."""
        self.save_data()



class GenIMG:
    def run(self, text:str):
        def gen():
            width, height = 1024, 720
            img = Image.new("RGB", (width, height), color="red")
            draw = ImageDraw.Draw(img)

            # Persona-style concentric rings
            cx, cy = width // 2, height // 2
            max_radius = int((width**2 + height**2)**0.5)
            red_width = 100
            black_width = 30
            radius = max_radius
            while radius > 0:
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill="black")
                radius -= black_width
                if radius <= 0:
                    break
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill="red")
                radius -= red_width

            # Font setup
            font_size = 30
            try:
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except:
                font = ImageFont.load_default()

            spacing = 1
            left_margin = 80
            right_margin = 80
            max_line_width = width - left_margin - right_margin

            # Word-based line wrapping
            words = text.split(" ")
            lines = []
            current_line = ""
            current_width = 0

            for word in words:
                word_width = sum(draw.textbbox((0, 0), c, font=font)[2] + spacing for c in word)
                space_width = font_size // 2  # space between words

                if current_line:
                    if current_width + space_width + word_width > max_line_width:
                        lines.append(current_line)
                        current_line = word
                        current_width = word_width
                    else:
                        current_line += " " + word
                        current_width += space_width + word_width
                else:
                    current_line = word
                    current_width = word_width

            if current_line:
                lines.append(current_line)

            # Vertical centering
            total_height = len(lines) * font_size
            start_y = (height - total_height) // 2

            def draw_text_with_outline(draw, pos, text, font, stroke_width=5, fill="black", stroke_fill="white"):
                x, y = pos
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), text, font=font, fill=stroke_fill)
                draw.text((x, y), text, font=font, fill=fill)

            # Centered text rendering within margins
            y = start_y
            for line in lines:
                total_line_width = sum(
                    draw.textbbox((0, 0), c, font=font)[2] + spacing if c != " " else font_size // 2
                    for c in line
                ) - spacing

                x = left_margin + (max_line_width - total_line_width) // 2

                for char in line:
                    if char == " ":
                        x += font_size // 2
                        continue
                    bbox = draw.textbbox((0, 0), char, font=font)
                    w = bbox[2] - bbox[0]
                    h = bbox[3] - bbox[1]
                    draw_text_with_outline(draw, (x, y - h // 2), char, font)
                    x += w + spacing
                y += font_size

            # Encode the image as base64
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG")
            img_bytes.seek(0)
            return img_bytes

        image_data = gen()
        encoded = base64.b64encode(image_data.getvalue()).decode("utf-8")
        return json.dumps({
            "filename": "calling_card.jpg",
            "mime_type": "image/jpeg",
            "image_data": encoded
        })



class Step:
    def __init__(self, config, globals, context: dict, extract_keys: list, set_keys: list, logger, csv_writer, base_url, response_list, is_success, is_block_error):
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
        self.csv_writer = csv_writer

        self.gen_img = GenIMG()


        self.extract_keys = extract_keys

        self.set_keys = set_keys

        self.response_list = response_list

        self.diagnostic_reasoning = []

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
                    self.logger.append(f"[ERROR] Failed to render '{raw_part}' as {data_type}: {msg}")

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
                                self.logger.append("[WARNING] Cannot prompt in non-interactive mode.")
                        else:
                            self.logger.append(f"[SUGGESTION] No close match found for '{var_name}'")

                    return None
                

            else:
                context = self.context.copy()

                if "gen_key()" in raw:
                    context["gen_key"] = lambda: uuid.uuid4().hex
                elif "gen_num()" in raw:
                    context["gen_num"] = lambda: random.randint(0, 9)
                elif "gen_img" in raw:
                    def gen_img(t:str = "TAKE YOUR HEART"):
                        return self.gen_img.run(t)
                    context["gen_img"] = gen_img
                elif "rinc" in raw:
                    def rinc(lst: list, sym: str = "+", key: str = None):
                        """
                        rinc = resolve + increase.
                        Supports "+" and "*" operations over a list of values or dicts with a given key.
                        """
                        try:
                            values = [(x[key] if isinstance(x, dict) and key else x) for x in lst]
                            if sym == "+":
                                return sum(values)
                            elif sym == "*":
                                result = 1
                                for v in values:
                                    result *= v
                                return result
                        except Exception:
                            return None
                    context["rinc"] = rinc
                elif "rdate" in raw:
                    def rdate(d:str=None):
                        try:
                            if d == None:
                                d = str(datetime.now().date())
                            return datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d")
                        except:
                            return None
                    context["rdate"] = rdate
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
                elif "word_lists" in raw:
                    def word_lists(file:str=None, index:int=0):
                        try:
                            with open(file=file, mode="r", encoding="utf-8") as wordlist_data:
                                contents = wordlist_data.read().split("\n")
                                return contents[index]
                            
                        except:
                            return None
                        
                    context["word_lists"] = word_lists
                elif "lapp" in raw:
                    def lapp(var_key: str, new_data=None):
                        try:
                            var = self.context.get(var_key, [])

                            # If stored as a string → try to parse
                            if isinstance(var, str):
                                try:
                                    var = json.loads(var)
                                except Exception:
                                    try:
                                        var = ast.literal_eval(var)
                                    except Exception:
                                        print(f"[lapp warning] {var_key} could not be parsed, resetting to []")
                                        var = []

                            # Enforce list
                            if not isinstance(var, list):
                                print(f"[lapp error] {var_key} is not a list (got {type(var).__name__}), resetting")
                                var = []

                            # If new_data looks like a JSON string → parse it
                            if isinstance(new_data, str):
                                try:
                                    new_data = json.loads(new_data)
                                except Exception:
                                    try:
                                        new_data = ast.literal_eval(new_data)
                                    except Exception:
                                        pass  # keep raw string if truly meant to be string

                            # Append safely
                            var.append(new_data)

                            # Store back
                            # self.context[var_key] = var[:]
                            return var[:]  # return copy of list
                        except Exception as e:
                            print(f"[lapp exception] {e}")
                            return None

                    context["lapp"] = lapp
                elif "lpop" in raw:
                    def lpop(var_key: str, target_value = None, except_target_value = None, index: int = -1):
                        try:
                            # Get existing value or default to list
                            var = self.context.get(var_key, [])

                            # If stored as a string → try to parse
                            if isinstance(var, str):
                                try:
                                    var = json.loads(var)
                                except Exception:
                                    try:
                                        var = ast.literal_eval(var)
                                    except Exception:
                                        print(f"[lpop warning] {var_key} could not be parsed, resetting to []")
                                        var = []

                            # Enforce list
                            if not isinstance(var, list):
                                print(f"[lpop error] {var_key} is not a list (got {type(var).__name__}), resetting")
                                var = []

                            # Pop logic
                            if target_value is None and except_target_value is None:
                                if var:  # avoid IndexError
                                    var.pop(index)

                            elif target_value is None and except_target_value is not None:
                                # keep only items that match except_target_value
                                new_var = []
                                for v in var:
                                    if isinstance(v, dict) and except_target_value in v.values():
                                        new_var.append(v)
                                var = new_var

                            else:  # target_value provided
                                new_var = []
                                for v in var:
                                    if isinstance(v, dict) and target_value in v.values():
                                        continue  # skip matched
                                    new_var.append(v)
                                var = new_var

                            # Store back
                            # self.context[var_key] = var[:]
                            return var[:]  # return copy of list
                        except Exception as e:
                            print(f"[lpop exception] {e}")
                            return None
                        
                    context["lpop"] = lpop

                elif "lfind" in raw:
                    def lfind(var_key: str, find_value):
                        try:
                            find_results = []
                            for c in self.context[var_key]:
                                if isinstance(c, dict) and find_value in c.values():
                                    find_results.append(c)

                            return find_results[:]
                        except Exception as e:
                            return None



                    context["lfind"] = lfind

                try:
                    rendered = self.jinja_env.from_string(raw).render(context)

                    if "gen_img" in raw:
                        try:
                            result = json.loads(rendered.replace("'", '"'))
                            filename = result["filename"]
                            mime_type = result["mime_type"]
                            image_data = base64.b64decode(result["image_data"])
                            return (filename, io.BytesIO(image_data), mime_type)
                        except Exception as e:
                            self.logger.append("Failed to parse gen_img result:", e)
                            return None
                    else:
                        return rendered
                except Exception as e:
                    self.logger.append(f"[ERROR] Failed to render '{raw}': {e}")
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
            print(f"[ERROR] Failed to parse JSON: {e}")
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

                    
                print(f"[DEBUG] Extracting {var} from path '{key_path}' → {extracted}")

                

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
                
                actual = self.context.get(key)

                reason = assertion.get("reason", "")

                self.assert_with_diagnostics(expected, actual)
                diagnostic_reasoning = self.diagnostic_reasoning

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
                            "error": f"[Condition Eval Error] '{condition}': {e}",
                            "diagnostic_reasoning": ""
                        })
                        continue

                passed = actual == expected
                results.append({
                    "key": key,
                    "expected": expected,
                    "actual": actual,
                    "passed": passed,
                    "error": "" if passed else f"Assertion failed: expected {expected}, got {actual}. Reason: {reason}",
                    "diagnostic_reasoning": diagnostic_reasoning
                })


        return results

    def assert_with_diagnostics(self, expected, output):
        """
        Assert expected == output, else try to guess possible reasons.
        Works with numbers, strings, datetimes, and decimals.
        """
        if expected == output:
            print("✅ Assertion passed")
            return True

        print("❌ Assertion failed")
        print(f"Expected: {expected!r} ({type(expected).__name__}), Got: {output!r} ({type(output).__name__})")

        # 🔹 Type mismatch
        if type(expected) != type(output):
            self.diagnostic_reasoning.append("Type mismatch (e.g., int vs str, float vs Decimal)")

        # 🔹 Numeric tolerance check
        try:
            if abs(float(expected) - float(output)) < 1e-6:
                self.diagnostic_reasoning.append("Numeric precision issue (rounding/float error)")
        except Exception:
            pass

        # 🔹 String formatting check
        try:
            if str(expected).strip() == str(output).strip():
                self.diagnostic_reasoning.append("Whitespace/formatting issue")
            if str(expected).lower() == str(output).lower():
                self.diagnostic_reasoning.append("Case sensitivity issue")
        except Exception:
            pass

        # 🔹 Decimal vs float mismatch
        if isinstance(expected, (float, Decimal)) and isinstance(output, (float, Decimal)):
            if round(float(expected), 2) == round(float(output), 2):
                self.diagnostic_reasoning.append("Rounded values match (decimal vs float mismatch)")

        # 🔹 Date/Datetime formatting mismatch
        if isinstance(expected, (datetime, str)) or isinstance(output, (datetime, str)):
            try:
                exp_dt = expected if isinstance(expected, datetime) else datetime.fromisoformat(str(expected))
                out_dt = output if isinstance(output, datetime) else datetime.fromisoformat(str(output))
                if exp_dt == out_dt:
                    self.diagnostic_reasoning.append("Datetime format mismatch (same moment, different string)")
            except Exception:
                pass

        # 🔹 Sign flip check (both ways)
        try:
            if abs(float(expected)) == abs(float(output)) and expected != output:
                self.diagnostic_reasoning.append("Sign error (positive vs negative mismatch)")
        except Exception:
            pass

        # 🔹 Operator mistake guess (add vs subtract)
        try:
            diff = float(output) - float(expected)
            if diff != 0:
                self.diagnostic_reasoning.append(f"Possible operator mistake: output differs by {diff} (maybe used '+' instead of '-' or vice versa)")
        except Exception:
            pass

        # 🔹 General fallback
        if not self.diagnostic_reasoning:
            self.diagnostic_reasoning.append("Unknown difference (needs manual inspection)")

        print("🔎 Possible reasons:")
        for r in self.diagnostic_reasoning:
            print(" -", r)

        return False


    def run(self):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        start = time.perf_counter()
        url = self.interpolate(self.url)
        headers = self.interpolate(self.headers)
        json_data = self.interpolate(self.json_data)
        data = self.interpolate(self.data)
        files = self.interpolate(self.files)

        log_data = []
        
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

            log_data = [
                f"[Step: {self.name}]",
                f"Start Request {start_datetime}",
                f"End Request {end_datetime}",
                f"→ Timestamp: {timestamp} (UTC)",
                f"→ {self.method} {url}",
                f"→ Status Code: {response.status_code}",
                f"→ Request Headers: {headers}"
            ]


            if self.block_rule:
                condition = self.block_rule.get("if", {})
                reason = self.interpolate(self.block_rule.get("reason", "Blocked by condition"))

                if reason == None:
                    reason = response.reason

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
                    assertions_message += f"[ASSERT FAIL] {result['error']}\n"
                    assertions_message += f"""
    DIAGNOSTICS:
        {result["diagnostic_reasoning"]}


                    """

            

            if json_data:
                log_data.append(f"→ Request JSON: {json_data}")
            elif data:
                log_data.append(f"→ Request Data: {data}")

            log_data.append(f"→ Request Files: {files}")

            log_data.append(f"→ Response Headers: {response.headers}")

            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    json_resp = response.json()
                    log_data.append(f"→ Response JSON: {json.dumps(json_resp, indent=2)}")
                    self.csv_writer.writerow({
                        "timestamp": timestamp,
                        "step": self.name,
                        "status_code": response.status_code,
                        "url": url,
                        "request_json": json_data, 
                        "request_data": data,
                        "files": files,
                        "response": json.dumps(json_resp),
                        "extract_variables": [{extract_key: self.context[extract_key]} for extract_key in self.extract_keys],
                        "set_variables": [{set_key: self.context[set_key]} for set_key in self.set_keys],
                        "assertions": assertions_message,
                    })
                except Exception as e:
                    log_data.append(f"→ Failed to parse JSON: {e}")
            else:
                text = response.text[:1000]
                log_data.append(f"→ Response Text: {text}")
                self.csv_writer.writerow({
                    "timestamp": timestamp,
                    "step": self.name,
                    "status_code": response.status_code,
                    "url": url,
                    "request_json": json_data,
                    "request_data": data,
                    "files": files,
                    "response": text,
                    "extract_variables": [{extract_key: self.context[extract_key]} for extract_key in self.extract_keys],
                    "set_variables": [{set_key: self.context[set_key]} for set_key in self.set_keys],
                    "assertions": assertions_message,
                })
            log_data.append(f"→ Extract Variables: {[{extract_key: self.context[extract_key]} for extract_key in self.extract_keys]}")
            log_data.append(f"→ Set Variables: {[{set_key: self.context[set_key]} for set_key in self.set_keys]}")
            log_data.append(f"→ Assertions: {assertions_message}")

            elapsed_seconds  = end - start

            elapsed_time = timedelta(seconds=elapsed_seconds)

            # Format nicely
            days = elapsed_time.days
            hours, remainder = divmod(elapsed_time.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = elapsed_time.microseconds // 1000

            log_data.append(f"→ Elapse Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms")


            self.logger.write("\n".join(log_data) + "\n===========================\n")

            self.is_success.append(True)
            
            

        except Exception as e:
            end = time.perf_counter()
            log_data.append(f"→ Error: {e}")

            elapsed_seconds  = end - start

            elapsed_time = timedelta(seconds=elapsed_seconds)

            # Format nicely
            days = elapsed_time.days
            hours, remainder = divmod(elapsed_time.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = elapsed_time.microseconds // 1000

            log_data.append(f"→ Elapse Time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms")

            self.logger.write("\n".join(log_data) + "\n===========================\n")

            self.is_block_error.append(True)


class Task:
    def __init__(self, config_path, config, code, user_name, base_url, globals: dict, store_data: str, context: dict, extract_keys: list, set_keys: list, user_podium_list: list):
        self.config_path = config_path
        self.globals = globals
        self.store_data = store_data
        self.code = code
        self.name = config.get("name", "Unnamed Task")
        self.loop = config.get("loop", 1)
        self.wait = config.get("wait", 0)
        self.steps_config = config.get("steps", [])
        self.user_name = user_name
        self.base_url = base_url
        self.logfile_path = self._prepare_log_file()
        self.csvfile_path = self._prepare_csv_file()
        self.store_file_path = self._prepare_store_file()

        self.context = context
        self.extract_keys = extract_keys
        self.set_keys = set_keys
        self.user_podium_list = user_podium_list
        self.response_list = []
        self.is_success = []
        self.is_block_error = []

    def _prepare_log_file(self):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        dir_name = str(self.config_path).replace(".json", "")+"-"+str(self.code)+"-"+timestamp
        os.makedirs("logs", exist_ok=True)
        os.makedirs("logs/"+dir_name, exist_ok=True)
        
        path = os.path.join("logs/"+dir_name, f"{self.user_name}-audit_log.log")
        return path

    def _prepare_csv_file(self):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        dir_name = str(self.config_path).replace(".json", "")+"-"+str(self.code)+"-"+timestamp
        os.makedirs("csv", exist_ok=True)
        os.makedirs("csv/"+dir_name, exist_ok=True)
        
        path = os.path.join("csv/"+dir_name, f"{self.user_name}.csv")
        if not os.path.exists(path):
            with open(path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["timestamp", "step", "status_code", "url", "request_json", "request_data", "files", "response", "extract_variables", "set_variables", "assertions",])
                writer.writeheader()
        return path
    
    def _prepare_store_file(self):
        os.makedirs("store", exist_ok=True)
        os.makedirs("store/"+self.store_data, exist_ok=True)
        store_instance = StoreData(self.store_data+"/"+self.user_name)
        path = store_instance._get_store_path()
        if not path or not os.path.exists(path):
            store_instance.save_data()
        
        return self.store_data+"/"+self.user_name


    def run_steps(self):
        file_name = str(self.config_path).replace(".json", "")
        with open(self.logfile_path, "a", encoding="utf-8") as logger_file, open(self.csvfile_path, "a", newline="", encoding="utf-8") as csv_file, StoreData(self.store_file_path) as store_file:
            writer = csv.DictWriter(csv_file, fieldnames=["timestamp", "step", "status_code", "url", "request_json", "request_data", "files", "response", "extract_variables", "set_variables", "assertions",])

            user_podium_dict = {
                "name": self.user_name,
                "task": self.name,
                "start": time.perf_counter(),
                "end": None,
                "num_of_response": None,
                "num_of_success": None,
                "num_of_blocked_error": None
            }

            if store_file.data:
                self.context = store_file.data

            for loop in range(self.loop):
                time.sleep(self.wait if loop > 0 else 0)
                for step_conf in self.steps_config:
                    if len(self.is_block_error) == 0:
                        step = Step(step_conf, self.globals, self.context, self.extract_keys, self.set_keys, logger_file, writer, self.base_url, self.response_list, self.is_success, self.is_block_error)
                        step.run()
                    else:
                        continue

            def safe_parse(raw_str):
                if not isinstance(raw_str, str):
                    return raw_str
                
                cleaned = raw_str.replace("'None'", "None")
                try:
                    return ast.literal_eval(cleaned)
                except Exception:
                    return raw_str

            for content_key in self.context:
                try:
                    self.context[content_key] = json.loads(self.context[content_key])
                except Exception:
                    self.context[content_key] = safe_parse(self.context[content_key])

            store_file.data = self.context

            user_podium_dict["end"] = time.perf_counter()
            user_podium_dict["num_of_response"] = len(self.response_list)
            user_podium_dict["num_of_success"] = len(self.is_success)
            user_podium_dict["num_of_blocked_error"] = len(self.is_block_error)
            self.user_podium_list.append(user_podium_dict)

    def run(self):
        print()
        print(f"[Task] User {self.user_name} is starting task: {self.name}")
        self.run_steps()


class UserRunner:
    def __init__(self, config_path):
        self.config_path = config_path
        self.users = []
        self.base_url = None
        self.user_podium_list = []
        self.code = uuid.uuid4().hex

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
                store_data = user_entry.get("store_data", "")
                user_copy["store_data"] = self.substitute_placeholders(store_data, profile)
                user_copy.pop("profiles", None)  # Remove original profile string list
                user_copy["tasks"] = [
                    self.substitute_placeholders(task, profile)
                    for task in user_copy["tasks"]
                ]
                all_users.append(user_copy)
        return all_users

    def load_config(self):
        with open(self.config_path, encoding="utf-8") as f:
            # try:
                config = json.load(f)
                self.base_url = config.get("base_url", "")

                


                self.users = self.expand_users(config)

                for user_conf in self.users:
                    user_name = user_conf["name"]
                    globals = user_conf["globals"]

                    store_data = user_conf["store_data"]


                    
                    task_list = []
                    context = {}
                    extract_keys = []
                    set_keys = []

                    

                    for task_conf in user_conf.get("tasks", []):
                        task = Task(self.config_path, task_conf, self.code, user_name, self.base_url, globals, store_data, context, extract_keys, set_keys, self.user_podium_list)
                        task_list.append(task)

                    user_conf["tasks"] = task_list
                    
                
                

            # except Exception as err:
            #     print(err)

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


            print()
            print()
            print("Who is the fastest podium?")
            for podium, user in enumerate(self.user_podium_list):
                elapsed_seconds  = user["end"] - user["start"]

                elapsed_time = timedelta(seconds=elapsed_seconds)

                # Format nicely
                days = elapsed_time.days
                hours, remainder = divmod(elapsed_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                milliseconds = elapsed_time.microseconds // 1000

                print(f"[{user['name']} {user['task']} ({str(podium+1)} place)] Elapsed time: {days}d {hours}h {minutes}m {seconds}s {milliseconds}ms | Number of response: {user['num_of_response']} | Number of success: {user['num_of_success']} | Number of blocked/error {user['num_of_blocked_error']}")

    def run_user_tasks(self, user_name, tasks):
        print()
        print(f"[UserRunner] Starting user {user_name} with {len(tasks)} tasks")
        for task in tasks:
            task.run()
        print()
        print(f"[UserRunner] Finished user {user_name}")
        


if __name__ == "__main__":
    init(autoreset=True)

    figlet = Figlet(font='slant')
    title = figlet.renderText('TASKBLADE')

    print(Fore.LIGHTWHITE_EX + title)

    # print(figlet.renderText('TASKBLADE'))
    
    print(Fore.CYAN + Style.BRIGHT + ">> MULTI-THREADED API TASK RUNNER <<\n")

    footer = (
        Fore.LIGHTBLACK_EX + Style.DIM +
        f"(c) 2025 TASKBLADE {Fore.YELLOW}·{Fore.WHITE} zediek · MIT Licensed · Open Source\n"
    )

    print(footer)



    parser = argparse.ArgumentParser(description="Class-based API Step Runner with Worker Pool")
    parser.add_argument("-c", "--config", required=True, action="store", nargs='+', help="Path to config JSON file/s")
    args = parser.parse_args()

    split_args = str(args.config).replace("[","").replace("]","").replace("'","").split(" ")

    for con in split_args:
        print("[INFO] Config file:",con)
        print("----------------------------------------------")
        runner = UserRunner(con)
        runner.load_config()
        runner.run_all()
        print("----------------------------------------------")
