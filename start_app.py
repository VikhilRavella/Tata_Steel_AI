import subprocess
import sys
import time
import os

def main():
    print("==================================================")
    print("STARTING TATA STEEL INDUSTRIAL AI PLATFORM")
    print("==================================================")
    
    # Ensure we run from the correct directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # 1. Pull Required Ollama Models
    print("\n[+] Initializing and Verifying AI Models (Ollama)...")
    models = ["mistral:latest", "qwen2.5vl:latest", "qwen2.5-coder:7b"]
    for model in models:
        print(f"    -> Pulling {model} (this will be fast if already installed)...")
        subprocess.run(["ollama", "pull", model], check=False)

    # 2. Start Backend (Uvicorn)
    print("\n[+] Starting Backend API Server (Port 8000)...")
    backend_cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    backend_process = subprocess.Popen(backend_cmd)
    
    # 3. Start Frontend (HTTP Server)
    print("[+] Starting Frontend Web Server (Port 3000)...")
    frontend_cmd = [sys.executable, "-m", "http.server", "3000", "-d", "frontend"]
    frontend_process = subprocess.Popen(frontend_cmd)
    
    print("\n==================================================")
    print("ALL SERVICES RUNNING SUCCESSFULLY")
    print("-> Frontend URL: http://localhost:3000/pages/index.html")
    print("-> Backend API Docs: http://localhost:8000/docs")
    print("Press Ctrl+C to shut down all services.")
    print("==================================================\n")
    
    # 4. Automatically open the browser
    import webbrowser
    print("[+] Launching platform in your default web browser...")
    time.sleep(2) # Give the servers a moment to spin up
    webbrowser.open("http://localhost:3000/pages/index.html")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Shutting down servers gracefully...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("[+] All services stopped.")

if __name__ == "__main__":
    main()
