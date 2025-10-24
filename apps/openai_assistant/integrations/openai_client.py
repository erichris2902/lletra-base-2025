import time
from django.conf import settings
from openai import OpenAI


class OpenAIClient:
    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.client = OpenAI(api_key=api_key)

    # ======================
    # ASSISTANTS
    # ======================
    def create_assistant(self, payload):
        return self.client.beta.assistants.create(**payload)

    def update_assistant(self, assistant_id, payload):
        return self.client.beta.assistants.update(assistant_id=assistant_id, **payload)

    def delete_assistant(self, assistant_id):
        return self.client.beta.assistants.delete(assistant_id=assistant_id)

    # ======================
    # THREADS / MESSAGES
    # ======================
    def create_thread(self):
        return self.client.beta.threads.create()

    def add_message(self, thread_id, role, content):
        return self.client.beta.threads.messages.create(
            thread_id=thread_id, role=role, content=content
        )

    def list_messages(self, thread_id, limit=20):
        return self.client.beta.threads.messages.list(thread_id=thread_id, limit=limit)

    # ======================
    # RUNS
    # ======================
    def create_run(self, thread_id, assistant_id):
        return self.client.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=assistant_id
        )

    def retrieve_run(self, thread_id, run_id):
        return self.client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )

    def list_runs(self, thread_id):
        return self.client.beta.threads.runs.list(thread_id=thread_id)

    def cancel_run(self, thread_id, run_id):
        return self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run_id)

    def submit_tool_outputs(self, thread_id, run_id, tool_outputs):
        return self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id, run_id=run_id, tool_outputs=tool_outputs
        )

    # ======================
    # HELPERS
    # ======================
    def wait_for_run_completion(self, thread_id, run_id, timeout: int = 300):
        start_time = time.time()
        while time.time() - start_time < timeout:
            run = self.retrieve_run(thread_id, run_id)
            print(f"[OpenAIClient] Run status: {run.status}")

            if run.status in ["completed", "failed", "cancelled", "expired"]:
                return run
            if run.status == "requires_action":
                return run

            time.sleep(1)

        self.cancel_run(thread_id, run_id)
        raise TimeoutError(f"Run {run_id} timed out after {timeout} seconds")

    def cancel_active_runs(self, thread_id: str, wait_until_cleared: bool = True, timeout: int = 15):
        try:
            runs = self.client.beta.threads.runs.list(thread_id=thread_id)
            active_runs = [r for r in runs.data if r.status in ["in_progress", "queued"]]

            for run in active_runs:
                self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                print(f"[OpenAIClient] 🛑 Run cancelado: {run.id}")

            if wait_until_cleared:
                import time
                start = time.time()
                while time.time() - start < timeout:
                    runs = self.client.beta.threads.runs.list(thread_id=thread_id)
                    still_active = [r for r in runs.data if r.status in ["in_progress", "queued"]]
                    if not still_active:
                        print(f"[OpenAIClient] ✅ Runs completamente limpiados en {thread_id}")
                        return
                    time.sleep(1.5)
                print(f"[OpenAIClient] ⚠️ Timeout esperando cancelación total de runs en {thread_id}")
        except Exception as e:
            print(f"[OpenAIClient] Error al cancelar runs activos: {e}")

