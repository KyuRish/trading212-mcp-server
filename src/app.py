from mcp.server.fastmcp import FastMCP
from dotenv import find_dotenv, load_dotenv
from api.client import Trading212Client

load_dotenv(find_dotenv())

mcp = FastMCP(
    name="trading212",
    dependencies=["pydantic"],
)

client = Trading212Client()
