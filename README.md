# PowerMCP ⚡

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

PowerMCP is an open-source collection of MCP servers for power system software like PowerWorld and OpenDSS. These tools enable LLMs to directly interact with power system applications, facilitating intelligent coordination, simulation, and control in the energy domain.

## 🌟 What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/introduction) is a standard that enables AI applications to connect with external tools.

## 🛡️ Cross-Platform Security Audit

PowerMCP includes a backend-neutral **Security Audit MCP server** for standardized base-case and N-1 screening across pandapower and PyPSA. It independently evaluates contingencies, detects voltage and thermal violations, treats non-convergence as critical, ranks contingencies with a deterministic 0–10 severity score, and can render a concise Markdown engineering report.

```bash
python SecurityAudit/security_audit_mcp.py
```

The audit layer uses deterministic screening helpers shared by both backends. Inputs are validated before simulator execution, and contingency records normalize identifiers and required fields so LLM clients receive stable JSON-friendly results regardless of backend-specific identifier types.

The security layer is deliberately complementary to the existing backend-specific servers: use it for a consistent first-pass screening and then use PowerWorld, pandapower, PyPSA, PSSE, PSLF, ANDES, OpenDSS, or other integrations for deeper studies.

## 🤝 Our Community Vision

We're building an open-source community focused on accelerating AI adoption in the power domain through MCP. Our goals are:

- **Collaboration**: Bring together power system experts, AI researchers, and software developers
- **Innovation**: Create and share MCP servers for various power system software and tools
- **Education**: Provide resources and examples for implementing AI in power systems
- **Standardization**: Develop best practices for AI integration in the energy sector

## 🚀 Getting Started with MCP

### 📖 Quick start

> **🚀 New to PowerMCP? Start here!**

The recommended way to get started is the `powermcp` package and its installer (see the **Installation** section below):

```bash
pip install powermcp
powermcp install        # pick tools, capture local paths, write your MCP client config
```

> 📋 The **[PowerMCP Tutorial PDF](https://github.com/Power-Agent/PowerMCP/blob/main/PowerMCP_Tutorial.pdf)** documents the original **low-code / manual** setup — cloning the repo and hand-editing the Claude Desktop config. It predates the `powermcp` installer and is **not the recommended path**; use it only if you specifically want the manual approach.

### Video Demos

Check out these demos showcasing PowerMCP in action:

- [**Contingency Evaluation Demo**](https://www.youtube.com/watch?v=MbF-SlBI4Ws): An LLM automatically operates power system software, such as PowerWorld and pandapower, to perform contingency analysis and generate professional reports.

- [**Loadgrowth Evaluation Demo**](https://www.youtube.com/watch?v=euFUvhhV5dM): An LLM automatically operates power system software, such as PowerWorld, to evaluate different load growth scenarios and generate professional reports with recommendations.

### Useful MCP Tutorials

MCP follows a client-server architecture where:

* **Hosts** are LLM applications (like Claude Desktop, Claude Code, or Codex) that initiate connections
* **Clients** maintain 1:1 connections between servers and hosts
* **Servers** provide context, tools, and prompts to clients

Check out these helpful tutorials to get started with MCP:

- [**Getting Started with MCP**](https://modelcontextprotocol.io/introduction): Official introduction to the Model Context Protocol fundamentals.
- [**Core Architecture**](https://modelcontextprotocol.io/docs/concepts/architecture): Detailed explanation of the MCP client-server architecture.
- [**Building Your First MCP Server**](https://modelcontextprotocol.io/docs/develop/build-server): Step-by-step guide to building your first MCP server.
- [**Anthropic MCP Tutorial**](https://docs.claude.com/en/docs/mcp): Learn how to build with MCP.
- [**Cursor MCP Tutorial**](https://cursor.com/docs/context/overview): Learn how to use MCP with Cursor.
- [**Other Protocol**](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf): OpenAI Function Calling guidance.

## 📦 Installation

PowerMCP installs as a single Python package with an interactive CLI. Python 3.10+ is required.

```bash
pip install powermcp
```

The base install includes the open-source engines that need no extra setup — **pandapower**, **PyPSA**, and **PowerIO** (the cross-server case-conversion substrate). Every other tool is opt-in via an extra:

```bash
pip install powermcp[psse]
pip install powermcp[andes,opendss]
pip install powermcp[opensource]
pip install powermcp[all]
```

### Set up with the interactive installer

```bash
powermcp install
```

The wizard lets you pick tools, captures local paths for closed-source tools where needed, installs the selected extras, and writes MCP client configuration. Use `--dry-run` to preview changes or `--yes` for a non-interactive core install.

### CLI commands

| Command | Description |
|---|---|
| `powermcp install` | Setup wizard |
| `powermcp run <tool>` | Launch a server over stdio |
| `powermcp list` | List available tools |
| `powermcp doctor` | Check dependencies and configured paths |
| `powermcp config show` / `config set <tool>.<key> <path>` | Inspect or set local software paths |

### Closed-source / EXE-based tools

These tools wrap commercial or locally-installed software. Local paths are stored in `~/.powermcp/config.toml` when needed.

### Case compilation between servers (PowerIO)

PowerMCP uses PowerIO as a core case-conversion substrate. Its canonical JSON transport lets cases move between supported backends with structured diagnostics and fidelity warnings.

## Testing with your LLMs

All MCPs should be tested via an MCP client before submitting a PR to ensure consistency.

### Security Audit testing

```bash
pytest SecurityAudit/tests/test_security_audit.py -v
```

The Security Audit tests cover deterministic severity/ranking, risk classification, report generation, input-limit validation, and stable JSON-friendly contingency records without requiring a commercial simulator.

## 📚 Documentation

For detailed documentation about MCP, please visit:
- [Model Context Protocol documentation](https://modelcontextprotocol.io/introduction)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Other General MCP Servers](https://smithery.ai/)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://power-agent.github.io/) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

### Core Team
- [Qian Zhang](https://www.linkedin.com/in/qian-zhang-75323111b/), [Steven Black](https://www.linkedin.com/in/steven-black-09322b31/), [Paulo Radatz](https://www.linkedin.com/in/pauloradatz/), [Andrea Pomarico](https://www.linkedin.com/in/andrea-pomarico-2695a2218/), [Muhy Eddin Za’ter](https://scholar.google.com/citations?user=_IFFYFAAAAAJ&hl=en), [Luan Lopes](https://www.linkedin.com/in/luanlopes/), [Stephen Jenkins](https://www.linkedin.com/in/stephenjenkins2/), [Maanas Goel](https://www.linkedin.com/in/maanas-goel/), [Shen Wang](https://www.linkedin.com/in/swang16/), [Drew Gray](https://www.linkedin.com/in/drew-gray-b09ba426/), [Samuel Talkington](https://samueltalkington.com/)

### Special Thanks
- All contributors who help make this project better
- [The Power and AI Initiative (PAI) at Harvard SEAS](https://pai.seas.harvard.edu/)
