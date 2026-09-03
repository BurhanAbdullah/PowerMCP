# PowerMCP ⚡

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

PowerMCP is an open-source collection of MCP servers for power system software like PowerWorld and OpenDSS. These tools enable LLMs to directly interact with power system applications, facilitating intelligent coordination, simulation, and control in the energy domain.

## 🌟 What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/introduction) (MCP) is a revolutionary standard that enables AI applications to seamlessly connect with various external tools. Think of MCP as a universal adapter for AI applications, similar to what USB-C is for physical devices. It provides:

- Standardized connections to power system software and data sources
- Secure and efficient data exchange between AI agents and power systems
- Reusable components for building intelligent power system applications
- Interoperability between different AI models and power system tools

## 🛡️ Cross-Platform Security Audit

PowerMCP now includes a backend-neutral **Security Audit MCP server** for standardized base-case and N-1 screening across pandapower and PyPSA. It independently evaluates contingencies, detects voltage/thermal violations, treats non-convergence as critical, ranks contingencies with a deterministic 0–10 severity score, and can render a concise Markdown engineering report.

```bash
python SecurityAudit/security_audit_mcp.py
```

The detailed solver-specific servers remain available for PowerWorld, pandapower, PyPSA, PSSE, PSLF, ANDES, OpenDSS, and other integrations. The Security Audit layer is intended for agent workflows that need a common screening result before deeper backend-specific analysis.

## 🤝 Our Community Vision

We're building an open-source community focused on accelerating AI adoption in the power domain through MCP. Our goals are:

- **Collaboration**: Bring together power system experts, AI researchers, and software developers
- **Innovation**: Create and share MCP servers for various power system software and tools
- **Education**: Provide resources and examples for implementing AI in power systems
- **Standardization**: Develop best practices for AI integration in the energy sector

## 🚀 Getting Started with MCP

### 📖 Quick start

> **🚀 New to PowerMCP? Start here!** The recommended way to get started is the `powermcp` package and its installer (see the **Installation** section below).

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
* **Clients** maintain 1:1 connections with servers, inside the host application
* **Servers** provide context, tools, and prompts to clients

Check out these helpful tutorials to get started with MCP:

- [**Getting Started with MCP**](https://modelcontextprotocol.io/introduction)
- [**Core Architecture**](https://modelcontextprotocol.io/docs/concepts/architecture)
- [**Building Your First MCP Server**](https://modelcontextprotocol.io/docs/develop/build-server)
- [**Anthropic MCP Tutorial**](https://docs.claude.com/en/docs/mcp)
- [**Cursor MCP Tutorial**](https://cursor.com/docs/context/mcp)
- [**Other Protocol**](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)

## 📦 Installation

PowerMCP installs as a single Python package with an interactive CLI. Python 3.10+ is required.

```bash
pip install powermcp
```

The base install includes the open-source engines that need no extra setup — **pandapower**, **PyPSA**, and **PowerIO**. Other tools are opt-in via extras.

```bash
pip install powermcp[psse]
pip install powermcp[andes,opendss]
pip install powermcp[opensource]
pip install powermcp[all]
```

### Case compilation between servers (PowerIO)

PowerMCP uses PowerIO as the canonical exchange substrate for cross-server case conversion and matrix construction. Parse a case once, pass its JSON transport between tools, and materialize runtime files only when a backend requires them.

## 🧪 Testing

The Security Audit unit tests can be run with:

```bash
pytest SecurityAudit/tests/test_security_audit.py -v
```

The existing backend-specific test suites remain unchanged.

## 📚 Documentation

For detailed documentation about MCP, please visit:
- [Model Context Protocol documentation](https://modelcontextprotocol.io/introduction)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://power-agent.github.io/) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

### Core Team
- Qian Zhang, Steven Black, Paulo Radatz, Andrea Pomarico, Muhy Eddin Za’ter, Luan Lopes dos Santos, Stephen Jenkins, Maanas Goel, Shen Wang, Drew Gray, Samuel Talkington

### Special Thanks
- All contributors who help make this project better
- The Power and AI Initiative (PAI) at Harvard SEAS
