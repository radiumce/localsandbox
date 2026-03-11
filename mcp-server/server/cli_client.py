#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import argparse
import sys
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".lsb-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_server_url(args_server=None):
    config = load_config()
    if args_server:
        config["server"] = args_server
        save_config(config)
        return args_server.rstrip('/')
    return config.get("server", "http://localhost:8775").rstrip('/')

def make_request(url, method="GET", data=None):
    headers = {'Content-Type': 'application/json'}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            return json.loads(error_body)
        except:
            return {"error": error_body, "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}

def print_success(msg):
    print(f"\033[92m✓ {msg}\033[0m")

def print_error(msg):
    print(f"\033[91m✗ {msg}\033[0m")

def print_info(msg):
    print(f"\033[94mℹ {msg}\033[0m")

def print_table(headers, rows):
    if not rows:
        print("No data.")
        return
    
    col_widths = [max(len(str(h)), max(len(str(row[i])) for row in rows)) for i, h in enumerate(headers)]
    row_format = " | ".join(["{:<" + str(w) + "}" for w in col_widths])
    print(row_format.format(*headers))
    print("-+-".join(["-" * w for w in col_widths]))
    for row in rows:
        print(row_format.format(*[str(c) for c in row]))

def read_input(arg_val):
    if arg_val == "-":
        return sys.stdin.read()
    return arg_val

def cmd_probe(server_url):
    print_info(f"Config File: {CONFIG_FILE.absolute()}")
    print_info(f"Target Server: {server_url}")
    res = make_request(f"{server_url}/health")
    if res.get('status') == 'healthy':
        print_success(f"Server is healthy (Version: {res.get('version', 'unknown')})")
    else:
        print_error(f"Failed to connect to server or server unhealthy: {res.get('error', 'unknown')}")

def handle_execution_result(res):
    if not res.get("success"):
        print_error(f"Execution failed: {res.get('error', 'Unknown Error')}")
    else:
        print_success("Execution finished successfully")

    print("\n--- STDOUT ---")
    stdout = res.get("stdout")
    print(stdout if stdout else "(empty)")
    
    stderr = res.get("stderr")
    if stderr:
        print("\n--- STDERR ---")
        print(f"\033[93m{stderr}\033[0m")
        
    print("\n--- METADATA ---")
    print(f"Session ID: {res.get('session_id')}")
    print(f"Time: {res.get('execution_time_ms')}ms")
    print(f"Exit Code: {res.get('exit_code')}")
    print(f"Template: {res.get('template')}")

def main():
    parser = argparse.ArgumentParser(description="LocalSandbox Independent CLI Client")
    parser.add_argument("--server", help="Server URL (e.g. http://localhost:8775)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # exec-code command
    parser_code = subparsers.add_parser(
        "exec-code", 
        help="Execute code in sandbox",
        description="Execute a code snippet in an isolated sandbox environment.\n\n"
                    "Examples:\n"
                    "  lsb-cli exec-code -c \"print('Hello')\"\n"
                    "  cat script.py | lsb-cli exec-code -c -\n"
                    "  lsb-cli exec-code -c \"console.log('JS')\" -t node",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser_code.add_argument("-c", "--code", required=True, help="Code string or '-' to read from stdin")
    parser_code.add_argument("-t", "--template", default="python", help="Sandbox template (default: python)")
    parser_code.add_argument("-s", "--session", help="Session ID for context reuse")
    parser_code.add_argument("-f", "--flavor", help="Resource flavor (e.g. small, medium)")
    parser_code.add_argument("--timeout", type=int, help="Execution timeout in seconds")
    
    # exec-cmd command
    parser_cmd = subparsers.add_parser(
        "exec-cmd", 
        help="Execute shell command in sandbox",
        description="Execute a shell command in an isolated sandbox environment.\n\n"
                    "Examples:\n"
                    "  lsb-cli exec-cmd -c \"ls -la\"\n"
                    "  lsb-cli exec-cmd -c \"pip install requests && python app.py\" -s <session_id>",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser_cmd.add_argument("-c", "--command", dest="cmd_str", required=True, help="Command string or '-' to read from stdin")
    parser_cmd.add_argument("-t", "--template", default="python", help="Sandbox template (default: python)")
    parser_cmd.add_argument("-s", "--session", help="Session ID for context reuse")
    parser_cmd.add_argument("-f", "--flavor", help="Resource flavor (e.g. small, medium)")
    parser_cmd.add_argument("--timeout", type=int, help="Execution timeout in seconds")

    # sessions command
    parser_sessions = subparsers.add_parser(
        "sessions", 
        help="List active sessions",
        description="List all currently active sandbox sessions.\n\n"
                    "Examples:\n"
                    "  lsb-cli sessions\n"
                    "  lsb-cli sessions -s <session_id>",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser_sessions.add_argument("-s", "--session", help="Filter by specific session ID")
    
    # stop command
    parser_stop = subparsers.add_parser(
        "stop", 
        help="Stop an active session",
        description="Force stop a specific active sandbox session and clean up its resources.\n\n"
                    "Examples:\n"
                    "  lsb-cli stop <session_id>",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser_stop.add_argument("session", help="The Session ID to stop")

    # volumes command
    parser_volumes = subparsers.add_parser(
        "volumes", 
        help="List volume mappings",
        description="List all configured volume mappings between host and container paths.\n\n"
                    "Examples:\n"
                    "  lsb-cli volumes",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # pin command
    parser_pin = subparsers.add_parser(
        "pin", 
        help="Pin a sandbox with a custom name",
        description="Pin an existing sandbox with a custom human-readable name for persistence.\n\n"
                    "Examples:\n"
                    "  lsb-cli pin <session_id> my-project-env",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser_pin.add_argument("session", help="The Session ID to pin")
    parser_pin.add_argument("name", help="Human-readable name for the pinned sandbox")

    # attach command
    parser_attach = subparsers.add_parser(
        "attach", 
        help="Attach to a pinned sandbox by name",
        description="Attach to a previously pinned sandbox using its custom name and retrieve the session ID.\n\n"
                    "Examples:\n"
                    "  lsb-cli attach my-project-env",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser_attach.add_argument("name", help="Name of the pinned sandbox")

    # If no arguments provided, trigger the default probe behavior
    if len(sys.argv) == 1:
        server_url = get_server_url()
        cmd_probe(server_url)
        return

    # To support parsing global args without a subcommand, check if just calling --server
    known_args, unknown_args = parser.parse_known_args()
    if not known_args.command:
        # e.g. `lsb-cli --server http://1.2.3.4`
        if known_args.server:
            server_url = get_server_url(known_args.server)
            cmd_probe(server_url)
            return

    args = parser.parse_args()
    server_url = get_server_url(args.server)
    
    if args.command == "exec-code":
        code = read_input(args.code)
        payload = {
            "code": code,
            "template": args.template,
        }
        if args.session:
            payload["session_id"] = args.session
        if args.flavor:
            payload["flavor"] = args.flavor
        if args.timeout:
            payload["timeout"] = args.timeout
            
        res = make_request(f"{server_url}/api/execute/code", method="POST", data=payload)
        handle_execution_result(res)

    elif args.command == "exec-cmd":
        cmd_str = read_input(args.cmd_str)
        payload = {
            "command": cmd_str,
            "template": args.template,
        }
        if args.session:
            payload["session_id"] = args.session
        if args.flavor:
            payload["flavor"] = args.flavor
        if args.timeout:
            payload["timeout"] = args.timeout
            
        res = make_request(f"{server_url}/api/execute/command", method="POST", data=payload)
        handle_execution_result(res)

    elif args.command == "sessions":
        url = f"{server_url}/api/sessions"
        if args.session:
            url += f"?session_id={args.session}"
        res = make_request(url, method="GET")
        if not res.get("success"):
            print_error(f"Failed to fetch sessions: {res.get('error')}")
            return
            
        sessions = res.get("sessions", [])
        if not sessions:
            print_info("No active sessions found.")
            return
            
        headers = ["Session ID", "Template", "Status", "Namespace", "Name", "Created"]
        rows = []
        for s in sessions:
            rows.append([s['session_id'], s['template'], s['status'], s['namespace'], s['sandbox_name'], s['created_at']])
        print_table(headers, rows)

    elif args.command == "stop":
        res = make_request(f"{server_url}/api/sessions/{args.session}/stop", method="POST")
        if res.get("success") and res.get("stopped"):
            print_success(f"Session {args.session} stopped successfully.")
        else:
            print_error(f"Failed to stop session: {res.get('error', 'Not found or already stopped.')}")

    elif args.command == "volumes":
        res = make_request(f"{server_url}/api/volumes", method="GET")
        if not res.get("success"):
            print_error(f"Failed to fetch volumes: {res.get('error')}")
            return
            
        volumes = res.get("volumes", [])
        if not volumes:
            print_info("No volume mappings configured.")
            return
            
        headers = ["Host Path", "Sandbox Path"]
        rows = [[v['host_path'], v['sandbox_path']] for v in volumes]
        print_table(headers, rows)

    elif args.command == "pin":
        payload = {"session_id": args.session, "pinned_name": args.name}
        res = make_request(f"{server_url}/api/sandbox/pin", method="POST", data=payload)
        if res.get("success"):
            print_success(res.get("result", "Successfully pinned sandbox."))
        else:
            print_error(f"Failed to pin sandbox: {res.get('error')}")

    elif args.command == "attach":
        payload = {"pinned_name": args.name}
        res = make_request(f"{server_url}/api/sandbox/attach", method="POST", data=payload)
        if res.get("success"):
            print_success(f"Attached successfully. Session ID: {res.get('session_id')}")
        else:
            print_error(f"Failed to attach: {res.get('error')}")

if __name__ == "__main__":
    main()
