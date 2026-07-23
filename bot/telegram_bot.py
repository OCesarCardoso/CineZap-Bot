import os

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from database.supabase_client import supabase

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [[InlineKeyboardButton("📍 Uberlândia", callback_data="cidade:uberlandia")]]
    await update.message.reply_text(
        "🎬 Bem-vindo ao CineZap!\nEscolha sua cidade:",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Cidade escolhida → lista de filmes ───────────────────────────────────────

async def escolher_cidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cidade_slug = query.data.split(":")[1]
    context.user_data["cidade"] = cidade_slug

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
    teclado.append([InlineKeyboardButton("⬅️ Voltar", callback_data="voltar:inicio")])

    await query.edit_message_text(
        "🎥 Filmes em cartaz — escolha um:",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Filme escolhido → menu do filme ──────────────────────────────────────────

async def escolher_filme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filme_id = int(query.data.split(":")[1])
    context.user_data["filme_id"] = filme_id


    filme = (
        supabase.table("filmes")
        .select("titulo, sinopse, duracao, classificacao, generos")
        .eq("id", filme_id)
        .single()
        .execute()
    )
    f = filme.data

    texto = f"🎬 *{f['titulo']}*\n\n"

    if f.get("sinopse"):
        texto += f"📝 {f['sinopse']}\n\n"
    if f.get("duracao"):
        texto += f"⏱ Duração: {f['duracao']}\n"
    if f.get("classificacao"):
        texto += f"🔞 Classificação: {f['classificacao']}\n"
    if f.get("generos"):
        texto += f"🎭 Gêneros: {', '.join(f['generos'])}\n"

    teclado = [
        [InlineKeyboardButton("🎬 Sessões", callback_data=f"sessoes:{filme_id}")],
        [InlineKeyboardButton("▶️ Trailer", callback_data=f"trailer:{filme_id}")],
        [InlineKeyboardButton("⭐ Curiosidades", callback_data=f"curiosidades:{filme_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"cidade:{context.user_data.get('cidade', 'uberlandia')}")],
    ]

    await query.edit_message_text(
        texto + "\nO que você quer ver?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Sessões ───────────────────────────────────────────────────────────────────

async def ver_sessoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filme_id = int(query.data.split(":")[1])
    cidade_slug = context.user_data.get("cidade", "uberlandia")

    filme = supabase.table("filmes").select("titulo").eq("id", filme_id).single().execute()

    cinemas = (
        supabase.table("cinemas")
        .select("id, nome")
        .eq("cidade", cidade_slug)
        .execute()
    )
    cinema_ids = {c["id"]: c["nome"] for c in cinemas.data}

    # Filtra sessões que ainda não passaram (com tolerância de 15 minutos)
    agora = datetime.now(timezone(timedelta(hours=-3)))
    limite = agora - timedelta(minutes=15)
    limite_str = limite.strftime("%Y-%m-%dT%H:%M:%S")

    sessoes = (
        supabase.table("sessoes")
        .select("cinema_id, data_horario, link_compra")
        .eq("filme_id", filme_id)
        .in_("cinema_id", list(cinema_ids.keys()))
        .gte("data_horario", limite_str)
        .order("data_horario")
        .execute()
    )

    if not sessoes.data:
        texto = "Não há sessões disponíveis para este filme no momento."
    else:
        texto = f"🎬 *{filme.data['titulo']}* — Sessões disponíveis:\n"

        por_cinema: dict = {}
        for s in sessoes.data:
            nome = cinema_ids[s["cinema_id"]]
            por_cinema.setdefault(nome, []).append(s)

        for nome_cinema, sessoes_cinema in por_cinema.items():
            texto += f"\n🏟 *{nome_cinema}*\n"
            for s in sessoes_cinema:
                horario = s["data_horario"][:16].replace("T", " ")
                link = s["link_compra"]
                texto += f"  • {horario} — [Comprar]({link})\n"

    teclado = [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"filme:{filme_id}")]]

    await query.edit_message_text(
        texto,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Trailer ───────────────────────────────────────────────────────────────────

async def ver_trailer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filme_id = int(query.data.split(":")[1])

    filme = (
        supabase.table("filmes")
        .select("titulo, trailer_url_youtube")
        .eq("id", filme_id)
        .single()
        .execute()
    )
    f = filme.data

    if f.get("trailer_url_youtube"):
        texto = f"*{f['titulo']}* — Trailer"

        preview = LinkPreviewOptions(
            url=f["trailer_url_youtube"],
            prefer_large_media=True,
            show_above_text=True
        )

        teclado = [
            [
                InlineKeyboardButton(
                    "▶️ Assistir no YouTube",
                    url=f["trailer_url_youtube"]
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data=f"filme:{filme_id}"
                )
            ]
        ]

    else:
        texto = "Trailer não disponível para este filme."
        preview = LinkPreviewOptions(is_disabled=True)

        teclado = [
            [InlineKeyboardButton("⬅️ Voltar", callback_data=f"filme:{filme_id}")]
        ]

    await query.edit_message_text(
        texto,
        parse_mode="Markdown",
        link_preview_options=preview,
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Curiosidades ──────────────────────────────────────────────────────────────

async def ver_curiosidades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filme_id = int(query.data.split(":")[1])

    filme = (
        supabase.table("filmes")
        .select("titulo, diretor, elenco, nota_imdb, nota_rotten, bilheteria_mojo")
        .eq("id", filme_id)
        .single()
        .execute()
    )
    f = filme.data

    texto = f"⭐ *{f['titulo']}* — Curiosidades\n\n"

    if f.get("diretor"):
        texto += f"🎬 *Diretor:* {f['diretor']}\n"
    if f.get("elenco"):
        texto += f"🎭 *Elenco:* {', '.join(f['elenco'][:5])}\n"

    # Campos dos outros scrapers — aparecem automaticamente quando estiverem no banco
    if f.get("nota_imdb"):
        texto += f"⭐ *IMDb:* {f['nota_imdb']}\n"
    if f.get("nota_rotten"):
        texto += f"🍅 *Rotten Tomatoes:* {f['nota_rotten']}\n"
    if f.get("bilheteria_mojo"):
        texto += f"💰 *Bilheteria:* {f['bilheteria_mojo']}\n"

    teclado = [[InlineKeyboardButton("⬅️ Voltar", callback_data=f"filme:{filme_id}")]]

    await query.edit_message_text(
        texto,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Voltar ao início ──────────────────────────────────────────────────────────

async def voltar_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    teclado = [[InlineKeyboardButton("📍 Uberlândia", callback_data="cidade:uberlandia")]]
    await query.edit_message_text(
        "🎬 Bem-vindo ao CineZap!\nEscolha sua cidade:",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


# ── Inicialização ─────────────────────────────────────────────────────────────

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(voltar_inicio, pattern="^voltar:inicio$"))
app.add_handler(CallbackQueryHandler(escolher_cidade, pattern="^cidade:"))
app.add_handler(CallbackQueryHandler(escolher_filme, pattern="^filme:"))
app.add_handler(CallbackQueryHandler(ver_sessoes, pattern="^sessoes:"))
app.add_handler(CallbackQueryHandler(ver_trailer, pattern="^trailer:"))
app.add_handler(CallbackQueryHandler(ver_curiosidades, pattern="^curiosidades:"))

print("Rodando o bot CineZap...")

app.run_polling()

print("Tirando o bot do ar...")