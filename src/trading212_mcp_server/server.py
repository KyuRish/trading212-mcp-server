import os

from trading212_mcp_server.app import mcp  # noqa: F401
import trading212_mcp_server.tools  # noqa: F401
import trading212_mcp_server.prompts  # noqa: F401


def main():
    mcp.run(transport=os.getenv('TRANSPORT', 'stdio'))


if __name__ == "__main__":
    main()
