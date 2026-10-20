from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from langfuse import get_client

_telemetry_initialized = False

def init_telemetry():
    """
    Initializes OpenInference instrumentation for OpenAI Agents and
    connects to the Langfuse distributed tracing telemetry server.
    """
    global _telemetry_initialized
    if _telemetry_initialized:
        return
    
    # Instrument OpenAI Agents SDK
    try:
        OpenAIAgentsInstrumentor().instrument()
    except Exception as e:
        print(f"⚠️ OpenInference instrumentation notice: {e}")
        
    # Initialize Langfuse client
    try:
        langfuse = get_client()
        if langfuse.auth_check():
            print("✅ Langfuse telemetry client authenticated and ready.")
        else:
            print("❌ Langfuse authentication failed. Check Langfuse credentials.")
    except Exception as e:
        print(f"⚠️ Langfuse connection notice: {e}. Tracing will proceed locally/natively.")
        
    _telemetry_initialized = True
