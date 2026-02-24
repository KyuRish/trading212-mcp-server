from mcp.server.fastmcp import FastMCP
from dotenv import find_dotenv, load_dotenv
from trading212_mcp_server.api.client import T212Client

load_dotenv(find_dotenv())

mcp = FastMCP(
    name="trading212",
    dependencies=["pydantic"],
)

client = T212Client()
