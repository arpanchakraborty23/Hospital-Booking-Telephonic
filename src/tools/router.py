from livekit.agents import function_tool, RunContext

# simple in-memory session state
class InMemoryState:
    def __init__(self):
        self.slots = {}

    def set(self, k, v):
        self.slots[k] = v

    def get(self, k, default=None):
        return self.slots.get(k, default)

state = InMemoryState()
state.set("loaded_tool_groups", [])  # track loaded groups

@function_tool()
async def tool_router(context: RunContext, action: str, target: str = ""):
    """
    Manage which tool groups the agent has loaded. Always call this first
    to check what tools are available before attempting a user request.

    action: "check_tools", "load", or "cleanup"
    target: required when action == "load" (appointments, directory, communication)
    """
    # helper to get router toolset and current agent tools
    from .hospital_tools import HospitalTools
    router_ts = HospitalTools.get_toolset("router")

    if action == "check_tools":
        loaded = state.get("loaded_tool_groups", [])
        loaded_msg = loaded if loaded else "none (router only)"
        return (
            f"Currently loaded tool groups: {loaded_msg}. "
            f"Call tool_router(action='load', target='appointments') for booking, "
            f"'directory' for info lookups, or 'communication' for confirmations. "
            f"Call tool_router(action='cleanup') when done."
        )

    if action == "load":
        if target not in ("appointments", "directory", "communication"):
            return (
                f"Unknown group '{target}'. Valid targets: appointments, directory, communication."
            )

        new_ts = HospitalTools.get_toolset(target)

        # Build the new tools list, preserving router and existing non-router tools if desired
        # Here we ensure router + new_ts only (replace other extras)
        try:
            await context.agent.update_tools([router_ts, new_ts])
        except Exception as e:
            return {"error": f"Failed to load tool group '{target}': {e}"}

        # update in-memory tracking
        state.set("loaded_tool_groups", [target])

        # inject a short assistant/system message so the LLM knows available tools changed
        try:
            await context.add_system_message(f"Available tools: router, {target}")
        except Exception:
            # fallback to plain text if add_system_message is unavailable
            await context.send_text(f"Available tools: router, {target}")

        return f"Tool group '{target}' loaded. Use its tools now, then call tool_router(action='cleanup') to unload."

    if action == "cleanup":
        try:
            await context.agent.update_tools([router_ts])
        except Exception as e:
            return {"error": f"Failed to cleanup tools: {e}"}

        state.set("loaded_tool_groups", [])
        try:
            await context.add_system_message("Available tools: router")
        except Exception:
            await context.send_text("Available tools: router")

        return "Extra tools removed. Only router remains. How can I help you?"

    return f"Unknown action '{action}'. Valid: check_tools, load, cleanup."