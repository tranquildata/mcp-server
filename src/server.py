# Copyright (c) 2025-2026, Tranquil Data, Inc. All rights reserved.

import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

async def main():
	load_dotenv()

	config = {
		"mcpServers": {
			"local-mcp": {
      			"command": "python",
      			"args": [
        			"tools/hub.py"
                ]
    		}
		}
	}

	client = MCPClient.from_dict(config)
	llm = ChatOpenAI(model="gpt-4.1")
	agent = MCPAgent(llm=llm, client=client, max_steps=10)

	result = await agent.run(
        "I am talking with the user alice@example.com and would like to share with her the perscriptions for her children"
	)
	print(f"\nResult: {result}")

if __name__ == "__main__":
	asyncio.run(main())
