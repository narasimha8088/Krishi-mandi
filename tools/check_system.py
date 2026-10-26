"""Krishi-Mandi system check. Uses only the Python standard library, so it runs before anything is installed."""
import os, platform, shutil, socket, ssl, subprocess, sys, urllib.error, urllib.request

OK, BAD, WARN = "[ OK ]", "[FAIL]", "[WARN]"
problems = []


def line(tag, msg):
    print(f"{tag} {msg}")


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return f"(could not run: {e})"


print("=" * 64)
print(" KRISHI-MANDI SYSTEM CHECK")
print("=" * 64)

# 1. Windows / Python
print("\n1. Computer and Python")
line(OK, f"Operating system: {platform.platform()}")
v = sys.version_info
bits = 64 if sys.maxsize > 2**32 else 32
line(OK if v >= (3, 10) else BAD, f"Python {v.major}.{v.minor}.{v.micro} ({bits}-bit) at {sys.executable}")
if v < (3, 10):
    problems.append("Python is older than 3.10. Install Python 3.12 from https://www.python.org/downloads/")
if bits != 64:
    line(BAD, "This is 32-bit Python. The packages need 64-bit Python.")
    problems.append("Install the 64-bit Python (Windows installer 64-bit) from python.org")
if v >= (3, 15):
    line(WARN, "Python is newer than the versions this project was checked with (3.10 to 3.14). Python 3.12 is the safest choice.")
if shutil.which("py"):
    line(OK, "The 'py' launcher is installed")
else:
    line(WARN, "The 'py' launcher was not found. That is fine if 'python' works.")
pipv = run([sys.executable, "-m", "pip", "--version"])
line(OK if pipv.startswith("pip") else BAD, pipv or "pip not found")
if not pipv.startswith("pip"):
    problems.append("pip is missing. Reinstall Python from python.org and keep 'pip' ticked in Optional Features.")

# 2. Proxy / pip config
print("\n2. Proxy and pip settings")
found = False
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "PIP_INDEX_URL", "PIP_CERT", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
    if os.environ.get(k):
        found = True
        line(WARN, f"{k} = {os.environ[k]}")
if not found:
    line(OK, "No proxy or certificate environment variables are set")
cfg = run([sys.executable, "-m", "pip", "config", "list"])
if cfg:
    line(WARN, "pip has custom settings (check these are correct):")
    for l in cfg.splitlines():
        print("        " + l)
else:
    line(OK, "pip has no custom settings")

# 3. Internet and certificates
print("\n3. Internet access (each site is tried with certificate checking, then without)")
SITES = [
    ("Package server (pip installs)", "https://pypi.org/simple/pip/", True),
    ("Package files (pip installs)", "https://files.pythonhosted.org/", True),
    ("Tailwind CSS (web page)", "https://cdn.tailwindcss.com/", False),
    ("React, Leaflet (web page)", "https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js", False),
    ("htm library (web page)", "https://cdn.jsdelivr.net/npm/htm@3.1.1/dist/htm.umd.js", False),
    ("Plotly charts (web page)", "https://cdn.plot.ly/plotly-basic-2.35.2.min.js", False),
    ("Google Fonts (web page)", "https://fonts.googleapis.com/", False),
    ("Map tiles (web page)", "https://tile.openstreetmap.org/0/0/0.png", False),
]


def fetch(url, verify):
    """Returns an HTTP status. A 404 etc. still proves the server was reached, so it counts as success."""
    ctx = ssl.create_default_context() if verify else ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={"User-Agent": "krishi-mandi-check"})
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
            r.read(256)
            return r.status
    except urllib.error.HTTPError as e:
        if e.code in (403, 407, 451):
            raise RuntimeError(f"blocked by a proxy or firewall (HTTP {e.code})")
        return e.code


pip_ssl_issue = pip_blocked = cdn_issue = False
for name, url, needed_for_pip in SITES:
    try:
        fetch(url, True)
        line(OK, name)
        continue
    except Exception as e1:
        err = str(e1)[:90]
    host = url.split("/")[2]
    if "blocked by a proxy" in err:
        line(BAD, f"{name}: {err}")
        problems.append(f"{host}: {err}")
        pip_blocked |= needed_for_pip
        cdn_issue |= not needed_for_pip
        continue
    try:
        fetch(url, False)
        line(BAD, f"{name}: reachable, but the certificate check failed ({err})")
        problems.append(f"Certificate problem reaching {host}")
        pip_ssl_issue |= needed_for_pip
        cdn_issue |= not needed_for_pip
    except Exception as e2:
        line(BAD, f"{name}: cannot connect ({str(e2)[:80]})")
        problems.append(f"Cannot reach {host}")
        pip_blocked |= needed_for_pip
        cdn_issue |= not needed_for_pip

# 4. Ports
print("\n4. Ports")
free = None
for port in range(8000, 8011):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            free = port
            break
        except OSError:
            line(WARN, f"Port {port} is already in use")
line(OK if free else BAD, f"Port {free} is free and will be used" if free else "No free port between 8000 and 8010")

# Summary
print("\n" + "=" * 64)
if not problems:
    print(" RESULT: everything looks good. Run START.bat.")
else:
    print(" RESULT: problems found:")
    for p in dict.fromkeys(problems):
        print("   - " + p)
    print("\n WHAT TO DO:")
    if pip_ssl_issue:
        print("   * Certificate problem: something is intercepting secure connections")
        print("     (antivirus web shield, VPN, school/office network). Pause the antivirus HTTPS/web")
        print("     scanning, switch off the VPN, or use your phone hotspot, then run START.bat.")
        print("     START.bat also retries automatically using the Windows certificate store.")
    if pip_blocked:
        print("   * The package server cannot be reached at all. Try another network such as a phone")
        print("     hotspot. If it still fails, see 'Offline install' in SETUP_GUIDE.txt.")
    if cdn_issue:
        print("   * Sites used by the web page are blocked: the dashboard may show a blank page or no map.")
print("=" * 64)
