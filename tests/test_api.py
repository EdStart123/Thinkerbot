import runpy
import sys
import types
from fastapi.testclient import TestClient
import pytest


def load_app():
    # Create a stub openai module to avoid network calls
    stub = types.ModuleType('openai')

    class StubOpenAI:
        def __init__(self, *args, **kwargs):
            self.created = 0
            self.messages = {}
            self.beta = types.SimpleNamespace(
                threads=types.SimpleNamespace(
                    create=self._create_thread,
                    messages=types.SimpleNamespace(
                        create=self._create_message,
                        list=self._list_messages,
                    ),
                    runs=types.SimpleNamespace(
                        create=self._create_run,
                        retrieve=self._retrieve_run,
                    ),
                )
            )

        def _create_thread(self):
            self.created += 1
            tid = f"thread_{self.created}"
            self.messages[tid] = []
            return types.SimpleNamespace(id=tid)

        def _create_message(self, thread_id, role, content):
            self.messages.setdefault(thread_id, []).append(
                types.SimpleNamespace(
                    role=role,
                    content=[types.SimpleNamespace(text=types.SimpleNamespace(value=content))],
                )
            )

        def _create_run(self, thread_id, assistant_id):
            return types.SimpleNamespace(id="run_1")

        def _retrieve_run(self, thread_id, run_id):
            return types.SimpleNamespace(status="completed")

        def _list_messages(self, thread_id):
            # Return a summary message
            return types.SimpleNamespace(
                data=[
                    types.SimpleNamespace(
                        role="assistant",
                        content=[types.SimpleNamespace(text=types.SimpleNamespace(value="summary text"))],
                    )
                ]
            )

    stub.OpenAI = StubOpenAI
    sys.modules['openai'] = stub

    mod_globals = runpy.run_path('main-2')
    app = mod_globals['app']
    return app, mod_globals


@pytest.fixture
def client():
    app, globals_dict = load_app()
    yield TestClient(app)
    sys.modules.pop('openai', None)


def test_health_endpoint(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {"status": "Thinkering Assistant is live!"}


def test_log_and_summary(client):
    response = client.post('/log', json={'fellow_name': 'alice', 'entry': 'hello'})
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    thread_id = data['thread_id']

    summary_resp = client.get('/summary/alice')
    assert summary_resp.status_code == 200
    assert summary_resp.json() == {"summary": "summary text"}
