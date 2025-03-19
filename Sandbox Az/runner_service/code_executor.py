"""
Module for executing code snippets in a sandboxed environment
"""
import os
import subprocess
import time
import logging
import uuid
import signal
import json
from pathlib import Path
import shutil
import threading
import resource
import psutil

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))
MAX_TIMEOUT = int(os.getenv("MAX_TIMEOUT", "120"))

# Extension mapping
LANGUAGE_EXTENSIONS = {
    'python': '.py',
    'javascript': '.js', 
    'js': '.js',
    'java': '.java',
    'go': '.go',
    'typescript': '.ts',
    'ts': '.ts'
}

# Command templates for different langs
LANGUAGE_COMMANDS = {
    'python': lambda filename: ["python3", filename],
    'javascript': lambda filename: ["node", filename],
    'js': lambda filename: ["node", filename],
    'java': lambda filename: ["java", Path(filename).stem],
    'go': lambda filename: ["go", "run", filename],
    'typescript': lambda filename: ["sh", "-c", f"tsc {filename} && node {Path(filename).with_suffix('.js')}"],
    'ts': lambda filename: ["sh", "-c", f"tsc {filename} && node {Path(filename).with_suffix('.js')}"]
}

# File names for different languages (when specific ones are needed)
LANGUAGE_FILENAMES = {
    'java': 'Solution.java',
    'python': 'snippet.py',
    'javascript': 'snippet.js',
    'js': 'snippet.js',
    'typescript': 'snippet.ts',
    'ts': 'snippet.ts',
    'go': 'snippet.go',
}

class CodeExecutionError(Exception):
    """Exception raised for errors during code execution"""
    pass

def monitor_process(process, exec_id, interval=0.5):
    """
    Monitor a running process and log resource usage
    
    Args:
        process: subprocess.Popen object
        exec_id: Execution ID for logging
        interval: Monitoring interval in seconds
    """
    try:
        # Convert subprocess PID to psutil Process
        p = psutil.Process(process.pid)
        
        # Monitor while process is running
        while process.poll() is None:
            try:
                # Get + log CPU and memory stats
                cpu_percent = p.cpu_percent(interval=0.1)
                memory_info = p.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                
                logger.debug(
                    f"Process stats [exec_id={exec_id}]: "
                    f"CPU={cpu_percent:.1f}%, Memory={memory_mb:.1f}MB"
                )
                
                # Get child processes if needed
                children = p.children(recursive=True)
                if children:
                    child_info = []
                    for child in children:
                        try:
                            child_cpu = child.cpu_percent(interval=0.1)
                            child_mem = child.memory_info().rss / (1024 * 1024)
                            child_info.append({
                                "pid": child.pid,
                                "cpu": f"{child_cpu:.1f}%",
                                "memory_mb": f"{child_mem:.1f}"
                            })
                        except:
                            pass
                    
                    if child_info:
                        logger.debug(f"Child processes [exec_id={exec_id}]: {json.dumps(child_info)}")
                
                # Wait before recheck
                time.sleep(interval)
            except psutil.NoSuchProcess:
                # Process ended
                break
            except Exception as e:
                logger.warning(f"Monitoring error [exec_id={exec_id}]: {str(e)}")
                time.sleep(interval)
    except Exception as e:
        logger.warning(f"Process monitor failed to start [exec_id={exec_id}]: {str(e)}")

def execute_code(language: str, code_snippet: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Execute code in a sandboxed environment
    
    Args:
        language (str): Programming language ('python', 'java', etc.)
        code_snippet (str): Code to execute
        timeout (int): Maximum execution time in seconds
        
    Returns:
        str: Execution output
    """
    # Create execution tracking ID
    execution_id = str(uuid.uuid4())
    logger.info(f"Starting execution [exec_id={execution_id}, language={language}]")
    
    phases = {
        "setup": {
            "start": time.time(),
            "end": None
        },
        "compilation": {
            "start": None,
            "end": None,
            "needed": language in ['java', 'typescript', 'ts']
        },
        "execution": {
            "start": None,
            "end": None
        },
        "cleanup": {
            "start": None,
            "end": None
        }
    }
    
    # Log system resources at start
    system_resources = {
        "cpu_count": os.cpu_count(),
        "memory_total_mb": psutil.virtual_memory().total / (1024 * 1024),
        "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
        "cpu_percent": psutil.cpu_percent()
    }
    logger.info(f"System resources [exec_id={execution_id}]: {json.dumps(system_resources)}")
    
    try:
        logger.debug(f"Normalizing language [exec_id={execution_id}]: {language}")
        language = language.lower()
        if language not in LANGUAGE_EXTENSIONS:
            supported = list(LANGUAGE_EXTENSIONS.keys())
            logger.warning(f"Unsupported language [exec_id={execution_id}]: {language}, supported={supported}")
            raise CodeExecutionError(f"Unsupported language: {language}. Supported languages: {', '.join(supported)}")
        
        original_timeout = timeout
        timeout = min(max(1, timeout), MAX_TIMEOUT)
        if original_timeout != timeout:
            logger.info(f"Adjusted timeout [exec_id={execution_id}]: {original_timeout} -> {timeout}")

        logger.debug(f"Creating execution directory [exec_id={execution_id}]")
        base_dir = Path("/home/sandbox/code")
        base_dir.mkdir(exist_ok=True)
        
        execution_dir = base_dir / execution_id
        execution_dir.mkdir(exist_ok=True)
        logger.debug(f"Created directory [exec_id={execution_id}]: {execution_dir}")
        
        # Prep phase
        phases["setup"]["end"] = time.time()
        setup_time = phases["setup"]["end"] - phases["setup"]["start"]
        logger.debug(f"Setup completed [exec_id={execution_id}] in {setup_time:.4f}s")
        
        # Get the appropriate filename for the language
        filename = LANGUAGE_FILENAMES.get(language, f"snippet{LANGUAGE_EXTENSIONS[language]}")
        file_path = execution_dir / filename
        
        # Log file creation
        logger.debug(f"Creating source file [exec_id={execution_id}]: {file_path}")
        
        # Write code to file
        with open(file_path, 'w') as f:
            f.write(code_snippet)
            
        file_size = file_path.stat().st_size
        logger.debug(f"Source file created [exec_id={execution_id}]: {file_size} bytes")
        
        # Get execution command for language
        cmd = LANGUAGE_COMMANDS[language](str(file_path))
        logger.info(f"Execution command [exec_id={execution_id}]: {' '.join(cmd)}")
        
        # Set resource limits
        # Prevent fork bombs and other resource abuse
        def limit_resources():
            # Set max proc count
            resource.setrlimit(resource.RLIMIT_NPROC, (20, 20))
            
            # Set CPU time limit, in secs
            resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
            
            # Set virtual memory limit
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        
        # Execute the code with timeout
        logger.info(f"Starting execution [exec_id={execution_id}, timeout={timeout}s]")
        phases["execution"]["start"] = time.time()
        
        try:
            # Create proc
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=execution_dir,
                text=True,
                preexec_fn=limit_resources
            )
            
            #Monitor thread
            monitor_thread = threading.Thread(
                target=monitor_process,
                args=(process, execution_id),
                daemon=True
            )
            monitor_thread.start()
            
            logger.debug(f"Process started [exec_id={execution_id}, pid={process.pid}]")
            
            try:
                # Wait for process to complete with timeout
                logger.debug(f"Waiting for process output [exec_id={execution_id}]")
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
                logger.debug(f"Process completed [exec_id={execution_id}, exit_code={exit_code}]")
                
            except subprocess.TimeoutExpired:
                # Process exceeded timeout
                logger.warning(f"Process timeout [exec_id={execution_id}, timeout={timeout}s]")
                
                # Kill the process and its process group if it times out
                parent = process
                parent_id = parent.pid
                
                # Log process tree before killing
                try:
                    p = psutil.Process(parent_id)
                    children = p.children(recursive=True)
                    logger.debug(f"Process tree before killing [exec_id={execution_id}]: "
                                f"parent={parent_id}, children={len(children)}")
                except Exception as e:
                    logger.debug(f"Error getting process tree [exec_id={execution_id}]: {str(e)}")
                
                # Try to kill the process group
                try:
                    logger.debug(f"Attempting to kill process group [exec_id={execution_id}, pgid={os.getpgid(parent_id)}]")
                    os.killpg(os.getpgid(parent_id), signal.SIGTERM)
                except Exception as e:
                    logger.debug(f"Error killing process group [exec_id={execution_id}]: {str(e)}")
                    
                # Try to kill process directly
                try:
                    logger.debug(f"Killing process directly [exec_id={execution_id}, pid={parent_id}]")
                    parent.kill()
                except Exception as e:
                    logger.debug(f"Error killing process [exec_id={execution_id}]: {str(e)}")
                
                # Get any output before timeout
                logger.debug(f"Retrieving output from timed-out process [exec_id={execution_id}]")
                stdout, stderr = process.communicate()
                exit_code = -1
                stderr += f"\n\nExecution timed out after {timeout} seconds."
                logger.info(f"Process terminated due to timeout [exec_id={execution_id}]")
            
            # Record execution end time
            phases["execution"]["end"] = time.time()
            execution_time = phases["execution"]["end"] - phases["execution"]["start"]
            
            # Log detailed execution stats
            execution_stats = {
                "exit_code": exit_code,
                "execution_time": round(execution_time, 4),
                "stdout_length": len(stdout) if stdout else 0,
                "stderr_length": len(stderr) if stderr else 0,
                "has_output": bool(stdout or stderr)
            }
            logger.info(f"Execution stats [exec_id={execution_id}]: {json.dumps(execution_stats)}")
            
            # Log output snippets for debugging (limit length)
            if stdout:
                stdout_snippet = stdout[:100] + "..." if len(stdout) > 100 else stdout
                logger.debug(f"Stdout snippet [exec_id={execution_id}]: {stdout_snippet}")
            
            if stderr:
                stderr_snippet = stderr[:100] + "..." if len(stderr) > 100 else stderr
                logger.debug(f"Stderr snippet [exec_id={execution_id}]: {stderr_snippet}")
            
            # Combine stdout and stderr
            output = stdout
            if stderr:
                if output:
                    output += "\n\n" + stderr
                else:
                    output = stderr
                    
            if not output and exit_code != 0:
                output = f"Process exited with code {exit_code}"
                
            return output
                
        except Exception as e:
            logger.error(f"Execution error [exec_id={execution_id}]: {str(e)}")
            raise CodeExecutionError(f"Execution error: {str(e)}")
    
    finally:
        # Cleanup phase
        phases["cleanup"]["start"] = time.time()
        
        try:
            logger.debug(f"Cleaning up execution directory [exec_id={execution_id}]")
            shutil.rmtree(execution_dir)
            logger.debug(f"Cleanup completed [exec_id={execution_id}]")
        except Exception as e:
            logger.error(f"Cleanup error [exec_id={execution_id}]: {str(e)}")
            
        phases["cleanup"]["end"] = time.time()
        
        # Log total execution lifecycle
        total_time = phases["cleanup"]["end"] - phases["setup"]["start"]

        time_summary = {
            "setup_time": round((phases["setup"]["end"] - phases["setup"]["start"]) * 1000, 2),
            "execution_time": round((phases["execution"]["end"] - phases["execution"]["start"]) * 1000, 2) if phases["execution"]["end"] else None,
            "cleanup_time": round((phases["cleanup"]["end"] - phases["cleanup"]["start"]) * 1000, 2),
            "total_time": round(total_time * 1000, 2)
        }
        
        logger.info(f"Execution completed [exec_id={execution_id}]: {json.dumps(time_summary)}")