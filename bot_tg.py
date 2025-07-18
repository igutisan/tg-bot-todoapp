import os
from dotenv import load_dotenv
import google.generativeai as genai
import requests
import re
import json # Para parsear la respuesta JSON de Gemini
from fuzzywuzzy import process # Para el fuzzy matching
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode # Para formatear mensajes
import hashlib
import secrets

# Para Speech-to-Text
import speech_recognition as sr
from pydub import AudioSegment

# Cargar variables de entorno desde .env
load_dotenv()

# --- CONFIGURACIÓN ---
# Obtén tu clave API de Gemini de una variable de entorno para mayor seguridad
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno.")

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = genai.GenerativeModel('gemini-2.5-flash') # Modelo más reciente y estable

# URL base de tu API de NestJS
NESTJS_API_BASE_URL = "http://localhost:3000/api" # Ajusta si es diferente

# Tu token del bot de Telegram
BOT_TOKEN = '7971202116:AAEAILYiyqMIFyF9sX0xhSn8VhI-WGNvjTg' # Reemplaza con tu token real

# Umbral de similitud para fuzzy matching (0-100). Ajusta según qué tan estricto quieres ser.
FUZZY_MATCH_THRESHOLD = 82

# --- Almacenamiento de estado (en un entorno de producción, esto iría en una DB) ---
user_tokens: dict[int, str] = {} # Almacena el token por user_id
waiting_for_email: dict[int, bool] = {} # Indica si estamos esperando un correo
waiting_for_password: dict[int, bool] = {} # Indica si estamos esperando una contraseña
temp_emails: dict[int, str] = {} # Almacena temporalmente el correo durante la autenticación

# --- Lógica de validación de correo ---
def is_valid_email(email: str) -> bool:
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None

# --- Funciones de autenticación ---
def generate_token() -> str:
    """Genera un token aleatorio"""
    return secrets.token_urlsafe(32)

async def authenticate_user(email: str, password: str) -> str | None:
    """Autentica al usuario y devuelve el token"""
    try:
        # Enviar contraseña sin hashear para login
        response = requests.post(f"{NESTJS_API_BASE_URL}/auth/login", json={
            "email": email,
            "password": password  # Contraseña en texto plano
        })
        response.raise_for_status()
        data = response.json()
        return data.get('token')  # Asumiendo que la API devuelve un campo 'token'
    except requests.exceptions.RequestException as e:
        print(f"Error en autenticación para {email}: {e}")
        return None

# --- Funciones de interacción con la API de NestJS ---
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

# --- Función para encontrar la tarea más parecida usando fuzzywuzzy ---
def find_most_similar_task(search_term: str, tasks: list[dict]) -> tuple[dict | None, int]:
    """
    Busca la tarea más similar en una lista de tareas.
    Retorna la tarea (dict) y el puntaje de similitud.
    """
    if not tasks:
        return None, 0

    task_names = {task['title']: task for task in tasks} # Mapea nombres a objetos tarea
    names_list = list(task_names.keys())

    # process.extractOne devuelve (cadena_mas_parecida, puntaje_similitud)
    best_match_name, score = process.extractOne(search_term, names_list)

    if score >= FUZZY_MATCH_THRESHOLD:
        return task_names[best_match_name], score
    return None, 0 # No se encontró una coincidencia suficientemente buena

# --- Lógica del prompt de Gemini ---
async def get_gemini_analysis(user_message: str) -> dict:
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
    Salida: ```json\n{{"intencion": "crear_tarea", "nombre_tarea": "lavar los platos"}}\n```

    Usuario: "Ya terminé de comprar víveres"
    Salida: ```json\n{{"intencion": "completar_tarea", "nombre_tarea": "comprar víveres"}}\n```

    Usuario: "Voy a lavar el perro"
    Salida: ```json\n{{"intencion": "en_proceso", "nombre_tarea": "lavar el perro"}}\n```

    Usuario: "En dos horas retirare dinero del banco"
    Salida: ```json\n{{"intencion": "en_proceso", "nombre_tarea": "retirar dinero"}}\n```

    Usuario: "Ya terminé de comprar víveres"
    Salida: ```json\n{{"intencion": "completar_tarea", "nombre_tarea": "comprar víveres"}}\n```

    Usuario: "Podrías borrar la tarea de llamar al doctor"
    Salida: ```json\n{{"intencion": "eliminar_tarea", "nombre_tarea": "llamar al doctor"}}\n```

    Usuario: "Cuáles son mis tareas?"
    Salida: ```json\n{{"intencion": "listar_tareas", "nombre_tarea": null}}\n```

    Usuario: "Hola, ¿cómo estás?"
    Salida: ```json\n{{"intencion": "saludo", "nombre_tarea": null}}\n```

    Usuario: "Gracias"
    Salida: ```json\n{{"intencion": "agradecimiento", "nombre_tarea": null}}\n```

    
    Usuario: "Crea la taea nueva paa e prycto"
    Salida: ```json\n{{"intencion": "crear_tarea", "nombre_tarea": "crear la tarea nueva para el proyecto"}}\n```

    Usuario: "ya termien la creacion de tar proyexcto"
    Salida: ```json\n{{"intencion": "completar_tarea", "nombre_tarea": "creación de tarea proyecto"}}\n```
    ---
    Ahora, analiza la siguiente frase del usuario:
    {user_message}
    """
    try:
        response = GEMINI_MODEL.generate_content(prompt)
        # Gemini a veces incluye markdown (```json ... ```) en su respuesta, lo limpiamos
        text_response = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(text_response)
    except Exception as e:
        print(f"Error al llamar a Gemini o parsear respuesta: {e}")
        return {"intencion": "desconocida", "nombre_tarea": None}

# --- Handlers del Bot ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_tokens:
        await update.message.reply_text("Ya estás autenticado. Estoy listo para gestionar tus tareas.")
    else:
        waiting_for_email[user_id] = True
        await update.message.reply_text("¡Hola! Para empezar, por favor envíame tu correo electrónico.")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Usar la función común para procesar mensajes de texto
    await process_text_message(user_id, text, context)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_token = user_tokens.get(user_id)

    if not user_token:
        waiting_for_email[user_id] = True
        await update.message.reply_text("Por favor, necesito tu correo electrónico para autenticarte. Envíamelo.")
        return

    await update.message.reply_text("Procesando tu audio, por favor espera...")

    try:
        # Descargar el archivo de voz de Telegram (viene en formato .ogg)
        voice_file = await update.message.voice.get_file()
        file_path = f"user_{user_id}_voice.ogg"
        await voice_file.download_to_drive(file_path)

        # Convertir OGG a WAV para SpeechRecognition
        audio = AudioSegment.from_ogg(file_path)
        wav_file_path = f"user_{user_id}_voice.wav"
        audio.export(wav_file_path, format="wav")

        # Usar SpeechRecognition para transcribir
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file_path) as source:
            audio_data = recognizer.record(source)
            # Usar Google Web Speech API (gratuito para uso básico)
            # O puedes usar recognizer.recognize_whisper() si tienes Whisper instalado localmente
            text_from_audio = recognizer.recognize_google(audio_data, language="es-ES")
            print(f"Transcripción de audio para {user_id}: {text_from_audio}")
            
            # En lugar de modificar el objeto update, procesamos el texto directamente
            await process_text_message(user_id, text_from_audio, context)

    except sr.UnknownValueError:
        await update.message.reply_text("No pude entender el audio. ¿Podrías hablar más claro o escribirlo?")
    except sr.RequestError as e:
        await update.message.reply_text(f"No pude procesar el audio debido a un error del servicio de reconocimiento de voz. {e}")
    except Exception as e:
        await update.message.reply_text(f"Hubo un error al procesar tu audio. {e}")
    finally:
        # Limpiar archivos temporales
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)

async def process_text_message(user_id: int, text: str, context: ContextTypes.DEFAULT_TYPE):
    """Procesa un mensaje de texto (usado tanto para texto como para audio transcrito)"""
    
    # Paso 1: Manejar registro de correo electrónico
    if waiting_for_email.get(user_id, False):
        if is_valid_email(text):
            temp_emails[user_id] = text
            waiting_for_email[user_id] = False
            waiting_for_password[user_id] = True
            # Enviar respuesta usando el contexto
            await context.bot.send_message(chat_id=user_id, text=f"Correo registrado: *{text}*. Ahora envíame tu contraseña.", parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_message(chat_id=user_id, text="El correo electrónico no es válido. Por favor, intenta de nuevo.")
        return

    # Paso 2: Manejar registro de contraseña
    if waiting_for_password.get(user_id, False):
        user_email = temp_emails.get(user_id)
        if user_email:
            # Intentar autenticar
            token = await authenticate_user(user_email, text)
            if token:
                user_tokens[user_id] = token
                waiting_for_password[user_id] = False
                # Limpiar el correo temporal
                if user_id in temp_emails:
                    del temp_emails[user_id]
                await context.bot.send_message(chat_id=user_id, text="¡Autenticación exitosa! Ahora puedes decirme cosas como:\n"
                                              "- `Crea la tarea de comprar leche`\n"
                                              "- `Ya terminé de lavar los platos`\n"
                                              "- `Muéstrame mis tareas`\n"
                                              "- `Borra la tarea de llamar a Juan`",
                                              parse_mode=ParseMode.MARKDOWN)
            else:
                await context.bot.send_message(chat_id=user_id, text="Error en la autenticación. Verifica tu correo y contraseña.")
        return

    # Paso 3: Si no tenemos el token, pedir autenticación
    if user_id not in user_tokens:
        waiting_for_email[user_id] = True
        await context.bot.send_message(chat_id=user_id, text="Por favor, necesito tu correo electrónico para autenticarte. Envíamelo.")
        return

    # Paso 4: Usar Gemini para analizar el mensaje
    await context.bot.send_message(chat_id=user_id, text="Analizando tu mensaje...")
    analysis = await get_gemini_analysis(text)
    print(f"Análisis de Gemini para '{text}': {analysis}")

    intencion = analysis.get("intencion")
    nombre_tarea_gemini = analysis.get("nombre_tarea")
    token = user_tokens.get(user_id)

    if intencion == "crear_tarea":
        if nombre_tarea_gemini:
            new_task = await create_task_in_nestjs(nombre_tarea_gemini, token)
            if new_task:
                await context.bot.send_message(chat_id=user_id, text=f"¡Tarea '{new_task['title']}' creada con éxito!")
            else:
                await context.bot.send_message(chat_id=user_id, text="Lo siento, no pude crear la tarea. ¿Podrías intentarlo de nuevo?")
        else:
            await context.bot.send_message(chat_id=user_id, text="No pude identificar el nombre de la tarea que quieres crear. ¿Podrías ser más específico?")
    elif intencion == "en_proceso":
        if nombre_tarea_gemini:
            # 1. Obtener todas las tareas del usuario
            user_tasks = await get_user_tasks_from_nestjs(token)
            if not user_tasks:
                await context.bot.send_message(chat_id=user_id, text="No pude obtener tus tareas para actualizar. Asegúrate de que existan.")
                return

            # 2. Encontrar la tarea más parecida usando fuzzywuzzy
            found_task, score = find_most_similar_task(nombre_tarea_gemini, user_tasks)

            if found_task:
                # 3. Marcar como completada en NestJS
                updated_task = await process_task_in_nestjs(found_task['id'], token)
                print(f"Tarea encontrada: {found_task['title']} con score {score}")
                print(f"Tarea actualizada: {updated_task}")
                if updated_task:
                    await context.bot.send_message(chat_id=user_id, text=f"¡Tarea '{updated_task['title']}' marcada como en proceso! 🎉")
                else:
                    await context.bot.send_message(chat_id=user_id, text="Hubo un problema al marcar la tarea como en proceso. ¿Puedes intentar de nuevo?")
            else:
                await context.bot.send_message(chat_id=user_id, text=f"No encontré ninguna tarea similar a '{nombre_tarea_gemini}'. ¿Quizás quieres crearla?")
        else:
            await context.bot.send_message(chat_id=user_id, text="No pude identificar la tarea que quieres completar. ¿Puedes ser más específico?")
    elif intencion == "completar_tarea":
        if nombre_tarea_gemini:
            # 1. Obtener todas las tareas del usuario
            user_tasks = await get_user_tasks_from_nestjs(token)
            if not user_tasks:
                await context.bot.send_message(chat_id=user_id, text="No pude obtener tus tareas para completar. Asegúrate de que existan.")
                return

            # 2. Encontrar la tarea más parecida usando fuzzywuzzy
            found_task, score = find_most_similar_task(nombre_tarea_gemini, user_tasks)

            if found_task:
                # 3. Marcar como completada en NestJS
                updated_task = await complete_task_in_nestjs(found_task['id'], token)
                print(f"Tarea encontrada: {found_task['title']} con score {score}")
                print(f"Tarea actualizada: {updated_task}")
                if updated_task:
                    await context.bot.send_message(chat_id=user_id, text=f"¡Tarea '{updated_task['title']}' marcada como completada! 🎉")
                else:
                    await context.bot.send_message(chat_id=user_id, text="Hubo un problema al marcar la tarea como completada. ¿Puedes intentar de nuevo?")
            else:
                await context.bot.send_message(chat_id=user_id, text=f"No encontré ninguna tarea similar a '{nombre_tarea_gemini}'. ¿Quizás quieres crearla?")
        else:
            await context.bot.send_message(chat_id=user_id, text="No pude identificar la tarea que quieres completar. ¿Puedes ser más específico?")
    elif intencion == "eliminar_tarea":
        if nombre_tarea_gemini:
            user_tasks = await get_user_tasks_from_nestjs(token)
            if not user_tasks:
                await context.bot.send_message(chat_id=user_id, text="No pude obtener tus tareas para eliminar. Asegúrate de que existan.")
                return

            found_task, score = find_most_similar_task(nombre_tarea_gemini, user_tasks)

            if found_task:
                deleted_task = await delete_task_in_nestjs(found_task['id'], token)
                if deleted_task:
                    await context.bot.send_message(chat_id=user_id, text=f"¡Tarea '{found_task['title']}' eliminada con éxito!🗑️")
                else:
                    await context.bot.send_message(chat_id=user_id, text="Hubo un problema al eliminar la tarea. ¿Puedes intentar de nuevo?")
            else:
                await context.bot.send_message(chat_id=user_id, text=f"No encontré ninguna tarea similar a '{nombre_tarea_gemini}' para eliminar.")
        else:
            await context.bot.send_message(chat_id=user_id, text="No pude identificar la tarea que quieres eliminar. ¿Puedes ser más específico?")

    elif intencion == "listar_tareas":
        tasks = await get_user_tasks_from_nestjs(token)
        if tasks:
            pending_tasks = [t for t in tasks if t.get('status') != 'completed'] # Asumiendo un campo 'status'
            if pending_tasks:
                task_list_text = "Estas son tus tareas pendientes:\n"
                for i, task in enumerate(pending_tasks):
                    task_list_text += f"*{i+1}.* {task['title']}\n"
                await context.bot.send_message(chat_id=user_id, text=task_list_text, parse_mode=ParseMode.MARKDOWN)
            else:
                await context.bot.send_message(chat_id=user_id, text="¡No tienes tareas pendientes! 🎉")
        else:
            await context.bot.send_message(chat_id=user_id, text="No pude recuperar tus tareas en este momento.")

    elif intencion == "saludo":
        await context.bot.send_message(chat_id=user_id, text="¡Hola! ¿En qué puedo ayudarte hoy con tus tareas?")

    elif intencion == "agradecimiento":
        await context.bot.send_message(chat_id=user_id, text="¡De nada! Estoy aquí para ayudarte.")

    else: # intencion == "desconocida" o cualquier otra
        await context.bot.send_message(chat_id=user_id, text="No entendí bien lo que quisiste decir. ¿Podrías intentar de nuevo o reformular tu solicitud?")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message)) # Nuevo handler para mensajes de voz

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()