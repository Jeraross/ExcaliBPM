# Security Policy

## Supported Versions

Only the versions listed below actively receive security fixes:

| Version | Supported          |
| ------- | ------------------ |
| `main` (latest) | ✅ Yes |
| Older versions | ❌ No |

---

## Reporting a Vulnerability

If you have found a security vulnerability in this project, **please do not open a public Issue**. This protects other users while a fix is being developed.

### How to Report

Use the **GitHub Private Security Advisory**:

1. Go to the **Security** tab of this repository
2. Click **"Report a vulnerability"**
3. Fill in the form with as much detail as possible

> You can access it directly at:  
> `https://github.com/YOUR_USERNAME/YOUR_REPOSITORY/security/advisories/new`

---

## What to Include in Your Report

To help us reproduce and fix the issue quickly, please include:

- **Clear description** of the vulnerability
- **Steps to reproduce** (with sample audio files, commands, or configurations if applicable)
- **Potential impact** (what a malicious actor could do)
- **Affected version** (branch, commit, or tag)
- **Environment** (operating system, Python version, dependencies)
- A suggested fix, if you have one (optional but appreciated)

---

## High-Risk Areas in This Project

As an audio analysis and mixing application, the following areas carry special security considerations:

- **Audio file processing** — malicious files (WAV, MP3, FLAC) may exploit vulnerabilities in decoding libraries such as `librosa`, `soundfile`, or `ffmpeg`
- **External API integrations** (e.g. Spotify API) — exposure of tokens or API keys
- **Third-party dependencies** — vulnerabilities in `numpy`, `scipy`, `librosa`, and other Python scientific ecosystem packages
- **Local file read/write** — path traversal via user-supplied file paths

---

## Response Timeline

| Step | Expected Timeframe |
| ---- | ------------------ |
| Acknowledgement of report | Within **3 business days** |
| Initial assessment (valid/invalid) | Within **7 business days** |
| Estimated fix timeline | Within **30 days** (depending on complexity) |
| Public disclosure | After the fix has been released |

---

## Responsible Disclosure

We follow the **Coordinated Vulnerability Disclosure (CVD)** model:

- We will work with you to understand and resolve the issue
- We will give you public credit for the finding (if you wish)
- We ask that you wait for the fix to be published before disclosing publicly

---

## Out of Scope

The following are **not** considered security vulnerabilities in this project:

- Incorrect music analysis results (wrong key or BPM detection)
- Performance issues or slowness when processing large audio files
- Functional bugs with no security impact
- Vulnerabilities in unsupported versions

---

## Acknowledgements

We appreciate everyone who helps keep this project secure through responsible disclosure. 🙏
