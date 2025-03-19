"""
Flask API for the Code Runner Service.
Executes code snippets within the container instead of creating new containers.
"""
from flask import Flask, request, jsonify, g, Response
from code_executor import execute_code, CodeExecutionError
import os
import time
import traceback
from dotenv import load_dotenv
import sys
import logging
import json
import uuid
from functools import wraps

ACR_LOGIN_SERVER = os.environ.get("ACR_LOGIN_SERVER", "devreadyregistry.azurecr.io")
SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "1ac160f1-0028-4451-9808-5fe61819e5b6")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "Sandbox-DevReady")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(request_id)s] - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)



class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(g, 'request_id', 'no-request-id')
        return True

root_logger = logging.getLogger()
root_logger.addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)

print(f"Python version: {sys.version}")
print("Starting code runner service...")

load_dotenv()

app = Flask(__name__)

# Request logging middleware
@app.before_request
def before_request():
    # Generate a unique request ID
    g.request_id = str(uuid.uuid4())
    g.start_time = time.time()
    
    # Log the incoming request
    request_data = {
        "method": request.method,
        "path": request.path,
        "remote_addr": request.remote_addr,
        "user_agent": request.headers.get('User-Agent', ''),
        "content_length": request.content_length,
    }
    
    if request.is_json and request.content_length:
        data = request.get_json(silent=True)
        if data:
            if 'code' in data:
                code_length = len(data['code']) if isinstance(data['code'], str) else 0
                request_data['code_length'] = code_length
                # Replace actual code with length info for logging
                data_for_log = data.copy()
                data_for_log['code'] = f"[{code_length} chars]"
                request_data['body'] = data_for_log
    
    logger.info(f"Received request: {json.dumps(request_data)}")

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time
    
    # Log response details
    response_data = {
        "status_code": response.status_code,
        "content_length": response.content_length,
        "duration_ms": round(duration * 1000, 2)
    }
    
    # Add response timing header
    response.headers['X-Response-Time'] = f"{duration:.6f}"
    
    if 200 <= response.status_code < 300:
        logger.info(f"Request completed successfully: {json.dumps(response_data)}")
    elif 400 <= response.status_code < 500:
        logger.warning(f"Request failed with client error: {json.dumps(response_data)}")
    elif 500 <= response.status_code < 600:
        logger.error(f"Request failed with server error: {json.dumps(response_data)}")
    else:
        logger.info(f"Request completed with status {response.status_code}: {json.dumps(response_data)}")
    
    return response

# Custom JSON response to include request_id
def json_response(data, status=200):
    """Creates a JSON response with request_id included"""
    if isinstance(data, dict):
        data['request_id'] = g.request_id
    response_obj = jsonify(data)
    return response_obj, status

@app.route("/run", methods=["POST"])
def run_code():
    """
    Handle POST requests to /run endpoint.
    Executes code within the current container.
    
    Expects a JSON payload with:
    {
        "language": "python",
        "code": "print('Hello, world!')"
    }
    
    Returns JSON with:
    {
        "output": "Hello, world!",
        "execution_time": 0.25,
        "request_id": "uuid"
    }
    
    Or on error:
    {
        "error": "Error message",
        "request_id": "uuid"
    }
    """
    logger.info("Processing code execution request")
    
    try:
        logger.info("Parsing request JSON")
        data = request.get_json()
        
        if not data:
            logger.warning("Request missing body or invalid JSON")
            return json_response({"error": "Request body must be valid JSON"}, 400)
        
        #Get request body
        language = data.get("language")
        code_snippet = data.get("code")
        
        timeout = data.get("timeout", int(os.environ.get("DEFAULT_TIMEOUT", "30")))
        logger.info(f"Request parameters: language={language}, timeout={timeout}, code_length={len(code_snippet) if code_snippet else 0}")
        
        #Validate
        logger.info("Validating request parameters")
        validation_errors = []
        
        if not language:
            validation_errors.append("Missing 'language' parameter")
        
        if not code_snippet:
            validation_errors.append("Missing 'code' parameter")
            
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            logger.warning(f"Validation failed: {error_msg}")
            return json_response({"error": error_msg}, 400)
        
        logger.info(f"Preparing to execute {language} code")
        
        logger.info("Starting code execution")
        exec_start = time.time()
        
        result = execute_code(language, code_snippet, timeout)
        
        execution_time = time.time() - exec_start
        logger.info(f"Code execution completed in {execution_time:.4f}s")

        output_length = len(result) if result else 0
        logger.info(f"Processing execution result: {output_length} chars")
        
        # Create and log response
        response_data = {
            "output": result,
            "execution_time": round(execution_time, 3),
            "language": language,
            "output_length": output_length
        }
        
        logger.info(f"Sending successful response with {output_length} chars of output")
        return json_response(response_data)
        
    except CodeExecutionError as e:
        error_message = str(e)
        logger.error(f"Code execution error: {error_message}")
        return json_response({"error": error_message, "phase": "execution"}, 400)
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Unexpected server error: {error_message}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return json_response({"error": "Internal server error", "details": error_message}, 500)

@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    logger.debug("Health check request received")
    
    # Basic system statistics
    import psutil
    
    system_stats = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }
    
    # Get process stats
    process = psutil.Process(os.getpid())
    process_stats = {
        "process_cpu_percent": process.cpu_percent(),
        "process_memory_mb": process.memory_info().rss / (1024 * 1024),
        "process_threads": process.num_threads(),
        "process_uptime_seconds": time.time() - process.create_time()
    }
    
    health_data = {
        "status": "ok", 
        "message": "Code runner service is operational",
        "time": time.strftime('%Y-%m-%d %H:%M:%S'),
        "system": system_stats,
        "process": process_stats
    }
    
    logger.debug("Health check completed")
    return json_response(health_data)

@app.route("/", methods=["GET"])
def root():
    """Root endpoint with basic info"""
    logger.debug("Root endpoint request received")
    
    # Get container information
    import platform
    import socket
    
    system_info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpus": os.cpu_count(),
        "container_id": os.environ.get("HOSTNAME", "unknown")
    }
    
    api_info = {
        "service": "Code Runner Service",
        "version": "2.0.0",
        "environment": os.environ.get("ENVIRONMENT", "production"),
        "endpoints": {
            "/run": "POST - Run code in the container",
            "/health": "GET - Service health check"
        },
        "supported_languages": [
            "python", "java", "go", "javascript/js", "typescript/ts"
        ],
        "system_info": system_info
    }
    
    logger.debug("Root endpoint request completed")
    return json_response(api_info)

if __name__ == "__main__":
    # For local testing only
    port = int(os.environ.get("PORT", 8000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)