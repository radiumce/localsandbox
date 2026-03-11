import logging
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from server.server import get_or_create_wrapper
from wrapper.models import SandboxFlavor

logger = logging.getLogger(__name__)

async def health_check(request: Request):
    """Health check probe endpoint for the CLI client and monitoring."""
    return JSONResponse({"status": "healthy", "version": "1.0.0"})

async def execute_code(request: Request):
    """Execute code endpoint."""
    try:
        data = await request.json()
        wrapper = await get_or_create_wrapper()
        
        flavor_val = data.get("flavor")
        if flavor_val is None:
            flavor_enum = wrapper.get_config().default_flavor
        else:
            flavor_enum = SandboxFlavor(flavor_val)
            
        result = await wrapper.execute_code(
            code=data.get("code", ""),
            template=data.get("template", "python"),
            session_id=data.get("session_id"),
            flavor=flavor_enum,
            timeout=data.get("timeout")
        )
        
        return JSONResponse({
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "session_id": result.session_id,
            "execution_time_ms": result.execution_time_ms,
            "template": getattr(result, "template", None),
            "exit_code": getattr(result, "exit_code", None)
        })
    except Exception as e:
        logger.error(f"API execute_code failed: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

async def execute_command(request: Request):
    """Execute command endpoint."""
    try:
        data = await request.json()
        wrapper = await get_or_create_wrapper()
        
        flavor_val = data.get("flavor")
        if flavor_val is None:
            flavor_enum = wrapper.get_config().default_flavor
        else:
            flavor_enum = SandboxFlavor(flavor_val)
            
        # Optional custom command string or fallback to sh -c "command"
        command_str = data.get("command", "")
        
        result = await wrapper.execute_command(
            command="sh",
            args=["-c", command_str],
            template=data.get("template", "python"),
            session_id=data.get("session_id"),
            flavor=flavor_enum,
            timeout=data.get("timeout")
        )
        
        return JSONResponse({
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "session_id": result.session_id,
            "execution_time_ms": result.execution_time_ms,
            "template": getattr(result, "template", None),
            "exit_code": getattr(result, "exit_code", None)
        })
    except Exception as e:
        logger.error(f"API execute_command failed: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

async def get_sessions(request: Request):
    """List sessions endpoint."""
    try:
        wrapper = await get_or_create_wrapper()
        session_id = request.query_params.get("session_id")
        sessions = await wrapper.get_sessions(session_id)
        
        sessions_data = []
        for s in sessions:
            sessions_data.append({
                "session_id": s.session_id,
                "template": s.template,
                "flavor": s.flavor.value,
                "status": s.status.value,
                "created_at": s.created_at.isoformat(),
                "last_accessed": s.last_accessed.isoformat(),
                "namespace": s.namespace,
                "sandbox_name": s.sandbox_name
            })
            
        return JSONResponse({
            "success": True,
            "sessions": sessions_data
        })
    except Exception as e:
        logger.error(f"API get_sessions failed: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

async def stop_session(request: Request):
    """Stop session endpoint."""
    try:
        session_id = request.path_params.get("session_id")
        if not session_id:
            return JSONResponse({"success": False, "error": "Missing session_id"}, status_code=400)
            
        wrapper = await get_or_create_wrapper()
        success = await wrapper.stop_session(session_id)
        
        return JSONResponse({
            "success": True,
            "stopped": success,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"API stop_session failed: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

async def get_volumes(request: Request):
    """List volume mappings endpoint."""
    try:
        wrapper = await get_or_create_wrapper()
        mappings = await wrapper.get_volume_mappings()
        
        volumes_data = []
        for m in mappings:
            volumes_data.append({
                "host_path": m.host_path,
                "sandbox_path": m.sandbox_path
            })
            
        return JSONResponse({
            "success": True,
            "volumes": volumes_data
        })
    except Exception as e:
        logger.error(f"API get_volumes failed: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

async def pin_sandbox(request: Request):
    """Pin sandbox endpoint."""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        pinned_name = data.get("pinned_name")
        if not session_id or not pinned_name:
            return JSONResponse({"success": False, "error": "Missing session_id or pinned_name"}, status_code=400)
            
        wrapper = await get_or_create_wrapper()
        result = await wrapper.pin_session(session_id, pinned_name)
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        logger.error(f"API pin_sandbox failed: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

async def attach_sandbox(request: Request):
    """Attach sandbox by name endpoint."""
    try:
        data = await request.json()
        pinned_name = data.get("pinned_name")
        if not pinned_name:
            return JSONResponse({"success": False, "error": "Missing pinned_name"}, status_code=400)
            
        wrapper = await get_or_create_wrapper()
        session_id = await wrapper.attach_to_pinned_sandbox(pinned_name)
        return JSONResponse({"success": True, "session_id": session_id})
    except Exception as e:
        logger.error(f"API attach_sandbox failed: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

api_routes = [
    Route("/health", health_check, methods=["GET"]),
    Route("/api/execute/code", execute_code, methods=["POST"]),
    Route("/api/execute/command", execute_command, methods=["POST"]),
    Route("/api/sessions", get_sessions, methods=["GET"]),
    Route("/api/sessions/{session_id}/stop", stop_session, methods=["POST"]),
    Route("/api/volumes", get_volumes, methods=["GET"]),
    Route("/api/sandbox/pin", pin_sandbox, methods=["POST"]),
    Route("/api/sandbox/attach", attach_sandbox, methods=["POST"]),
]
