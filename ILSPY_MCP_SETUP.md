# ILSpy MCP Server Setup Guide

## Installation Summary

### Prerequisites Installed
- **.NET SDK**: 10.0.201
- **ILSpy CLI (ilspycmd)**: 10.0.0.8330
- **Python**: 3.12.0
- **ilspy-mcp-server**: 0.1.1

### Installation Commands
```bash
# Install ILSpy CLI
dotnet tool install --global ilspycmd

# Install ILSpy MCP Server
pip install ilspy-mcp-server
```

## MCP Configuration

### Cursor IDE
Add to Cursor settings:
```json
{
  "mcpServers": {
    "ilspy": {
      "command": "python",
      "args": ["-m", "ilspy_mcp_server.server"],
      "env": {
        "LOGLEVEL": "INFO"
      }
    }
  }
}
```

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ilspy": {
      "command": "python",
      "args": ["-m", "ilspy_mcp_server.server"],
      "env": {
        "LOGLEVEL": "INFO"
      }
    }
  }
}
```

### Windsurf
Add to Windsurf MCP configuration with same format.

## Available MCP Tools

### 1. decompile_assembly
Decompile .NET assembly to C# source code.

**Parameters:**
- `assembly_path` (required): Path to .NET assembly file
- `output_dir` (optional): Output directory for decompiled files
- `type_name` (optional): Specific type to decompile
- `language_version` (optional): C# language version (default: "Latest")
- `create_project` (optional): Create compilable project structure
- `show_il_code` (optional): Show IL code instead of C#
- `remove_dead_code` (optional): Remove dead code during decompilation
- `nested_directories` (optional): Use nested directories for namespaces

**Example:**
```json
{
  "name": "decompile_assembly",
  "arguments": {
    "assembly_path": "Xeno-v1.3.30/XenoUI.dll",
    "type_name": "XenoUI.MainWindow",
    "language_version": "CSharp10_0"
  }
}
```

### 2. list_types
List types in a .NET assembly.

**Parameters:**
- `assembly_path` (required): Path to .NET assembly file
- `entity_types` (optional): Array of entity types ("c", "i", "s", "d", "e")
  - c = class
  - i = interface
  - s = struct
  - d = delegate
  - e = enum

**Example:**
```json
{
  "name": "list_types",
  "arguments": {
    "assembly_path": "Xeno-v1.3.30/XenoUI.dll",
    "entity_types": ["c", "i"]
  }
}
```

### 3. generate_diagrammer
Generate interactive HTML diagrammer for assembly structure.

**Parameters:**
- `assembly_path` (required): Path to .NET assembly file
- `output_dir` (optional): Output directory for diagrammer
- `include_pattern` (optional): Regex pattern for types to include
- `exclude_pattern` (optional): Regex pattern for types to exclude

**Example:**
```json
{
  "name": "generate_diagrammer",
  "arguments": {
    "assembly_path": "Xeno-v1.3.30/XenoUI.dll",
    "output_dir": "./diagrammer"
  }
}
```

### 4. get_assembly_info
Get basic information about an assembly.

**Parameters:**
- `assembly_path` (required): Path to .NET assembly file

**Example:**
```json
{
  "name": "get_assembly_info",
  "arguments": {
    "assembly_path": "Xeno-v1.3.30/XenoUI.dll"
  }
}
```

## Available Prompts

### 1. analyze_assembly
Analyze a .NET assembly and provide insights about its structure.

### 2. decompile_and_explain
Decompile a specific type and provide explanation of its functionality.

## Testing with Workspace DLLs

### Valid Assembly: XenoUI.dll
```bash
# List classes in XenoUI.dll
ilspycmd -l c "Xeno-v1.3.30/XenoUI.dll"

# Output:
# Class XenoUI.App
# Class XenoUI.ClientsWindow
# Class XenoUI.MainWindow
# Class XenoUI.ScriptsWindow
# Class XenoUI.SettingsWindow
# ... (23 classes total)
```

### Invalid Assembly: Xeno.dll
- Xeno.dll is not a .NET assembly (PE file without managed metadata)
- Cannot be decompiled with ILSpy

## Architecture

- **Transport**: stdio
- **Backend**: ILSpy (via ilspycmd)
- **Language**: Python 3.8+
- **Headless**: No UI required
- **Compatible**: Cursor IDE, Claude Desktop, Windsurf MCP

## Troubleshooting

### MCP Server Not Starting
```bash
# Test MCP server directly
python -m ilspy_mcp_server.server
```

### ILSpy CLI Not Found
```bash
# Verify installation
dotnet tool list --global

# Reinstall if needed
dotnet tool install --global ilspycmd
```

### Assembly Not Supported
- Verify the file is a valid .NET assembly
- Use `ilspycmd <file.dll>` to test directly
- Some native DLLs cannot be decompiled

## Notes

- All outputs are JSON structured
- Fully scriptable and headless
- No GUI tools required
- Production-ready setup
