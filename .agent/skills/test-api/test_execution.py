import argparse
import urllib.request
import urllib.error
import urllib.parse
import json
import time
import sys

# Default local API configuration
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "dev-api-key-change-me"  # From config.example.toml

def execute_code(url, api_key, language, code, version=None, stdin=None):
    """Submits code for synchronous execution and prints the result."""
    
    endpoint = f"{url}/api/v1/execute/sync"
    
    payload = {
        "language": language,
        "code": code
    }
    
    if version:
        payload["version"] = version
    if stdin:
        payload["stdin"] = stdin
        
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(
        endpoint, 
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key
        },
        method="POST"
    )
    
    print(f"Sending {language} code to {endpoint}...")
    start_time = time.time()
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            status_code = response.getcode()
            
            elapsed = time.time() - start_time
            print(f"\\n--- Execution Result ({status_code} - {elapsed:.2f}s) ---")
            print(f"Status: {result.get('status')}")
            print(f"Exit Code: {result.get('exit_code')}")
            
            stdout = result.get('stdout')
            if stdout:
                print(f"\\nStdout:\\n{stdout.strip()}")
                
            stderr = result.get('stderr')
            if stderr:
                print(f"\\nStderr:\\n{stderr.strip()}")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}\\nMake sure the API is running at {url}", file=sys.stderr)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Code Executor API")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API Base URL")
    parser.add_argument("--key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--lang", default="python", help="Subject Language")
    parser.add_argument("--code", default="print('Hello from test_execution.py!')", help="Code to execute")
    parser.add_argument("--version", help="Language version")
    parser.add_argument("--stdin", help="Standard input data")
    
    args = parser.parse_args()
    execute_code(args.url, args.key, args.lang, args.code, args.version, args.stdin)
