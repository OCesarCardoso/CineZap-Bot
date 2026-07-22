import os
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from database.supabase_client import supabase

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ── /start ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [[InlineKeyboardButton("📍 Uberlândia", callback_data="cidade:uberlandia")]]
    await update.message.reply_text(
        "🎬 Bem-vindo ao CineZap!\nEscolha sua cidade:",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Usuário escolheu a cidade ────────────────────────────────────────────────

async def escolher_cidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cidade_slug = query.data.split(":")[1]
    context.user_data["cidade"] = cidade_slug

    # Busca filmes que têm sessão nessa cidade
    cinemas = supabase.table("cinemas").select("id").eq("cidade", cidade_slug).execute()
    cinema_ids = [c["id"] for c in cinemas.data]

    sessoes = (
        supabase.table("sessoes")
        .select("filme_id")
        .in_("cinema_id", cinema_ids)
        .execute()
    )
    filme_ids = list({s["filme_id"] for s in sessoes.data})

    filmes = (
        supabase.table("filmes")
        .select("id, titulo")
        .in_("id", filme_ids)
        .order("titulo")
        .execute()
    )

    if not filmes.data:
        await query.edit_message_text("Nenhum filme encontrado para essa cidade.")
        return

    teclado = [
        [InlineKeyboardButton(f["titulo"], callback_data=f"filme:{f['id']}")]
        for f in filmes.data
    ]
    await query.edit_message_text(
        "🎥 Filmes em cartaz — escolha um:",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Usuário escolheu o filme ─────────────────────────────────────────────────

async def escolher_filme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filme_id = int(query.data.split(":")[1])
    cidade_slug = context.user_data.get("cidade", "uberlandia")

    filme = supabase.table("filmes").select("*").eq("id", filme_id).single().execute()
    f = filme.data

    cinemas = supabase.table("cinemas").select("id, nome").eq("cidade", cidade_slug).execute()
    cinema_ids = {c["id"]: c["nome"] for c in cinemas.data}

    sessoes = (
        supabase.table("sessoes")
        .select("cinema_id, data_horario, link_compra")
        .eq("filme_id", filme_id)
        .in_("cinema_id", list(cinema_ids.keys()))
        .order("data_horario")
        .execute()
    )

    # Monta o texto de resposta
    texto = f"🎬 *{f['titulo']}*\n"

    if f.get("sinopse"):
        texto += f"\n📝 {f['sinopse']}\n"
    if f.get("duracao"):
        texto += f"⏱ Duração: {f['duracao']}\n"
    if f.get("classificacao"):
        texto += f"🔞 Classificação: {f['classificacao']}\n"
    if f.get("diretor"):
        texto += f"🎬 Diretor: {f['diretor']}\n"
    if f.get("trailer_url_youtube"):
        texto += f"▶️ [Trailer]({f['trailer_url_youtube']})\n"

    texto += "\n📅 *Sessões:*\n"

    # Agrupa sessões por cinema
    por_cinema: dict = {}
    for s in sessoes.data:
        nome_cinema = cinema_ids[s["cinema_id"]]
        por_cinema.setdefault(nome_cinema, []).append(s)

    for nome_cinema, sessoes_cinema in por_cinema.items():
        texto += f"\n🏟 *{nome_cinema}*\n"
        for s in sessoes_cinema:
            horario = s["data_horario"].replace("T", " ")[:16]
            link = s["link_compra"]
            texto += f"  • {horario} — [Comprar]({link})\n"

    await query.edit_message_text(
        texto,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


# ── Inicialização ─────────────────────────────────────────────────────────────

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(escolher_cidade, pattern="^cidade:"))
app.add_handler(CallbackQueryHandler(escolher_filme, pattern="^filme:"))

print("Rodando o bot CineZap...")

app.run_polling()