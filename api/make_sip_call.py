from livekit import api
import json
import asyncio
import os
from dotenv import load_dotenv

load_dotenv("../.env")

room_name = "call-"
agent_name = "outbound-caller"

livekit_url = os.getenv("LIVEKIT_URL")
livekit_api_key = os.getenv("LIVEKIT_API_KEY")
livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

async def explicit_dispatch_call(goal, context=""):
    lkapi = api.LiveKitAPI(
        url=livekit_url,
        api_key=livekit_api_key,
        api_secret=livekit_api_secret,
    )
    metadata = {
        "phone_number": "+13109388969",
        "transfer_to": "+13105825023",
        "goal": goal,
        "context": context
    }

    dispatch = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name=agent_name, room=room_name, metadata=json.dumps(metadata)
        )
    )
    print("created dispatch", dispatch)

    dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
    print(f"there are {len(dispatches)} dispatches in {room_name}")
    await lkapi.aclose()

asyncio.run(main())