from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

"""

E2E Tests for Windows Subprocess Execution

Tests Windows-specific subprocess handling for frontend and service management.



Business Value Justification (BVJ):

- Segment: Platform/Internal (Windows developers and deployments)

- Business Goal: Development velocity and Windows compatibility

- Value Impact: Ensures development environment works on Windows

- Strategic Impact: Windows compatibility for development team

"""



import pytest

import subprocess

import sys

import os

import asyncio

import time

from pathlib import Path





@pytest.mark.e2e

@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")

class TestWindowsSubprocessExecution:

    """Test suite for Windows-specific subprocess execution issues."""



    def test_npm_commands_work_on_windows(self):

        """

        Test that npm commands work correctly on Windows.

        

        Critical Assertions:

        - npm --version works

        - node --version works

        - npm commands use correct shell

        

        Expected Failure: Shell execution issues, npm not found

        Business Impact: Frontend development blocked on Windows

        """

        # Test npm is available

        try:

            result = subprocess.run(

                ["npm", "--version"],

                capture_output=True,

                text=True,

                timeout=10,

                shell=True

            )

            assert result.returncode == 0, f"npm not available: {result.stderr}"

            assert result.stdout.strip(), "npm version empty"

        except subprocess.TimeoutExpired:

            pytest.fail("npm --version timed out")

        except FileNotFoundError:

            pytest.fail("npm command not found - ensure Node.js is installed")



        # Test node is available

        try:

            result = subprocess.run(

                ["node", "--version"],

                capture_output=True,

                text=True,

                timeout=10,

                shell=True

            )

            assert result.returncode == 0, f"node not available: {result.stderr}"

            assert result.stdout.strip().startswith("v"), "Invalid node version format"

        except subprocess.TimeoutExpired:

            pytest.fail("node --version timed out")

        except FileNotFoundError:

            pytest.fail("node command not found - ensure Node.js is installed")



    def test_python_subprocess_shell_execution(self):

        """

        Test Python subprocess shell execution on Windows.

        

        Critical Assertions:

        - shell=True works correctly

        - Process creation doesn't hang

        - stdout/stderr capture works

        

        Expected Failure: Shell execution hanging, pipe issues

        Business Impact: Dev launcher and scripts fail on Windows

        """

        # Test basic shell command

        result = subprocess.run(

            ["echo", "test"],

            capture_output=True,

            text=True,

            timeout=5,

            shell=True

        )

        assert result.returncode == 0, f"Echo command failed: {result.stderr}"

        assert "test" in result.stdout, "Echo output incorrect"



        # Test Python command execution

        result = subprocess.run(

            [sys.executable, "-c", "print('subprocess_test')"],

            capture_output=True,

            text=True,

            timeout=10,

            shell=True

        )

        assert result.returncode == 0, f"Python subprocess failed: {result.stderr}"

        assert "subprocess_test" in result.stdout, "Python subprocess output incorrect"



    def test_long_running_process_management(self):

        """

        Test management of long-running processes on Windows.

        

        Critical Assertions:

        - Processes can be started in background

        - Processes can be terminated cleanly

        - No zombie processes left

        

        Expected Failure: Process cleanup issues, termination problems

        Business Impact: Dev server processes accumulate, system instability

        """

        # Start a long-running process

        process = subprocess.Popen(

            [sys.executable, "-c", "import time; [time.sleep(0.1) for _ in range(100)]"],

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            shell=True

        )

        

        # Verify process started

        assert process.poll() is None, "Process terminated immediately"

        

        # Let it run briefly

        time.sleep(0.2)

        

        # Terminate process

        process.terminate()

        

        # Wait for termination with timeout

        try:

            process.wait(timeout=5)

        except subprocess.TimeoutExpired:

            # Force kill if termination failed

            process.kill()

            process.wait(timeout=2)

        

        # Verify process is dead

        assert process.poll() is not None, "Process did not terminate"



    def test_frontend_process_simulation(self):

        """

        Test simulation of frontend process startup on Windows.

        

        This test SHOULD FAIL until Windows subprocess handling is properly implemented.

        Exposes coverage gap in Windows-specific process management.

        

        Critical Assertions:

        - Can simulate npm start process

        - Process streams don't block

        - Cleanup works properly

        

        Expected Failure: Process hanging, stream blocking

        Business Impact: Frontend development broken on Windows

        """

        # Simulate npm start command (without actually running it)

        # Use a Python script that behaves like npm start

        script_content = '''

import sys

import time

import random



print("Starting development server...")

print("Compiled successfully!")

print("Local: http://localhost:3000")



# Simulate ongoing output like webpack dev server

for i in range(5):

    time.sleep(0.1)

    if random.choice([True, False]):

        print(f"[HMR] Checking for updates... {i}")

    sys.stdout.flush()



print("Server ready")

'''

        

        # Create temporary script

        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:

            f.write(script_content)

            script_path = f.name

        

        try:

            # Start the simulated frontend process

            process = subprocess.Popen(

                [sys.executable, script_path],

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE,

                text=True,

                shell=True,

                bufsize=1,  # Line buffered

                universal_newlines=True

            )

            

            # Read output with timeout to prevent hanging

            output_lines = []

            start_time = time.time()

            

            while time.time() - start_time < 5:  # 5 second timeout

                if process.poll() is not None:

                    # Process finished

                    break

                    

                # Try to read a line with timeout

                import select

                if sys.platform == "win32":

                    # Windows doesn't have select for pipes

                    # Use polling approach

                    time.sleep(0.05)

                    try:

                        line = process.stdout.readline()

                        if line:

                            output_lines.append(line.strip())

                    except:

                        break

                else:

                    # Unix-like systems

                    ready, _, _ = select.select([process.stdout], [], [], 0.1)

                    if ready:

                        line = process.stdout.readline()

                        if line:

                            output_lines.append(line.strip())

            

            # Terminate process

            process.terminate()

            try:

                process.wait(timeout=2)

            except subprocess.TimeoutExpired:

                process.kill()

                process.wait(timeout=1)

            

            # Verify we got expected output

            assert len(output_lines) > 0, "No output captured from simulated frontend process"

            assert any("Starting development server" in line for line in output_lines), \

                f"Expected startup message not found in output: {output_lines}"

            

            # This assertion SHOULD FAIL until proper Windows handling is implemented

            assert any("Server ready" in line for line in output_lines), \

                "Process did not complete properly - Windows subprocess handling issue"

                

        finally:

            # Cleanup temp file

            try:

                os.unlink(script_path)

            except:

                pass



    def test_concurrent_process_management(self):

        """

        Test managing multiple concurrent processes on Windows.

        

        Critical Assertions:

        - Multiple processes can run concurrently

        - Each process is independently manageable

        - Resource cleanup works for all processes

        

        Expected Failure: Resource conflicts, cleanup issues

        Business Impact: Cannot run multiple services simultaneously

        """

        processes = []

        

        try:

            # Start multiple short-lived processes

            for i in range(3):

                process = subprocess.Popen(

                    [sys.executable, "-c", f"import time; time.sleep(0.5); print('Process {i} done')"],

                    stdout=subprocess.PIPE,

                    stderr=subprocess.PIPE,

                    text=True,

                    shell=True

                )

                processes.append(process)

            

            # Verify all started

            assert len(processes) == 3, "Not all processes started"

            

            # Wait for all to complete

            for process in processes:

                try:

                    stdout, stderr = process.communicate(timeout=3)

                    assert process.returncode == 0, f"Process failed: {stderr}"

                    assert "done" in stdout, f"Process output incorrect: {stdout}"

                except subprocess.TimeoutExpired:

                    process.kill()

                    pytest.fail("Process timed out")

                    

        finally:

            # Cleanup any remaining processes

            for process in processes:

                if process.poll() is None:

                    process.terminate()

                    try:

                        process.wait(timeout=1)

                    except subprocess.TimeoutExpired:

                        process.kill()



    def test_environment_variable_passing(self):

        """

        Test environment variable passing to subprocesses on Windows.

        

        Critical Assertions:

        - Environment variables are passed correctly

        - PATH modifications work

        - Custom variables are available

        

        Expected Failure: Environment not inherited, PATH issues

        Business Impact: Services can't find dependencies, configuration issues

        """

        # Test custom environment variable

        import os

        custom_env = os.environ.copy()

        custom_env["WINDOWS_TEST_VAR"] = "windows_test_value"

        

        result = subprocess.run(

            ['echo', '%WINDOWS_TEST_VAR%'],

            capture_output=True,

            text=True,

            timeout=5,

            shell=True,

            env=custom_env

        )

        

        assert result.returncode == 0, f"Environment test failed: {result.stderr}"

        assert "windows_test_value" in result.stdout, \

            f"Custom environment variable not passed: {result.stdout}"

        

        # Test PATH variable preservation

        result = subprocess.run(

            capture_output=True,

            text=True,

            timeout=5,

            shell=True,

            env=custom_env

        )

        

        assert result.returncode == 0, f"PATH test failed: {result.stderr}"

        path_count = int(result.stdout.strip())

        assert path_count > 5, f"PATH not properly inherited: {path_count} entries"

