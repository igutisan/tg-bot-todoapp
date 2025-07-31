import sys
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.auth import authenticate_user, is_valid_email
from modules.gemini import get_gemini_analysis
from modules.speech import transcribe_voice_message
from modules.state import bot_state
from modules.tasks import (
    get_user_tasks_from_nestjs,
    complete_task_in_nestjs,
    process_task_in_nestjs,
    create_task_in_nestjs,
    delete_task_in_nestjs,
    find_most_similar_task,
)
from config import BOT_TOKEN

# Command Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user_id = update.message.from_user.id
    if not bot_state.get_user_token(user_id):
        bot_state.set_waiting_for_email(user_id, True)
        await update.message.reply_text("Hola! Para comenzar, por favor, introduce tu correo electrónico.")
    else:
        await update.message.reply_text("Ya estás autenticado. Puedes comenzar a gestionar tus tareas.")

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /logout command."""
    user_id = update.message.from_user.id
    bot_state.clear_user_auth_session(user_id)
    if user_id in bot_state.user_tokens:
        del bot_state.user_tokens[user_id]
    await update.message.reply_text("Has cerrado sesión correctamente.")

# Message Handlers
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text messages."""
    user_id = update.message.from_user.id
    message_text = update.message.text

    # Authentication flow
    if bot_state.is_waiting_for_email(user_id):
        await update.message.delete()
        if is_valid_email(message_text):
            bot_state.set_temp_email(user_id, message_text)
            bot_state.set_waiting_for_email(user_id, False)
            bot_state.set_waiting_for_password(user_id, True)
            await update.message.reply_text("Correo electrónico recibido. Ahora, por favor, introduce tu contraseña.")
        else:
            await update.message.reply_text("El correo electrónico no es válido. Por favor, inténtalo de nuevo.")
        return

    if bot_state.is_waiting_for_password(user_id):
        await update.message.delete()
        email = bot_state.get_temp_email(user_id)
        token = await authenticate_user(email, message_text)
        if token:
            bot_state.set_user_token(user_id, token)
            bot_state.clear_user_auth_session(user_id)
            await update.message.reply_text("Autenticación exitosa. Ahora puedes gestionar tus tareas.")
        else:
            await update.message.reply_text("Autenticación fallida. Por favor, revisa tus credenciales e inténtalo de nuevo, comenzando por tu correo electrónico.")
            bot_state.clear_user_auth_session(user_id)
            bot_state.set_waiting_for_email(user_id, True)
        return

    # Task management flow
    token = bot_state.get_user_token(user_id)
    if not token:
        await update.message.reply_text("Por favor, autentícate primero. Usa /start para comenzar.")
        return

    analysis = await get_gemini_analysis(message_text)
    intent = analysis.get("intencion")
    task_name = analysis.get("nombre_tarea")

    if intent == "crear_tarea":
        if task_name:
            await create_task_in_nestjs(task_name, token)
            await update.message.reply_text(f"Tarea '{task_name}' creada.")
        else:
            await update.message.reply_text("No pude identificar el nombre de la tarea para crearla.")

    elif intent in ["completar_tarea", "en_proceso", "eliminar_tarea"]:
        if not task_name:
            await update.message.reply_text(f"No pude identificar el nombre de la tarea para {intent.replace('_task', '')}.")
            return

        tasks = await get_user_tasks_from_nestjs(token)
        if not tasks or not tasks.get('data'):
            await update.message.reply_text(f"No encontré ninguna tarea para '{task_name}'.")
            return

        best_match, score = find_most_similar_task(task_name, tasks)

        if best_match:
            task_id = best_match.get('id')
            matched_task_name = best_match.get('title', task_name)
            if intent == "completar_tarea":
                await complete_task_in_nestjs(task_id, token)
                await update.message.reply_text(f"Tarea '{matched_task_name}' completada.")
            elif intent == "en_proceso":
                await process_task_in_nestjs(task_id, token)
                await update.message.reply_text(f"Tarea '{matched_task_name}' marcada como 'en proceso'.")
            elif intent == "eliminar_tarea":
                await delete_task_in_nestjs(task_id, token)
                await update.message.reply_text(f"Tarea '{matched_task_name}' eliminada.")
        else:
            await update.message.reply_text(f"No encontré una tarea que coincida con '{task_name}'.")

    elif intent == "listar_tareas":
        tasks = await get_user_tasks_from_nestjs(token)
        if tasks and tasks.get('data'):
            active_tasks = [task for task in tasks['data'] if task['status'] in ['pending', 'in_progress']]
            if active_tasks:
                task_list = "\n".join([f"- {task['title']} ({task['status']})" for task in active_tasks])
                await update.message.reply_text(f"Tus tareas activas:\n{task_list}")
            else:
                await update.message.reply_text("No tienes tareas pendientes o en progreso.")
        else:
            await update.message.reply_text("No tienes tareas o no pude recuperarlas.")

    elif intent == "saludo":
        await update.message.reply_text("¡Hola! ¿En qué puedo ayudarte con tus tareas?")

    elif intent == "agradecimiento":
        await update.message.reply_text("¡De nada! Estoy aquí para ayudarte.")

    else:
        await update.message.reply_text("No entendí tu solicitud. Puedes pedirme crear, completar, listar o eliminar tareas.")

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles voice messages."""
    user_id = update.message.from_user.id
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    
    transcribed_text = await transcribe_voice_message(user_id, voice_file)

    if transcribed_text:
        # Create a new Update object with the transcribed text
        new_update = Update(update.update_id, message=update.message)
        new_update.message.text = transcribed_text
        await handle_text_message(new_update, context)
    else:
        await update.message.reply_text("No pude entender el audio. ¿Podrías intentarlo de nuevo o escribir tu solicitud?")

def main():
    """Runs the bot."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('logout', logout_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()