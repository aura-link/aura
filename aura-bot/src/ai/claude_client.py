"""Wrapper del Anthropic SDK para Claude AI con tool use."""

import anthropic
from src.ai.system_prompt import build_system_prompt
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor
from src.utils.logger import log
from src import config


class ClaudeClient:
    def __init__(self, tool_executor: ToolExecutor):
        self.tool_executor = tool_executor
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        return self._client

    @property
    def enabled(self) -> bool:
        return bool(config.ANTHROPIC_API_KEY)

    async def chat(
        self,
        user_message: str,
        history: list[dict],
        role: str = "guest",
        client_name: str | None = None,
        client_id: str | None = None,
        user_context: dict | None = None,
    ) -> str:
        """Envia mensaje a Claude con tool use y retorna respuesta final."""
        if not self.enabled:
            return (
                "Lo siento, el asistente de IA no esta disponible en este momento.\n"
                "Usa /help para ver los comandos disponibles."
            )

        system = build_system_prompt(role=role, client_name=client_name, client_id=client_id)

        # Build messages from history
        messages = []
        for h in history[-18:]:  # Keep last 18 for context window
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        # Determine which tools to offer based on role
        available_tools = self._tools_for_role(role)

        try:
            response = await self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1024,
                system=system,
                messages=messages,
                tools=available_tools,
            )

            # Handle tool use loop (max 5 iterations)
            iterations = 0
            while response.stop_reason == "tool_use" and iterations < 5:
                iterations += 1

                # Process all tool calls in the response
                tool_results = []
                assistant_content = response.content

                for block in response.content:
                    if block.type == "tool_use":
                        log.info("Claude tool call: %s(%s)", block.name, block.input)
                        result = await self.tool_executor.execute(
                            block.name, block.input, user_context
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                # Add assistant response and tool results to messages
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})

                # Call Claude again with tool results
                response = await self.client.messages.create(
                    model=config.CLAUDE_MODEL,
                    max_tokens=1024,
                    system=system,
                    messages=messages,
                    tools=available_tools,
                )

            # Extract final text response
            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)

            return "\n".join(text_parts) or "No pude generar una respuesta."

        except anthropic.APIError as e:
            log.error("Claude API error: %s", e)
            return (
                "Lo siento, tuve un problema al procesar tu mensaje.\n"
                "Intenta de nuevo o usa /help para ver los comandos disponibles."
            )
        except Exception as e:
            log.error("Claude unexpected error: %s", e)
            return "Ocurrio un error inesperado. Por favor intenta de nuevo."

    def _tools_for_role(self, role: str) -> list[dict]:
        """Filtra herramientas segun el rol."""
        admin_only = {"consultar_estado_red", "buscar_cliente_por_nombre",
                      "listar_dispositivos_offline"}
        customer_tools = {"consultar_saldo_cliente", "consultar_servicio_cliente",
                          "diagnosticar_conexion_cliente", "escalar_a_soporte"}
        shared_tools = {"consultar_sesion_pppoe", "ping_dispositivo"}

        if role == "admin":
            allowed = admin_only | customer_tools | shared_tools
        elif role == "customer":
            allowed = customer_tools | shared_tools
        else:
            allowed = set()  # Guests don't get tools

        return [t for t in TOOLS if t["name"] in allowed]
