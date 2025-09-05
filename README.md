# Lineagentic-DPC

Lineagentic-DPC is an MCP server concentrating on composing step of building data products. It solves challenges metadata shift left governance in data mesh.

## Status

| Component | Status | Version | Description |
|-----------|--------|---------|-------------|
| **Core MCP Server** | 🟢 Active | 0.6.2 | Main MCP server for data product composition |
| **Scoping Agent** | 🟢 Active | 0.6.2 | Agent for data product scoping and requirements gathering |
| **Data Contract Agent** | 🟢 Active | 0.6.2 | Agent for data contract definition and validation |
| **Gradio Interface** | 🟢 Active | 0.6.2 | Web UI for interactive data product composition |
| **Data Catalog Agent** | ⚪ Backlog | 0.6.2 | Agent for data catalog definition and validation |
| **Deployment Agent** | ⚪ Backlog | 0.6.2 | Deployment composition of data products |
| **Data Quality Port Agent** | ⚪ Backlog | 0.6.2 | Data quality port for data products |
| **Data Observability Port Agent** | ⚪ Backlog | 0.6.2 | Data observability port for data products |



**Legend:** 🟢 Active/Ready | 🟡 In Progress | ⚪ Backlog

## Features

- MCP server for composing data products
- Agentic ai chat based approach for composing data products
- Governance shift left in practice
- Data mesh metadata shift left governance
- Data product composition

## How it works

MCP server is a server that provides a set of tools to the agent. The agent can use the tools to compose data products.
The tools that current version of Lineagentic-DPC MCP server provides are:

| Agent | Purpose | Description |
|-------|---------|-------------|
| **Scoping Agent** | Data Product Scoping | Captures product scope: name, domain, owner, purpose, and upstream data sources. Guides users through structured scoping process. |
| **Data Contract Agent** | Data Contract Definition | Defines data contracts with output ports, field schemas, sink locations, and freshness requirements. Handles field normalization and validation. |
| **Data Catalog Agent** | Data Catalog Management | *Planned* - Will manage data catalog entries, metadata, and lineage tracking for data products. |
| **Deployment Agent** | Data Product Deployment | *Planned* - Will handle deployment composition and orchestration of data products across different environments. |
| **Data Quality Port Agent** | Data Quality Management | *Planned* - Will define and manage data quality ports, validation rules, and quality metrics for data products. |
| **Data Observability Port Agent** | Data Observability | *Planned* - Will set up observability ports for monitoring, alerting, and tracking data product health and performance. |



## Quick Start

You can use MCP server either by normal way ot you can use a statefull agent with a MCP server which is developed on top of the MCP server. To run the chat either you can use gradio which have interface or you can run in command line chat by following command:

```bash
make run-chat
```

## MCP Server Configuration

To run the `dp_composer_server`, you need to configure it as an MCP server in your client configuration. Add the following configuration to your MCP client settings (e.g., Claude Desktop configuration):

```json
{
  "mcpServers": {
    "demo": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/ali.shamsaddinlou/Documents/codes/lineagentic-dpc/dp_composer_server",
        "run",
        "-m"
        "dp_composer-server"
      ]
    }
  }
}
```

This configuration allows the MCP client to connect to and use the data product composition tools provided by the Lineagentic-DPC server.
