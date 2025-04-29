export const adminCommands = {
  async showPanel(bot, msg, supabase) {
    const isAdmin = await checkAdmin(msg.from.id, supabase);
    if (!isAdmin) {
      bot.sendMessage(msg.chat.id, "Bu buyruq faqat adminlar uchun!");
      return;
    }

    const keyboard = {
      inline_keyboard: [
        [{ text: "👥 Foydalanuvchilar soni", callback_data: "users_count" }],
        [{ text: "📢 Reklama yuborish", callback_data: "send_ad" }],
        [{ text: "➕ Anime qo'shish", callback_data: "add_anime" }]
      ]
    };

    bot.sendMessage(msg.chat.id, "Admin panel:", { reply_markup: keyboard });
  },

  async showUsers(bot, msg, supabase) {
    const isAdmin = await checkAdmin(msg.from.id, supabase);
    if (!isAdmin) return;

    const { data: users } = await supabase
      .from('users')
      .select('*');

    const stats = `
Jami foydalanuvchilar: ${users.length}
VIP foydalanuvchilar: ${users.filter(u => u.is_vip).length}
    `;

    bot.sendMessage(msg.chat.id, stats);
  },

  async broadcast(bot, msg, supabase) {
    const isAdmin = await checkAdmin(msg.from.id, supabase);
    if (!isAdmin) return;

    // Implementation for broadcasting messages to all users
  }
};

async function checkAdmin(userId, supabase) {
  const { data } = await supabase
    .from('admins')
    .select('*')
    .eq('user_id', userId)
    .single();
  
  return !!data;
}