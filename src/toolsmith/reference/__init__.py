"""The reference target: a codebase-intelligence MCP server to optimize against.

This package is a test subject, not part of the optimizer. Nothing outside it
may import from it; the benchmark, proxy, and optimizer reach it only over the
MCP protocol, exactly as they would a third-party server. A test enforces this.
"""
