# Implementation Plan

- [x] 1. Set up project structure and core data models
  - Create e2e_integration_test.py file with basic structure and imports
  - Define TestResult, TestConfiguration, and EnvironmentConfig dataclasses
  - Import required MCP SDK components and other dependencies
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Implement environment configuration management
  - [x] 2.1 Create environment configuration loader
    - Write load_env_config() function to parse .env.example file
    - Implement validation for required environment variables
    - Add error handling for missing or invalid configuration
    - _Requirements: 1.1, 9.2_

  - [x] 2.2 Create configuration validation utilities
    - Write validate_dependencies() function to check MCP client availability
    - Implement Docker/container runtime validation
    - Add shared volume path validation
    - _Requirements: 1.1, 3.1_

- [x] 3. Implement MCP server and client management
  - [x] 3.1 Create MCPServerManager class
    - Implement server startup with environment configuration
    - Add server health checking functionality
    - Implement graceful server shutdown
    - _Requirements: 1.1, 1.2_

  - [x] 3.2 Create MCPClientManager class
    - Implement MCP client connection using official SDK
    - Add client session management and cleanup
    - Implement tool calling wrapper with error handling
    - _Requirements: 1.2, 1.4_

- [x] 4. Implement core test execution framework
  - [x] 4.1 Create TestSequenceExecutor class
    - Implement base test step execution pattern
    - Add session ID tracking and state management
    - Create result validation utilities
    - _Requirements: 1.3, 1.4_

  - [x] 4.2 Create TestReporter class
    - Implement step result recording functionality
    - Add test report generation with detailed output
    - Create summary printing with success/failure indicators
    - _Requirements: 1.3, 9.3_

- [x] 5. Implement individual test steps (Steps 1-3)
  - [x] 5.1 Implement Python hello world execution test
    - Write execute_python_hello_world() method
    - Add output validation for "Hello, World!" message
    - Implement session ID extraction from result
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 5.2 Implement shared volume access verification test
    - Write verify_shared_volume_access() method using execute_command tool
    - Add validation for /shared directory contents
    - Verify data.txt file accessibility from host volume mapping
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 5.3 Implement file creation and persistence test
    - Write create_hello_txt_file() method
    - Create /hello.txt file with "hello sandbox" content
    - Add file existence and content validation
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 6. Implement sandbox pinning and session management (Steps 4-6)
  - [x] 6.1 Implement sandbox pinning functionality
    - Write pin_sandbox() method using pin_sandbox tool
    - Add pinning success validation
    - Implement pinned sandbox name generation
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 6.2 Implement pinned sandbox file verification
    - Write verify_pinned_sandbox_files() method
    - Validate that files persist immediately after pinning
    - Add comprehensive file content verification
    - _Requirements: 5.2, 8.1_

  - [x] 6.3 Implement session termination
    - Write stop_session() method using stop_session tool
    - Add session cleanup validation
    - Verify session is no longer active
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 7. Implement sandbox reattachment and state validation (Steps 7-9)
  - [x] 7.1 Implement sandbox reattachment by name
    - Write attach_to_pinned_sandbox() method using attach_sandbox_by_name tool
    - Add new session ID extraction and validation
    - Implement attachment success verification
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 7.2 Implement restored file content verification
    - Write verify_restored_files() method
    - Validate /hello.txt content matches original "hello sandbox"
    - Add comprehensive state persistence validation
    - _Requirements: 7.3, 8.1, 8.3_

  - [x] 7.3 Implement restored shared volume verification
    - Write verify_shared_volume_in_restored() method
    - Execute "ls /shared" command in restored sandbox
    - Validate volume mapping persistence across pin-attach cycle
    - _Requirements: 8.2, 8.3_

- [x] 8. Implement main test runner and error handling
  - [x] 8.1 Create main E2EIntegrationTest class
    - Implement test initialization and setup
    - Add comprehensive error handling for all test phases
    - Create cleanup mechanisms for failed tests
    - _Requirements: 1.4, 6.4, 7.4_

  - [x] 8.2 Implement test execution orchestration
    - Write run_complete_test() method that executes all 9 steps
    - Add step-by-step progress reporting
    - Implement failure recovery and continuation logic
    - _Requirements: 1.3, 8.4_

  - [x] 8.3 Add comprehensive error handling and logging
    - Implement custom exception classes for different error types
    - Add detailed error logging with context information
    - Create error recovery mechanisms where possible
    - _Requirements: 1.4, 2.4, 3.4, 4.4, 5.4, 6.4, 7.4, 8.4_

- [-] 9. Create executable script and documentation
  - [x] 9.1 Implement command-line interface
    - Add argument parsing for test configuration options
    - Implement main() function with proper error handling
    - Add verbose output options and quiet mode
    - _Requirements: 9.2, 9.3_

  - [x] 9.2 Create comprehensive E2ETEST.md documentation
    - Write setup and configuration instructions
    - Add step-by-step execution guide with examples
    - Include troubleshooting section for common issues
    - Document environment variable requirements
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ] 9.3 Add test validation and final integration
    - Write unit tests for individual components
    - Add integration test for complete test sequence
    - Implement test result validation and reporting
    - Create example test runs and expected outputs
    - _Requirements: 1.3, 8.3, 9.4_