# Security Review Report: 2PAC Image Analysis Tool

**Review Date:** 2025-10-30
**Reviewer:** Security Analysis
**Version:** 1.5.0

---

## Executive Summary

This security review identified **5 critical/high severity vulnerabilities** and **3 medium/low severity issues** in the 2PAC codebase. The most critical issue is an **arbitrary code execution vulnerability** via unsafe pickle deserialization. Immediate remediation is recommended for production use.

---

## Critical & High Severity Vulnerabilities

### 1. 🔴 CRITICAL: Arbitrary Code Execution via Pickle Deserialization (CWE-502)

**Location:** `find_bad_images.py:692, 720`

**Severity:** CRITICAL (CVSS 9.8)

**Description:**
The application uses Python's `pickle.load()` to deserialize session progress files without validation. Pickle can execute arbitrary Python code during deserialization, allowing an attacker to achieve remote code execution.

```python
# Line 692 - Unsafe deserialization
with open(progress_file, 'rb') as f:
    progress_state = pickle.load(f)  # VULNERABLE!
```

**Attack Scenario:**
1. Attacker creates a malicious `.progress` file with embedded Python code
2. User runs `find_bad_images.py --resume <malicious_session>`
3. Pickle executes attacker's code with user's privileges
4. Complete system compromise

**Impact:**
- Remote Code Execution (RCE)
- Complete system compromise
- Data exfiltration
- Malware installation

**Remediation:**
Replace pickle with JSON for serialization:

```python
import json

# Save progress (SECURE)
with open(progress_file, 'w') as f:
    json.dump(progress_state, f)

# Load progress (SECURE)
with open(progress_file, 'r') as f:
    progress_state = json.load(f)
```

**Status:** ⚠️ UNPATCHED

---

### 2. 🟠 HIGH: Path Traversal Vulnerability (CWE-22)

**Location:** `find_bad_images.py:934-941`

**Severity:** HIGH (CVSS 7.5)

**Description:**
When moving corrupt files, the application constructs destination paths using `os.path.relpath()` and `os.path.join()` without validating for path traversal sequences (e.g., `../../../etc/passwd`).

```python
# Line 934-941 - Path traversal vulnerability
rel_path = os.path.relpath(file_path, str(directory))
dest_path = os.path.join(move_to, rel_path)  # VULNERABLE!
os.makedirs(os.path.dirname(dest_path), exist_ok=True)
shutil.move(file_path, dest_path)
```

**Attack Scenario:**
1. Attacker places specially-crafted symlinks or files with `..` in their paths
2. User runs tool with `--move-to /safe/location`
3. Files are written outside the intended directory (e.g., `/etc/cron.d/`)
4. Attacker achieves privilege escalation or persistence

**Impact:**
- Arbitrary file write
- Directory traversal
- Potential privilege escalation
- Configuration file overwrite

**Remediation:**
Validate and sanitize file paths:

```python
import os.path

def safe_join(base_dir, user_path):
    """Safely join paths and prevent traversal attacks."""
    # Normalize and resolve the path
    full_path = os.path.normpath(os.path.join(base_dir, user_path))

    # Ensure the result is within base_dir
    if not full_path.startswith(os.path.abspath(base_dir)):
        raise ValueError(f"Path traversal detected: {user_path}")

    return full_path
```

**Status:** ⚠️ UNPATCHED

---

### 3. 🟠 HIGH: Command Injection via Subprocess (CWE-78)

**Location:** `find_bad_images.py:286-295`

**Severity:** MEDIUM-HIGH (CVSS 7.0)

**Description:**
The application calls external tools (`exiftool`, `identify`) via subprocess with user-controlled file paths. While not using `shell=True`, special characters in filenames could potentially be exploited.

```python
# Line 286-295 - Potential command injection
result = subprocess.run(['exiftool', '-m', '-p', '$Error', file_path],
                       capture_output=True, text=True, timeout=5)
result = subprocess.run(['identify', '-verbose', file_path],
                       capture_output=True, text=True, timeout=5)
```

**Attack Scenario:**
1. Attacker creates file with name: `evil.jpg; rm -rf /`
2. Depending on shell processing, commands could be executed
3. System compromise

**Impact:**
- Potential command execution
- Information disclosure via error messages
- Denial of service

**Remediation:**
1. Validate file paths before passing to subprocess
2. Use absolute paths only
3. Whitelist allowed characters
4. Consider disabling external tool validation by default

```python
import re

def validate_file_path(path):
    """Validate file path for subprocess usage."""
    # Only allow alphanumeric, dots, dashes, underscores, forward slashes
    if not re.match(r'^[a-zA-Z0-9._/\-]+$', path):
        raise ValueError(f"Invalid characters in path: {path}")

    # Must be absolute path
    if not os.path.isabs(path):
        raise ValueError(f"Path must be absolute: {path}")

    return path
```

**Status:** ⚠️ UNPATCHED

---

## Medium Severity Vulnerabilities

### 4. 🟡 MEDIUM: Missing Import Causes Runtime Crash (Bug)

**Location:** `rat_finder.py:136`

**Severity:** MEDIUM (Availability Impact)

**Description:**
The `rat_finder.py` module uses `tempfile.NamedTemporaryFile` but never imports the `tempfile` module, causing a runtime crash.

```python
# Line 136 - Missing import
temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=True)
# NameError: name 'tempfile' is not defined
```

**Impact:**
- Application crash during ELA analysis
- Denial of service for JPEG steganography detection

**Remediation:**
Add import at top of file:

```python
import tempfile
```

**Status:** ⚠️ UNPATCHED

---

### 5. 🟡 MEDIUM: Weak Cryptographic Hash (CWE-327)

**Location:** `find_bad_images.py:639`

**Severity:** LOW-MEDIUM (CVSS 3.7)

**Description:**
The application uses MD5 for generating session IDs. While session IDs are not security-critical, MD5 is cryptographically broken and could allow session ID prediction or collision attacks.

```python
# Line 639 - Weak hash function
hash_obj = hashlib.md5()
```

**Impact:**
- Session ID collision (low probability)
- Predictable session identifiers
- Best practice violation

**Remediation:**
Use SHA-256 or better:

```python
import hashlib

hash_obj = hashlib.sha256()
# Rest remains the same
```

**Status:** ⚠️ UNPATCHED

---

### 6. 🟡 MEDIUM: Lack of Input Validation

**Location:** Multiple locations

**Severity:** MEDIUM (CVSS 5.3)

**Description:**
The application does not validate:
- File sizes (could load multi-GB images causing memory exhaustion)
- Image dimensions (could cause DoS via decompression bombs)
- File type mismatches (file extension vs. actual format)
- Directory depth (could cause stack overflow)

**Impact:**
- Denial of Service
- Memory exhaustion
- Resource exhaustion

**Remediation:**
Add validation checks:

```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_IMAGE_PIXELS = 50000 * 50000    # 50MP

def validate_image_file(file_path):
    """Validate image file before processing."""
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_size} bytes")

    # Check image dimensions
    with Image.open(file_path) as img:
        width, height = img.size
        if width * height > MAX_IMAGE_PIXELS:
            raise ValueError(f"Image too large: {width}x{height}")

    return True
```

**Status:** ⚠️ UNPATCHED

---

## Low Severity Issues

### 7. 🟢 LOW: Information Disclosure via Error Messages

**Location:** Multiple locations

**Severity:** LOW (CVSS 2.7)

**Description:**
Detailed error messages and stack traces can reveal system information, file paths, and internal structure to attackers.

**Remediation:**
- Sanitize error messages shown to users
- Log detailed errors internally only
- Avoid showing full file paths in error messages

**Status:** ⚠️ UNPATCHED

---

### 8. 🟢 LOW: No File Type Validation

**Location:** `find_bad_images.py:748-772`

**Severity:** LOW (CVSS 3.1)

**Description:**
The application relies solely on file extensions to determine file types. Malicious files could be disguised with image extensions.

**Remediation:**
Validate actual file format matches extension:

```python
def validate_file_type(file_path, expected_formats):
    """Ensure file content matches extension."""
    with Image.open(file_path) as img:
        actual_format = img.format

        # Check if format matches expected
        if actual_format not in expected_formats:
            raise ValueError(f"File format mismatch: {actual_format}")
```

**Status:** ⚠️ UNPATCHED

---

## Recommendations

### Immediate Actions (Critical Priority)

1. **Replace pickle with JSON** - Fix arbitrary code execution vulnerability
2. **Implement path traversal protection** - Validate all file paths
3. **Add tempfile import** - Fix runtime crash in rat_finder.py

### Short-term Actions (High Priority)

4. **Upgrade to SHA-256** - Replace MD5 usage
5. **Add input validation** - File sizes, dimensions, types
6. **Sanitize subprocess inputs** - Validate paths before external tool calls

### Long-term Actions (Medium Priority)

7. **Implement security modes** - Add `--safe-mode` flag with stricter validation
8. **Add rate limiting** - Prevent resource exhaustion
9. **Security audit** - Third-party penetration testing
10. **Add integrity checks** - Verify file hashes before processing

---

## Security Features to Add (Low-Hanging Fruit for Demo)

### 1. File Hash Verification
Add SHA-256 hash calculation and verification for processed files.

### 2. Security Scan Mode
Add `--security-scan` mode that:
- Detects files with mismatched extensions
- Identifies suspicious metadata
- Flags potentially malicious images
- Checks for polyglot files

### 3. Sandbox Mode
Add `--sandbox` flag that:
- Runs with restricted file system access
- Limits memory usage
- Disables external tool execution
- Uses read-only mode

### 4. Malicious Image Detection
Enhance steganography detection to identify:
- Polyglot files (valid as multiple formats)
- Files with executable code in metadata
- Files with suspicious EXIF data
- Known exploit patterns (e.g., ImageTragick)

### 5. Rate Limiting
Add configurable rate limiting to prevent DoS:
- Max files per minute
- Max total file size per run
- Memory usage limits

---

## Compliance & Standards

**Relevant Standards:**
- OWASP Top 10 2021
  - A03:2021 - Injection (Command Injection, Path Traversal)
  - A08:2021 - Software and Data Integrity Failures (Pickle)
- CWE Top 25
  - CWE-502: Deserialization of Untrusted Data
  - CWE-78: OS Command Injection
  - CWE-22: Path Traversal

**Severity Ratings:**
- Critical: Immediate RCE, full system compromise
- High: Significant security impact, data exposure
- Medium: Availability impact, partial compromise
- Low: Information disclosure, best practices

---

## Testing Recommendations

### Security Test Cases

1. **Pickle Deserialization Test**
   - Create malicious `.progress` file with embedded code
   - Verify code execution is prevented after patch

2. **Path Traversal Test**
   - Create files with `../` in names
   - Verify files cannot be written outside target directory

3. **Fuzzing**
   - Fuzz file names with special characters
   - Fuzz file contents with malformed data
   - Monitor for crashes and unexpected behavior

4. **DoS Testing**
   - Test with extremely large files
   - Test with decompression bombs
   - Test with thousands of files

---

## References

- [OWASP Deserialization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html)
- [CWE-502: Deserialization of Untrusted Data](https://cwe.mitre.org/data/definitions/502.html)
- [CWE-22: Path Traversal](https://cwe.mitre.org/data/definitions/22.html)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

---

## Conclusion

The 2PAC tool provides valuable functionality for image corruption detection and steganography analysis. However, several critical security vulnerabilities must be addressed before the tool can be safely used in production environments, especially with untrusted input.

The highest priority is fixing the pickle deserialization vulnerability, which allows arbitrary code execution. The path traversal vulnerability should also be addressed immediately to prevent file system attacks.

Once these critical issues are resolved, the tool will be significantly more secure for general use.

---

**Report Version:** 1.0
**Next Review:** After critical fixes implemented
