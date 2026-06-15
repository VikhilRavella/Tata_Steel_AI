import httpx
import json
import asyncio
OLLAMA_API_GENERATE = 'http://localhost:11434/api/generate'
OLLAMA_API_EMBED = 'http://localhost:11434/api/embeddings'
SUPPORTED_MODELS = ['qwen2.5-coder:7b', 'mistral', 'llama3', 'qwen', 'deepseek', 'gemma']

async def generate_completion_stream(prompt: str, system: str=None, model: str='qwen2.5-coder:7b', on_complete=None):
    """
    Streams a response from Ollama using the requested model.
    Yields SSE formatted strings.
    """
    payload = {'model': model, 'prompt': prompt, 'stream': True}
    if system:
        payload['system'] = system
    print('OLLAMA PAYLOAD KEYS:', list(payload.keys()))
    print('OLLAMA PAYLOAD MODEL:', payload.get('model'))
    print('OLLAMA PAYLOAD STREAM:', payload.get('stream'))
    full_response = ''
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream('POST', OLLAMA_API_GENERATE, json=payload) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    yield f"data: {json.dumps({'error': f'Ollama failed {response.status_code}: {error_body.decode()}'})}\n\n"
                    return
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get('response', '')
                            if token:
                                full_response += token
                                yield f"data: {json.dumps({'token': token})}\n\n"
                            if data.get('done', False):
                                yield 'data: [DONE]\n\n'
                                break
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        print(f'Ollama stream error: {e}')
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield 'data: [DONE]\n\n'
    if on_complete and full_response:
        try:
            await on_complete(full_response)
        except Exception as e:
            print(f'on_complete error: {e}')

async def generate_completion_sync(prompt: str, system: str=None, model: str='qwen2.5-coder:7b') -> str:
    """
    Generates a synchronous response from Ollama.
    """
    payload = {'model': model, 'prompt': prompt, 'stream': False}
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(OLLAMA_API_GENERATE, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            return f'Error: Status {response.status_code}'
    except Exception as e:
        print(f'Ollama sync error: {e}')
        return f'Error connecting to Ollama: {str(e)}'