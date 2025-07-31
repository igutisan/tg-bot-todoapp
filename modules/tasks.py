"""
Handles all interactions with the NestJS API.
"""
import requests
from config import NESTJS_API_BASE_URL, FUZZY_MATCH_THRESHOLD
from fuzzywuzzy import process

def get_auth_headers(token: str) -> dict:
    """Gets authentication headers for a token"""
    return {"Authorization": f"Bearer {token}"}

async def get_user_tasks_from_nestjs(token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.get(f"{NESTJS_API_BASE_URL}/tasks/my-tasks", headers=headers)
        response.raise_for_status() # Raises an exception for HTTP errors (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting tasks from NestJS: {e}")
        return None

async def complete_task_in_nestjs(task_id: str, token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.patch(f"{NESTJS_API_BASE_URL}/tasks/{task_id}", 
                                json={"status": "completed"}, 
                                headers=headers)
        response.raise_for_status()
        return response.json() # Should return the updated task
    except requests.exceptions.RequestException as e:
        print(f"Error completing task {task_id} in NestJS: {e}")
        return None
    
async def process_task_in_nestjs(task_id: str, token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.patch(f"{NESTJS_API_BASE_URL}/tasks/{task_id}", 
                                json={"status": "in_progress"}, 
                                headers=headers)
        response.raise_for_status()
        return response.json() # Should return the updated task
    except requests.exceptions.RequestException as e:
        print(f"Error updating task {task_id} in NestJS: {e}")
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
        print(f"Error creating task '{task_name}' in NestJS: {e}")
        return None

async def delete_task_in_nestjs(task_id: str, token: str):
    try:
        headers = get_auth_headers(token)
        response = requests.delete(f"{NESTJS_API_BASE_URL}/tasks/{task_id}", headers=headers)
        response.raise_for_status()
        return True  # If we get here, the deletion was successful
    except requests.exceptions.RequestException as e:
        print(f"Error deleting task {task_id} in NestJS: {e}")
        return None

def find_most_similar_task(search_term: str, tasks: list[dict]) -> tuple[dict | None, int]:
    """
    Finds the most similar task in a list of tasks.
    Returns the task (dict) and the similarity score.
    """
    if not tasks or 'data' not in tasks or not tasks['data']:
        return None, 0
    
    tasks_data = tasks['data']

    task_names = {}
    for task in tasks_data:
        if isinstance(task, dict) and 'title' in task:
            task_names[task['title']] = task
    
    
    names_list = list(task_names.keys())
    
    # Find the best match
    try:
        best_match_name, score = process.extractOne(search_term, names_list)
        
        if score >= FUZZY_MATCH_THRESHOLD:
            return task_names[best_match_name], score
    except Exception as e:
        print(f"Error in search: {e}")
        return None, 0
    
    return None, 0