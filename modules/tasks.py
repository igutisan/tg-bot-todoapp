"""
Handles all interactions with the NestJS API.
"""
import requests
from config import NESTJS_API_BASE_URL, FUZZY_MATCH_THRESHOLD
from fuzzywuzzy import process

def get_auth_headers(token: str) -> dict:
    """Obtiene las cabeceras de autenticación para un token"""
    return {"Authorization": f"Bearer {token}"}

async def get_user_tasks_from_nestjs(token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.get(f"{NESTJS_API_BASE_URL}/tasks/my-tasks", headers=headers)
        response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener tareas de NestJS: {e}")
        return None

async def complete_task_in_nestjs(task_id: str, token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.patch(f"{NESTJS_API_BASE_URL}/tasks/{task_id}", 
                                json={"status": "completed"}, 
                                headers=headers)
        response.raise_for_status()
        return response.json() # Debería devolver la tarea actualizada
    except requests.exceptions.RequestException as e:
        print(f"Error al completar tarea {task_id} en NestJS: {e}")
        return None
    
async def process_task_in_nestjs(task_id: str, token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.patch(f"{NESTJS_API_BASE_URL}/tasks/{task_id}", 
                                json={"status": "in_progress"}, 
                                headers=headers)
        response.raise_for_status()
        return response.json() # Debería devolver la tarea actualizada
    except requests.exceptions.RequestException as e:
        print(f"Error al actualizar la tarea {task_id} en NestJS: {e}")
        return None

async def create_task_in_nestjs(task_name: str, token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.post(f"{NESTJS_API_BASE_URL}/tasks", 
                               json={"title": task_name}, 
                               headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al crear tarea '{task_name}' en NestJS: {e}")
        return None

async def delete_task_in_nestjs(task_id: str, token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.delete(f"{NESTJS_API_BASE_URL}/tasks/{task_id}", headers=headers)
        response.raise_for_status()
        return True  # Si llegamos aquí, la eliminación fue exitosa
    except requests.exceptions.RequestException as e:
        print(f"Error al eliminar tarea {task_id} en NestJS: {e}")
        return None

def find_most_similar_task(search_term: str, tasks: list[dict]) -> tuple[dict | None, int]:
    """
    Busca la tarea más similar en una lista de tareas.
    Retorna la tarea (dict) y el puntaje de similitud.
    """
    if not tasks or 'data' not in tasks or not tasks['data']:
        return None, 0
    
    tasks_data = tasks['data']

    task_names = {}
    for task in tasks_data:
        if isinstance(task, dict) and 'title' in task:
            task_names[task['title']] = task
    
    
    names_list = list(task_names.keys())
    
    # Buscar la mejor coincidencia
    try:
        best_match_name, score = process.extractOne(search_term, names_list)
        
        if score >= FUZZY_MATCH_THRESHOLD:
            return task_names[best_match_name], score
    except Exception as e:
        print(f"Error en la búsqueda: {e}")
        return None, 0
    
    return None, 0
