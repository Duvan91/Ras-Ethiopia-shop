from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram import WebAppInfo
CHANNEL_USERNAME = "@Ethiopianonlineshoppin"
WEBAPP_URL = "https://duvan91.github.io/Ras-Ethiopia-shop/"
import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)

logging.basicConfig(level=logging.INFO)

# ---------- SETTINGS: EDIT THESE ----------
ADMIN_USERNAME = "RasEthiopia"          # without @
SUPPORT_PHONE = "+251955071070"
SUPPORT_TELEGRAM = "@Rasethiopiashupport"
CHANNEL_USERNAME = "@Ethiopianonlineshoppin"

DATA_FILE = "shop_data.json"

# ---------- DATA STORAGE (persists in a JSON file) ----------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "products": {},   # id -> {name, price, category, stock, photo}
        "categories": ["Clothes", "Watch", "Phone", "Book"],
        "payments": {"telebirr": True, "cbe": True, "cod": True},
        "next_id": 1,
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()
carts = {}

# Conversation states
NAME, ADDRESS, PHONE, PAYMENT_PROOF = range(4)
ADD_PHOTO, ADD_NAME, ADD_PRICE, ADD_CATEGORY, ADD_STOCK = range(4, 9)
NEW_CATEGORY = 9


def is_admin(update: Update):
    user = update.effective_user
    return user.username and user.username.lower() == ADMIN_USERNAME.lower()


async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def require_join_message(update: Update):
    keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
                [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]]
    await update.message.reply_text(
        "Please join our official channel first to use the shop:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------- BUYER FLOW ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        joined = await check_membership(update, context)
        if not joined:
            await require_join_message(update)
            return
    await show_categories(update, context)
, reply_markup=InlineKeyboardMarkup(keyboard))

    keyboard = [[InlineKeyboardButton("🛍 Open Shop", web_app=WebAppInfo(url=WEBAPP_URL))]]
    text = "Welcome to Ras Ethiopia Shop! ሰላም! Tap below to browse and shop:"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

def products_in_category(cat):
    return {pid: p for pid, p in data["products"].items() if p["category"] == cat}


def cart_total(user_id):
    cart = carts.get(user_id, {})
    total = 0
    for pid, qty in cart.items():
        p = data["products"].get(pid)
        if p:
            total += p["price"] * qty
    return total


def cart_text(user_id):
    cart = carts.get(user_id, {})
    if not cart:
        return "Your cart is empty."
    lines = ["🛒 Your Cart:\n"]
    for pid, qty in cart.items():
        p = data["products"].get(pid)
        if p:
            lines.append(f"{p['name']} x{qty} — {p['price'] * qty:.2f} ETB")
    lines.append(f"\nTotal: {cart_total(user_id):.2f} ETB")
    return "\n".join(lines)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    d = query.data

    if d == "check_join":
        joined = await check_membership(update, context)
        if joined:
            await query.answer("Thank you for joining!")
            await show_categories(update, context)
        else:
            await query.answer("You haven't joined yet. Please join first.", show_alert=True)
        return

    if d.startswith("cat_"):
        await query.answer()
        cat = d[4:]
        prods = products_in_category(cat)
        keyboard = []
        for pid, p in prods.items():
            stock_note = "" if p["stock"] > 0 else " (Out of stock)"
            keyboard.append([InlineKeyboardButton(
                f"{p['name']} — {p['price']:.2f} ETB{stock_note}", callback_data=f"view_{pid}"
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_categories")])
        if not prods:
            await query.edit_message_text(f"No products in {cat} yet.", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(f"📁 {cat} — choose an item:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if d == "back_categories":
        await query.answer()
        await show_categories(update, context)
        return

    if d.startswith("view_"):
        await query.answer()
        pid = d[5:]
        p = data["products"].get(pid)
        if not p:
            await query.edit_message_text("This product no longer exists.")
            return
        keyboard = [[InlineKeyboardButton("➕ Add to Cart", callback_data=f"add_{pid}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"cat_{p['category']}")]]
        caption = f"{p['name']}\nPrice: {p['price']:.2f} ETB\nStock: {p['stock']}"
        if p.get("photo"):
            await context.bot.send_photo(chat_id=user_id, photo=p["photo"], caption=caption,
                                          reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(caption, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if d.startswith("add_"):
        pid = d[4:]
        p = data["products"].get(pid)
        if not p or p["stock"] <= 0:
            await query.answer("Out of stock!", show_alert=True)
            return
        cart = carts.setdefault(user_id, {})
        cart[pid] = cart.get(pid, 0) + 1
        await query.answer(f"Added {p['name']} to cart!", show_alert=True)
        return

    if d == "view_cart":
        await query.answer()
        keyboard = [[InlineKeyboardButton("✅ Checkout", callback_data="checkout")],
                    [InlineKeyboardButton("🗑 Clear Cart", callback_data="clear_cart")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="back_categories")]]
        await context.bot.send_message(chat_id=user_id, text=cart_text(user_id),
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if d == "clear_cart":
        await query.answer()
        carts[user_id] = {}
        await query.edit_message_text("Cart cleared.")
        return


async def checkout_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not carts.get(user_id):
        await query.edit_message_text("Your cart is empty.")
        return ConversationHandler.END
    await query.edit_message_text(f"{cart_text(user_id)}\n\nWhat's your name?")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Your delivery address / Sub-City?")
    return ADDRESS


async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text
    await update.message.reply_text("Your phone number?")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    methods = []
    if data["payments"]["telebirr"]:
        methods.append("📱 Telebirr: " + SUPPORT_PHONE)
    if data["payments"]["cbe"]:
        methods.append("🏦 CBE Bank: Commercial Bank of Ethiopia (contact admin for account number)")
    if data["payments"]["cod"]:
        methods.append("💵 Cash on Delivery (Addis Ababa only)")
    text = "Payment Options:\n\n" + "\n".join(methods) + "\n\nAfter paying, send a screenshot here to confirm your order."
    await update.message.reply_text(text)
    return PAYMENT_PROOF


async def get_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    order_summary = (
        f"🆕 NEW ORDER\n\n{cart_text(user_id)}\n\n"
        f"Name: {context.user_data.get('name')}\n"
        f"Address: {context.user_data.get('address')}\n"
        f"Phone: {context.user_data.get('phone')}\n"
        f"Buyer: @{user.username or user.id}"
    )
    admin_chats = context.bot_data.get("admin_chat_id")
    if admin_chats:
        await context.bot.send_message(chat_id=admin_chats, text=order_summary)
        if update.message.photo:
            await context.bot.send_photo(chat_id=admin_chats, photo=update.message.photo[-1].file_id)
    await update.message.reply_text("✅ Order received! We'll confirm your payment and contact you shortly.")
    for pid, qty in carts.get(user_id, {}).items():
        if pid in data["products"]:
            data["products"][pid]["stock"] = max(0, data["products"][pid]["stock"] - qty)
    save_data(data)
    carts[user_id] = {}
    return ConversationHandler.END

async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order = json.loads(update.effective_message.web_app_data.data)
    user = update.effective_user
    lines = [f"🆕 NEW ORDER (Mini App)\n"]
    total = 0
    for pid, qty in order["cart"].items():
        p = data["products"].get(pid)
        if p:
            sub = p["price"] * qty
            total += sub
            lines.append(f"{p['name']} x{qty} — {sub:.2f} ETB")
            p["stock"] = max(0, p["stock"] - qty)
    lines.append(f"\nTotal: {total:.2f} ETB")
    lines.append(f"\nName: {order['name']}\nAddress: {order['address']}\nPhone: {order['phone']}")
    lines.append(f"Buyer: @{user.username or user.id}")
    save_data(data)

    admin_chat = context.bot_data.get("admin_chat_id")
    if admin_chat:
        await context.bot.send_message(chat_id=admin_chat, text="\n".join(lines))

    await update.message.reply_text("✅ Order received! We'll confirm your payment and contact you shortly.")


# ---------- ADMIN FLOW ----------
async def register_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update):
        context.bot_data["admin_chat_id"] = update.effective_chat.id


async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    await register_admin(update, context)
    await update.message.reply_text("Send the product photo (or type 'skip' for no photo):")
    return ADD_PHOTO


async def add_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data["new_photo"] = update.message.photo[-1].file_id
    else:
        context.user_data["new_photo"] = None
    await update.message.reply_text("Product name?")
    return ADD_NAME


async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_name"] = update.message.text
    await update.message.reply_text("Price in ETB (numbers only)?")
    return ADD_PRICE


async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_price"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please send a valid number for price.")
        return ADD_PRICE
    keyboard = [[InlineKeyboardButton(c, callback_data=f"setcat_{c}")] for c in data["categories"]]
    await update.message.reply_text("Choose category:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_CATEGORY


async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.replace("setcat_", "")
    context.user_data["new_category"] = cat
    await query.edit_message_text("Stock quantity (number)?")
    return ADD_STOCK


async def add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stock = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Please send a valid whole number for stock.")
        return ADD_STOCK
    pid = str(data["next_id"])
    data["next_id"] += 1
    data["products"][pid] = {
        "name": context.user_data["new_name"],
        "price": context.user_data["new_price"],
        "category": context.user_data["new_category"],
        "stock": stock,
        "photo": context.user_data.get("new_photo"),
    }
    save_data(data)
    await update.message.reply_text(f"✅ Product added: {context.user_data['new_name']} ({stock} in stock)")
    return ConversationHandler.END


async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    await update.message.reply_text("Type the new category name:")
    return NEW_CATEGORY


async def add_category_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat = update.message.text.strip()
    if cat not in data["categories"]:
        data["categories"].append(cat)
        save_data(data)
        await update.message.reply_text(f"✅ Category '{cat}' added.")
    else:
        await update.message.reply_text("That category already exists.")
    return ConversationHandler.END


async def remove_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /removecategory CategoryName")
        return
    cat = " ".join(context.args)
    if cat in data["categories"]:
        data["categories"].remove(cat)
        save_data(data)
        await update.message.reply_text(f"✅ Category '{cat}' removed.")
    else:
        await update.message.reply_text("Category not found.")


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not data["products"]:
        await update.message.reply_text("No products yet.")
        return
    lines = []
    for pid, p in data["products"].items():
        lines.append(f"#{pid} {p['name']} — {p['price']:.2f} ETB — {p['category']} — Stock: {p['stock']}")
    await update.message.reply_text("\n".join(lines))


async def remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /removeproduct ID")
        return
    pid = context.args[0]
    if pid in data["products"]:
        name = data["products"][pid]["name"]
        del data["products"][pid]
        save_data(data)
        await update.message.reply_text(f"✅ Removed {name}.")
    else:
        await update.message.reply_text("Product ID not found.")


async def set_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setstock ID quantity")
        return
    pid, qty = context.args[0], context.args[1]
    if pid in data["products"]:
        data["products"][pid]["stock"] = int(qty)
        save_data(data)
        await update.message.reply_text(f"✅ Stock updated: {data['products'][pid]['name']} = {qty}")
    else:
        await update.message.reply_text("Product ID not found.")


async def toggle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str, label: str):
    if not is_admin(update):
        return
    data["payments"][method] = not data["payments"][method]
    save_data(data)
    status = "ON" if data["payments"][method] else "OFF"
    await update.message.reply_text(f"⚙️ {label} is now {status}")


async def toggle_cod(update, context):
    await toggle_payment(update, context, "cod", "Cash on Delivery")

async def toggle_telebirr(update, context):
    await toggle_payment(update, context, "telebirr", "Telebirr")

async def toggle_cbe(update, context):
    await toggle_payment(update, context, "cbe", "CBE Bank Transfer")


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Need help? Contact us:\n📞 {SUPPORT_PHONE}\n💬 {SUPPORT_TELEGRAM}"
    )


async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await register_admin(update, context)
    text = (
        "🛠 Admin Commands:\n"
        "/addproduct - Add a new product (with photo)\n"
        "/addcategory - Add a new category\n"
        "/removecategory NAME - Remove a category\n"
        "/listproducts - List all products with IDs\n"
        "/removeproduct ID - Remove a product\n"
        "/setstock ID QTY - Update stock\n"
        "/toggle_cod - Turn Cash on Delivery on/off\n"
        "/toggle_telebirr - Turn Telebirr on/off\n"
        "/toggle_cbe - Turn CBE Transfer on/off\n"
    )
    await update.message.reply_text(text)


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("Set the BOT_TOKEN environment variable")

    app = Application.builder().token(token).build()

    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_entry, pattern="^checkout$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PAYMENT_PROOF: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), get_payment_proof)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    add_product_conv = ConversationHandler(
        entry_points=[CommandHandler("addproduct", add_product_start)],
        states={
            ADD_PHOTO: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), add_product_photo)],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_name)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_price)],
            ADD_CATEGORY: [CallbackQueryHandler(add_product_category, pattern="^setcat_")],
            ADD_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_stock)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    add_category_conv = ConversationHandler(
        entry_points=[CommandHandler("addcategory", add_category_start)],
        states={NEW_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_finish)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CommandHandler("admin", admin_help))
    app.add_handler(CommandHandler("removecategory", remove_category))
    app.add_handler(CommandHandler("listproducts", list_products))
    app.add_handler(CommandHandler("removeproduct", remove_product))
    app.add_handler(CommandHandler("setstock", set_stock))
    app.add_handler(CommandHandler("toggle_cod", toggle_cod))
    app.add_handler(CommandHandler("toggle_telebirr", toggle_telebirr))
    app.add_handler(CommandHandler("toggle_cbe", toggle_cbe))
    app.add_handler(checkout_conv)
    app.add_handler(add_product_conv)
    app.add_handler(add_category_conv)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
