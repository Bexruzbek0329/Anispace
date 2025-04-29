from telegram import InlineKeyboardMarkup, InlineKeyboardButton

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Orqaga", callback_data="back")]
])

await query.message.edit_text("Yangi matn", reply_markup=keyboard)