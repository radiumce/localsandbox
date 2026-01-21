---
name: "sandbox-usage"
description: "How to use the sandbox environment: managing session lifecycle, executing command lines, managing file mappings, and handling permissions."
version: "1.0.0"
---

# Core Definition
A sandbox is an allocated remote server environment used for running programs and installing software. You can only get feedback through **command-line tool calls** and **file reading**; GUI access is not available.

# Tool Combination
- **sandbox tools**: Used to manage the sandbox environment, including session lifecycle, command line execution, and file mapping management.
- **plan tools**: When the task to be executed is complex, the Plan tool should be used to formulate a plan and track task execution.

# Part 1: Session Management
To ensure context consistency, the following session rules must be strictly adhered to:

1.  **Session Consistency**
    - During the completion of the same Work and related tasks, one must lock onto using the same `sessionid`.
    - Frequent switching of Sessions without cause is prohibited to maintain the continuity of environment variables and temporary files.

2.  **Timeout Handling**
    - Sandbox Sessions may time out.
    - **Action**: If a session invalidation or timeout error is encountered, immediately generate a new `sessionid` to initialize a new sandbox and reconfigure necessary environment dependencies.

# Part 2: Execution Standards

1.  **Pre-flight Check**
    - Before starting complex tasks, confirm the current user identity (User Identity).
    - Some sandboxes default to non-root users. If you need to install software or modify system configuration, determine if the `sudo` prefix is needed.

2.  **Output Hygiene**
    - **On Success**: When executing commands, strictly control the length of `stdout` output. It is recommended to output only the last 20 lines (e.g., using `tail -n 20`) to avoid consuming excessive Context Window.
    - **On Failure**: If command execution fails, the full error output (stderr) must be obtained and analyzed for debugging.

3.  **Implicit Execution**
    - **Action**: When performing programming tasks, directly call tools to run code.
    - **Constraint**: Do **NOT** display the specific program code you wrote to the user unless the user explicitly requests to see the source code.

# Part 3: File System & Mapping

Sandbox internal files are isolated from the Host file system and must interact through mapping relationships. Before executing any task involving file reading or writing, you should first confirm the file system mapping relationship and understand the mapping between the current or target working directory and the corresponding directory in the sandbox:

1.  **Get Mapping Relationships**
    - Call the `get_volume_mappings` tool to get the correspondence between "Sandbox Path" and "Host Path".
    - **Example**:
      `Host: /Users/Me/project -> Container: /shared`

2.  **File Interaction Flow**
    - If you need to read a file generated in the sandbox (such as a generated image or compiled binary):
      1. Generate the file in the sandbox's mapped directory (e.g., `/shared/output.png`).
      2. Deduce the host path based on the mapping relationship (e.g., `/Users/Me/project/output.png`).
      3. Use the host's `filesystem` tool to read the file.

# Troubleshooting
- **Input Quality Check**: If the program reports an error, prioritize checking input parameters and environment dependencies.
- **Output Correction**: If the execution result is not as expected, consider whether to adjust command line parameters or the usage of open source libraries, and verify in the sandbox.
