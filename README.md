# PowerMCP ⚡

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

PowerMCP is an open-source collection of MCP servers for power system software like PowerWorld and OpenDSS. These tools enable LLMs to directly interact with power system applications, facilitating intelligent coordination, simulation, and control in the energy domain.

## 🌟 What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/introduction) (MCP) is a standard that enables AI applications to connect with external tools.

## 🛡️ Cross-Platform Security Audit

PowerMCP includes a backend-neutral **Security Audit MCP server** for standardized base-case and N-1 screening across pandapower and PyPSA. It independently evaluates contingencies, detects voltage and thermal violations, treats non-convergence as critical, ranks contingencies with a deterministic 0–10 severity score, and can render a concise Markdown engineering report.

```bash
python SecurityAudit/security_audit_mcp.py
```

The audit layer uses deterministic screening helpers shared by both backends. Inputs are validated before a simulator is loaded, and contingency records normalize identifiers and default fields so LLM clients receive stable JSON-friendly results regardless of backend-specific identifier types.

The security layer is deliberately complementary to the existing backend-specific servers: use it for a consistent first-pass screening and then use PowerWorld, pandapower, PyPSA, PSSE, PSLF, ANDES, OpenDSS, or other integrations for deeper studies.

## 🤝 Our Community Vision

We're building an open-source community focused on accelerating AI adoption in the power domain through MCP. Our goals are collaboration, innovation, education, and standardization.

## 🚀 Getting Started with MCP

### 📖 Quick start

> **🚀 New to PowerMCP? Start here!**

The recommended way to get started is the `powermcp` package and its installer:

```bash
pip install powermcp
powermcp install
```

### Installation

PowerMCP installs as a single Python package with an interactive CLI. Python 3.10+ is required.

```bash
pip install powermcp
```

The base install includes open-source engines that need no extra setup — **pandapower**, **PyPSA**, and **PowerIO**. Other tools are opt-in via extras:

```bash
pip install powermcp[psse]
pip install powermcp[andes,opendss]
pip install powermcp[opensource]
pip install powermcp[all]
```

### CLI commands

| Command | Description |
|---|---|
| `powermcp install` | Setup wizard |
| `powermcp run <tool>` | Launch a server over stdio |
| `powermcp list` | List available tools |
| `powermcp doctor` | Check dependencies and configured paths |
| `powermcp config show` / `config set <tool>.<key> <path>` | Inspect or set local software paths |

### Security Audit testing

```bash
pytest SecurityAudit/tests/test_security_audit.py -v
```

The tests cover severity calculation, deterministic ranking, risk classification, report generation, input validation, and stable contingency-record construction without requiring a commercial simulator.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://power-agent.github.io/) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
