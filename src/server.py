import os
from dotenv import load_dotenv, find_dotenv

from app import mcp
from tools import *
from prompts import *
from resources import *

load_dotenv(find_dotenv())

if __name__ == "__main__":
    mcp.run(transport=os.getenv('TRANSPORT', 'stdio'))
