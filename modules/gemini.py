"""
Handles the interaction with the Gemini API.
"""
import json
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = genai.GenerativeModel('gemini-2.5-flash')

async def get_gemini_analysis(user_message: str) -> dict:
    """Analyzes the user's message using the Gemini API."""
    prompt = f"""
    Eres un asistente inteligente para la gestión de tareas. Tu objetivo es interpretar las frases de un usuario y extraer su intención y los detalles relevantes de la tarea.

    Si el usuario quiere CREAR una tarea, extrae el nombre de la tarea.
    Si el usuario quiere COMPLETAR una tarea, extrae el nombre de la tarea que se va a completar. Asume que el estado es "completada".
    Si el usuario quiere MARCAR una tarea como en PROCESO, extrae el nombre de la tarea que se está realizando. Indica que la intención es "en_proceso".
    Si el usuario quiere LISTAR sus tareas, indica que la intención es "listar_tareas".
    Si el usuario quiere ELIMINAR una tarea, extrae el nombre de la tarea.
    Si el usuario quiere SALUDAR o agradecer, indica la intención "saludo" o "agradecimiento".

    Si no puedes identificar una tarea específica, indícalo con "nombre_tarea": null.
    Si no puedes identificar la intención, usa "intencion": "desconocida".

    Formato de salida JSON:
    ```json
    {{
      "intencion": "nombre_de_la_intencion",
      "nombre_tarea": "nombre de la tarea"
    }}
    ```

    Ejemplos:

    Usuario: "Necesito una tarea para lavar los platos mañana"
    Salida: ```json
{{"intencion": "crear_tarea", "nombre_tarea": "lavar los platos"}}
```

    Usuario: "Ya terminé de comprar víveres"
    Salida: ```json
{{"intencion": "completar_tarea", "nombre_tarea": "comprar víveres"}}
```

    Usuario: "Voy a lavar el perro"
    Salida: ```json
{{"intencion": "en_proceso", "nombre_tarea": "lavar el perro"}}
```

    Usuario: "En dos horas retirare dinero del banco"
    Salida: ```json
{{"intencion": "en_proceso", "nombre_tarea": "retirar dinero"}}
```

    Usuario: "Ya terminé de comprar víveres"
    Salida: ```json
{{"intencion": "completar_tarea", "nombre_tarea": "comprar víveres"}}
```

    Usuario: "Podrías borrar la tarea de llamar al doctor"
    Salida: ```json
{{"intencion": "eliminar_tarea", "nombre_tarea": "llamar al doctor"}}
```

    Usuario: "Cuáles son mis tareas?"
    Salida: ```json
{{"intencion": "listar_tareas", "nombre_tarea": null}}
```

    Usuario: "Hola, ¿cómo estás?"
    Salida: ```json
{{"intencion": "saludo", "nombre_tarea": null}}
```

    Usuario: "Gracias"
    Salida: ```json
{{"intencion": "agradecimiento", "nombre_tarea": null}}
```

    
    Usuario: "Crea la taea nueva paa e prycto"
    Salida: ```json
{{"intencion": "crear_tarea", "nombre_tarea": "crear la tarea nueva para el proyecto"}}
```

    Usuario: "ya termien la creacion de tar proyexcto"
    Salida: ```json
{{"intencion": "completar_tarea", "nombre_tarea": "creación de tarea proyecto"}}
```
    ---
    Ahora, analiza la siguiente frase del usuario:
    {user_message}
    """
    try:
        response = GEMINI_MODEL.generate_content(prompt)
        text_response = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(text_response)
    except Exception as e:
        print(f"Error al llamar a Gemini o parsear respuesta: {e}")
        return {"intencion": "desconocida", "nombre_tarea": None}
