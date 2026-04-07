package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

var (
	globalServerURL string
)

func getConfigDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ".lsb-cli"
	}
	return filepath.Join(home, ".lsb-cli")
}

func getConfigFile() string {
	return filepath.Join(getConfigDir(), "config.json")
}

func loadConfig() map[string]interface{} {
	cfgFile := getConfigFile()
	data, err := os.ReadFile(cfgFile)
	if err != nil {
		return make(map[string]interface{})
	}
	var config map[string]interface{}
	if err := json.Unmarshal(data, &config); err != nil {
		return make(map[string]interface{})
	}
	return config
}

func saveConfig(config map[string]interface{}) {
	cfgDir := getConfigDir()
	os.MkdirAll(cfgDir, 0755)
	data, err := json.MarshalIndent(config, "", "    ")
	if err == nil {
		os.WriteFile(getConfigFile(), data, 0644)
	}
}

func getServerURL() string {
	config := loadConfig()
	if globalServerURL != "" {
		config["server"] = globalServerURL
		saveConfig(config)
		return strings.TrimRight(globalServerURL, "/")
	}
	if v, ok := config["server"].(string); ok && v != "" {
		return strings.TrimRight(v, "/")
	}
	return "http://localhost:8775"
}

func printSuccess(msg string) {
	fmt.Printf("\033[92m✓ %s\033[0m\n", msg)
}

func printError(msg string) {
	fmt.Printf("\033[91m✗ %s\033[0m\n", msg)
}

func printInfo(msg string) {
	fmt.Printf("\033[94mℹ %s\033[0m\n", msg)
}

func makeRequest(url, method string, reqData interface{}) map[string]interface{} {
	var bodyReader io.Reader
	if reqData != nil {
		b, _ := json.Marshal(reqData)
		bodyReader = bytes.NewReader(b)
	}
	
	req, err := http.NewRequest(method, url, bodyReader)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	if reqData != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	defer resp.Body.Close()

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}

	var result map[string]interface{}
	if err := json.Unmarshal(bodyBytes, &result); err != nil {
		return map[string]interface{}{"success": false, "error": string(bodyBytes)}
	}
	return result
}

func cmdProbe(serverURL string) {
	printInfo(fmt.Sprintf("Config File: %s", getConfigFile()))
	printInfo(fmt.Sprintf("Target Server: %s", serverURL))
	
	res := makeRequest(serverURL+"/health", "GET", nil)
	if status, ok := res["status"].(string); ok && status == "healthy" {
		version, _ := res["version"].(string)
		if version == "" {
			version = "unknown"
		}
		printSuccess(fmt.Sprintf("Server is healthy (Version: %s)", version))
	} else {
		errMsg, _ := res["error"].(string)
		if errMsg == "" {
			errMsg = "unknown"
		}
		printError(fmt.Sprintf("Failed to connect to server or server unhealthy: %s", errMsg))
	}
}

func handleExecutionResult(res map[string]interface{}) {
	success, ok := res["success"].(bool)
	if !ok || !success {
		errMsg, _ := res["error"].(string)
		if errMsg == "" {
			errMsg = "Unknown Error"
		}
		printError(fmt.Sprintf("Execution failed: %s", errMsg))
	} else {
		printSuccess("Execution finished successfully")
	}

	fmt.Println("\n--- STDOUT ---")
	stdout, _ := res["stdout"].(string)
	if stdout == "" {
		fmt.Println("(empty)")
	} else {
		fmt.Println(stdout)
	}

	stderr, _ := res["stderr"].(string)
	if stderr != "" {
		fmt.Println("\n--- STDERR ---")
		fmt.Printf("\033[93m%s\033[0m\n", stderr)
	}

	fmt.Println("\n--- METADATA ---")
	sessionID, _ := res["session_id"].(string)
	fmt.Printf("Session ID: %s\n", sessionID)
	
	switch t := res["execution_time_ms"].(type) {
	case float64:
		fmt.Printf("Time: %vms\n", t)
	default:
		fmt.Printf("Time: <null>ms\n")
	}

	switch c := res["exit_code"].(type) {
	case float64:
		fmt.Printf("Exit Code: %v\n", c)
	default:
		fmt.Printf("Exit Code: <null>\n")
	}

	template, _ := res["template"].(string)
	fmt.Printf("Template: %s\n", template)
}

func readInput(argVal string) string {
	if argVal == "-" {
		b, err := io.ReadAll(os.Stdin)
		if err != nil {
			return ""
		}
		return string(b)
	}
	return argVal
}

func printTable(headers []string, rows [][]string) {
	if len(rows) == 0 {
		fmt.Println("No data.")
		return
	}

	colWidths := make([]int, len(headers))
	for i, h := range headers {
		colWidths[i] = len(h)
	}
	for _, row := range rows {
		for i, c := range row {
			if len(c) > colWidths[i] {
				colWidths[i] = len(c)
			}
		}
	}

	var rowFormat string
	for _, w := range colWidths {
		rowFormat += fmt.Sprintf("%%-%ds | ", w)
	}
	rowFormat = strings.TrimSuffix(rowFormat, " | ") + "\n"

	headerArgs := make([]interface{}, len(headers))
	for i, h := range headers {
		headerArgs[i] = h
	}
	fmt.Printf(rowFormat, headerArgs...)

	var separators []string
	for _, w := range colWidths {
		separators = append(separators, strings.Repeat("-", w))
	}
	fmt.Println(strings.Join(separators, "-+-"))

	for _, row := range rows {
		rowArgs := make([]interface{}, len(row))
		for i, c := range row {
			rowArgs[i] = c
		}
		fmt.Printf(rowFormat, rowArgs...)
	}
}

func main() {
	flag.StringVar(&globalServerURL, "server", "", "Server URL (e.g. http://localhost:8775)")
	flag.Usage = printUsage
	flag.Parse()

	if len(flag.Args()) == 0 {
		serverURL := getServerURL()
		cmdProbe(serverURL)
		return
	}

	cmd := flag.Arg(0)
	args := flag.Args()[1:]
	serverURL := getServerURL()

	switch cmd {
	case "exec-code":
		fs := flag.NewFlagSet("exec-code", flag.ExitOnError)
		codeParam := fs.String("c", "", "Code string or '-' to read from stdin")
		codeLong := fs.String("code", "", "Code string or '-' to read from stdin")
		templateParam := fs.String("t", "python", "Sandbox template (default: python)")
		templateLong := fs.String("template", "python", "Sandbox template (default: python)")
		sessionParam := fs.String("s", "", "Session ID for context reuse")
		sessionLong := fs.String("session", "", "Session ID for context reuse")
		flavorParam := fs.String("f", "", "Resource flavor (e.g. small, medium)")
		flavorLong := fs.String("flavor", "", "Resource flavor (e.g. small, medium)")
		timeoutParam := fs.Int("timeout", 0, "Execution timeout in seconds")
		fs.Parse(args)

		code := *codeParam
		if *codeLong != "" {
			code = *codeLong
		}
		template := *templateParam
		if *templateLong != "python" {
			template = *templateLong
		}
		session := *sessionParam
		if *sessionLong != "" {
			session = *sessionLong
		}
		flavor := *flavorParam
		if *flavorLong != "" {
			flavor = *flavorLong
		}

		if code == "" {
			fmt.Println("Error: --code/-c is required")
			os.Exit(1)
		}

		payload := map[string]interface{}{
			"code":     readInput(code),
			"template": template,
		}
		if session != "" {
			payload["session_id"] = session
		}
		if flavor != "" {
			payload["flavor"] = flavor
		}
		if *timeoutParam > 0 {
			payload["timeout"] = *timeoutParam
		}

		res := makeRequest(serverURL+"/api/execute/code", "POST", payload)
		handleExecutionResult(res)

	case "exec-cmd":
		fs := flag.NewFlagSet("exec-cmd", flag.ExitOnError)
		cmdParam := fs.String("c", "", "Command string or '-' to read from stdin")
		cmdLong := fs.String("command", "", "Command string or '-' to read from stdin")
		templateParam := fs.String("t", "python", "Sandbox template (default: python)")
		templateLong := fs.String("template", "python", "Sandbox template (default: python)")
		sessionParam := fs.String("s", "", "Session ID for context reuse")
		sessionLong := fs.String("session", "", "Session ID for context reuse")
		flavorParam := fs.String("f", "", "Resource flavor (e.g. small, medium)")
		flavorLong := fs.String("flavor", "", "Resource flavor (e.g. small, medium)")
		timeoutParam := fs.Int("timeout", 0, "Execution timeout in seconds")
		fs.Parse(args)

		cmdStr := *cmdParam
		if *cmdLong != "" {
			cmdStr = *cmdLong
		}
		template := *templateParam
		if *templateLong != "python" {
			template = *templateLong
		}
		session := *sessionParam
		if *sessionLong != "" {
			session = *sessionLong
		}
		flavor := *flavorParam
		if *flavorLong != "" {
			flavor = *flavorLong
		}

		if cmdStr == "" {
			fmt.Println("Error: --command/-c is required")
			os.Exit(1)
		}

		payload := map[string]interface{}{
			"command":  readInput(cmdStr),
			"template": template,
		}
		if session != "" {
			payload["session_id"] = session
		}
		if flavor != "" {
			payload["flavor"] = flavor
		}
		if *timeoutParam > 0 {
			payload["timeout"] = *timeoutParam
		}

		res := makeRequest(serverURL+"/api/execute/command", "POST", payload)
		handleExecutionResult(res)

	case "sessions":
		fs := flag.NewFlagSet("sessions", flag.ExitOnError)
		sessionParam := fs.String("s", "", "Filter by specific session ID")
		sessionLong := fs.String("session", "", "Filter by specific session ID")
		fs.Parse(args)

		session := *sessionParam
		if *sessionLong != "" {
			session = *sessionLong
		}

		url := serverURL + "/api/sessions"
		if session != "" {
			url += "?session_id=" + session
		}

		res := makeRequest(url, "GET", nil)
		if success, ok := res["success"].(bool); !ok || !success {
			errMsg, _ := res["error"].(string)
			printError(fmt.Sprintf("Failed to fetch sessions: %s", errMsg))
			return
		}

		sessionsList, ok := res["sessions"].([]interface{})
		if !ok || len(sessionsList) == 0 {
			printInfo("No active sessions found.")
			return
		}

		headers := []string{"Session ID", "Template", "Status", "Namespace", "Name", "Created"}
		var rows [][]string
		for _, sRaw := range sessionsList {
			s, _ := sRaw.(map[string]interface{})
			getStr := func(k string) string {
				val, _ := s[k].(string)
				return val
			}
			rows = append(rows, []string{
				getStr("session_id"),
				getStr("template"),
				getStr("status"),
				getStr("namespace"),
				getStr("sandbox_name"),
				getStr("created_at"),
			})
		}
		printTable(headers, rows)

	case "stop":
		if len(args) < 1 {
			fmt.Println("Error: session ID is required")
			os.Exit(1)
		}
		sessionID := args[0]
		res := makeRequest(serverURL+"/api/sessions/"+sessionID+"/stop", "POST", nil)
		success, _ := res["success"].(bool)
		stopped, _ := res["stopped"].(bool)
		if success && stopped {
			printSuccess(fmt.Sprintf("Session %s stopped successfully.", sessionID))
		} else {
			errMsg, _ := res["error"].(string)
			if errMsg == "" {
				errMsg = "Not found or already stopped."
			}
			printError(fmt.Sprintf("Failed to stop session: %s", errMsg))
		}

	case "volumes":
		res := makeRequest(serverURL+"/api/volumes", "GET", nil)
		if success, ok := res["success"].(bool); !ok || !success {
			errMsg, _ := res["error"].(string)
			printError(fmt.Sprintf("Failed to fetch volumes: %s", errMsg))
			return
		}

		volumesList, ok := res["volumes"].([]interface{})
		if !ok || len(volumesList) == 0 {
			printInfo("No volume mappings configured.")
			return
		}

		headers := []string{"Host Path", "Sandbox Path"}
		var rows [][]string
		for _, vRaw := range volumesList {
			v, _ := vRaw.(map[string]interface{})
			hostPath, _ := v["host_path"].(string)
			sandboxPath, _ := v["sandbox_path"].(string)
			rows = append(rows, []string{hostPath, sandboxPath})
		}
		printTable(headers, rows)

	case "pin":
		if len(args) < 2 {
			fmt.Println("Error: session ID and name are required")
			os.Exit(1)
		}
		payload := map[string]interface{}{
			"session_id":  args[0],
			"pinned_name": args[1],
		}
		res := makeRequest(serverURL+"/api/sandbox/pin", "POST", payload)
		if success, ok := res["success"].(bool); ok && success {
			resultMsg, _ := res["result"].(string)
			if resultMsg == "" {
				resultMsg = "Successfully pinned sandbox."
			}
			printSuccess(resultMsg)
		} else {
			errMsg, _ := res["error"].(string)
			printError(fmt.Sprintf("Failed to pin sandbox: %s", errMsg))
		}

	case "attach":
		if len(args) < 1 {
			fmt.Println("Error: pinned name is required")
			os.Exit(1)
		}
		payload := map[string]interface{}{
			"pinned_name": args[0],
		}
		res := makeRequest(serverURL+"/api/sandbox/attach", "POST", payload)
		if success, ok := res["success"].(bool); ok && success {
			sessionID, _ := res["session_id"].(string)
			printSuccess(fmt.Sprintf("Attached successfully. Session ID: %s", sessionID))
		} else {
			errMsg, _ := res["error"].(string)
			printError(fmt.Sprintf("Failed to attach: %s", errMsg))
		}

	default:
		fmt.Printf("Unknown command: %s\n", cmd)
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("LocalSandbox Independent CLI Client")
	fmt.Println("\nUsage: lsb-cli [global options] <command> [command options]")
	fmt.Println("\nGlobal Options:")
	flag.PrintDefaults()
	fmt.Println("\nAvailable commands:")
	fmt.Println("  exec-code      Execute code in sandbox")
	fmt.Println("  exec-cmd       Execute shell command in sandbox")
	fmt.Println("  sessions       List active sessions")
	fmt.Println("  stop           Stop an active session")
	fmt.Println("  volumes        List volume mappings")
	fmt.Println("  pin            Pin a sandbox with a custom name")
	fmt.Println("  attach         Attach to a pinned sandbox by name")
	fmt.Println("\nRun 'lsb-cli <command> -h' for command-specific help.")
}
